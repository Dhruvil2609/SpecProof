"""Windows RealSense camera provider."""

from __future__ import annotations

import asyncio
import importlib
from collections.abc import AsyncIterator, Sequence
from pathlib import Path
from types import ModuleType
from uuid import uuid4

import numpy as np

from specproof_capture_service.errors import CameraNotFoundError, CameraUnavailableError
from specproof_capture_service.models import (
    CameraDevice,
    CameraExtrinsics,
    CameraFrame,
    CameraIntrinsics,
    StreamProfile,
    utc_now,
)


class RealSenseCameraProvider:
    """Native RealSense provider with bounded capture retries."""

    def __init__(self, maximum_attempts: int = 3) -> None:
        if maximum_attempts < 1:
            raise ValueError("maximum_attempts must be positive")
        self._maximum_attempts = maximum_attempts
        self._rs = self._load_sdk()
        self._recording_pipeline: object | None = None
        self._recording_path: Path | None = None

    async def list_devices(self) -> Sequence[CameraDevice]:
        """Enumerate connected devices by serial number."""

        return await asyncio.to_thread(self._list_devices_sync)

    async def capture_frames(
        self,
        camera_serial: str,
        profile: StreamProfile,
        frame_count: int,
    ) -> Sequence[CameraFrame]:
        """Capture aligned frames with bounded recovery attempts."""

        last_error: Exception | None = None
        for attempt in range(self._maximum_attempts):
            try:
                return await asyncio.to_thread(
                    self._capture_sync,
                    camera_serial,
                    profile,
                    frame_count,
                )
            except CameraNotFoundError:
                raise
            except Exception as error:
                last_error = error
                if attempt + 1 < self._maximum_attempts:
                    await asyncio.sleep(0.25 * (attempt + 1))
        raise CameraUnavailableError(str(last_error)) from last_error

    async def stream_preview(
        self,
        camera_serial: str,
        profile: StreamProfile,
    ) -> AsyncIterator[CameraFrame]:
        """Yield aligned frames from one active pipeline."""

        pipeline, align = await asyncio.to_thread(
            self._start_pipeline,
            camera_serial,
            profile,
            None,
        )
        try:
            while True:
                yield await asyncio.to_thread(
                    self._read_aligned_frame,
                    pipeline,
                    align,
                    camera_serial,
                )
        except Exception as error:
            raise CameraUnavailableError(str(error)) from error
        finally:
            await asyncio.to_thread(pipeline.stop)

    async def start_recording(
        self,
        camera_serial: str,
        profile: StreamProfile,
        output_path: Path,
    ) -> None:
        """Begin recording a native `.bag` file."""

        if self._recording_pipeline is not None:
            raise CameraUnavailableError("A recording is already active")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        pipeline, _ = await asyncio.to_thread(
            self._start_pipeline,
            camera_serial,
            profile,
            output_path,
        )
        self._recording_pipeline = pipeline
        self._recording_path = output_path

    async def stop_recording(self) -> Path:
        """Stop recording and return the `.bag` path."""

        if self._recording_pipeline is None or self._recording_path is None:
            raise CameraUnavailableError("No recording is active")
        await asyncio.to_thread(self._recording_pipeline.stop)
        path = self._recording_path
        self._recording_pipeline = None
        self._recording_path = None
        return path

    async def close(self) -> None:
        """Release an active recording pipeline."""

        if self._recording_pipeline is not None:
            await asyncio.to_thread(self._recording_pipeline.stop)
            self._recording_pipeline = None
            self._recording_path = None

    @staticmethod
    def _load_sdk() -> ModuleType:
        try:
            return importlib.import_module("pyrealsense2")
        except ImportError as error:
            raise CameraUnavailableError("pyrealsense2 is not installed") from error

    def _list_devices_sync(self) -> Sequence[CameraDevice]:
        context = self._rs.context()
        devices: list[CameraDevice] = []
        for device in context.query_devices():
            devices.append(
                CameraDevice(
                    serial_number=device.get_info(self._rs.camera_info.serial_number),
                    name=device.get_info(self._rs.camera_info.name),
                    firmware_version=device.get_info(self._rs.camera_info.firmware_version),
                    usb_type=self._safe_device_info(
                        device, self._rs.camera_info.usb_type_descriptor
                    ),
                )
            )
        return devices

    @staticmethod
    def _safe_device_info(device: object, key: object) -> str:
        try:
            return str(device.get_info(key))
        except RuntimeError:
            return "unknown"

    def _capture_sync(
        self,
        camera_serial: str,
        profile: StreamProfile,
        frame_count: int,
    ) -> Sequence[CameraFrame]:
        pipeline, align = self._start_pipeline(camera_serial, profile, None)
        try:
            for _ in range(5):
                pipeline.wait_for_frames(5000)
            return [
                self._read_aligned_frame(pipeline, align, camera_serial) for _ in range(frame_count)
            ]
        finally:
            pipeline.stop()

    def _start_pipeline(
        self,
        camera_serial: str,
        profile: StreamProfile,
        recording_path: Path | None,
    ) -> tuple[object, object]:
        if camera_serial not in {device.serial_number for device in self._list_devices_sync()}:
            raise CameraNotFoundError(f"Camera {camera_serial} was not found")
        pipeline = self._rs.pipeline()
        config = self._rs.config()
        config.enable_device(camera_serial)
        config.enable_stream(
            self._rs.stream.depth,
            profile.depth_width,
            profile.depth_height,
            self._rs.format.z16,
            profile.frames_per_second,
        )
        config.enable_stream(
            self._rs.stream.color,
            profile.color_width,
            profile.color_height,
            self._rs.format.bgr8,
            profile.frames_per_second,
        )
        if recording_path is not None:
            config.enable_record_to_file(str(recording_path))
        pipeline.start(config)
        return pipeline, self._rs.align(self._rs.stream.color)

    def _read_aligned_frame(
        self,
        pipeline: object,
        align: object,
        camera_serial: str,
    ) -> CameraFrame:
        frames = align.process(pipeline.wait_for_frames(5000))
        color_frame = frames.get_color_frame()
        depth_frame = frames.get_depth_frame()
        if not color_frame or not depth_frame:
            raise CameraUnavailableError("Aligned RGB-D frame was incomplete")
        color_profile = color_frame.profile.as_video_stream_profile()
        depth_profile = depth_frame.profile.as_video_stream_profile()
        extrinsics = depth_profile.get_extrinsics_to(color_profile)
        depth_sensor = pipeline.get_active_profile().get_device().first_depth_sensor()
        return CameraFrame(
            frame_id=str(uuid4()),
            camera_serial=camera_serial,
            captured_at_utc=utc_now(),
            color_bgr=np.asanyarray(color_frame.get_data()).copy(),
            depth_units=np.asanyarray(depth_frame.get_data()).copy(),
            depth_scale_metres=float(depth_sensor.get_depth_scale()),
            color_intrinsics=self._map_intrinsics(color_profile.get_intrinsics()),
            depth_intrinsics=self._map_intrinsics(depth_profile.get_intrinsics()),
            depth_to_color=CameraExtrinsics(
                rotation=tuple(float(value) for value in extrinsics.rotation),
                translation_metres=tuple(float(value) for value in extrinsics.translation),
            ),
        )

    @staticmethod
    def _map_intrinsics(value: object) -> CameraIntrinsics:
        return CameraIntrinsics(
            width=int(value.width),
            height=int(value.height),
            fx=float(value.fx),
            fy=float(value.fy),
            ppx=float(value.ppx),
            ppy=float(value.ppy),
            distortion_model=str(value.model),
            coefficients=tuple(float(coefficient) for coefficient in value.coeffs),
        )
