"""Deterministic mock camera provider."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Sequence
from pathlib import Path
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


class MockCameraProvider:
    """Synthetic provider used by unit tests and development."""

    def __init__(self, serial_number: str = "MOCK-001") -> None:
        self._device = CameraDevice(
            serial_number=serial_number,
            name="SpecProof Mock RGB-D",
            firmware_version="1.0.0",
            usb_type="3.2",
        )
        self._connected = True
        self._recording_path: Path | None = None

    def set_connected(self, connected: bool) -> None:
        """Change simulated connection state."""

        self._connected = connected

    async def list_devices(self) -> Sequence[CameraDevice]:
        """Return the mock camera when connected."""

        return [self._device] if self._connected else []

    async def capture_frames(
        self,
        camera_serial: str,
        profile: StreamProfile,
        frame_count: int,
    ) -> Sequence[CameraFrame]:
        """Create deterministic aligned frames."""

        self._require_camera(camera_serial)
        return [self._create_frame(profile, index) for index in range(frame_count)]

    async def stream_preview(
        self,
        camera_serial: str,
        profile: StreamProfile,
    ) -> AsyncIterator[CameraFrame]:
        """Yield preview frames at the requested rate."""

        index = 0
        while self._connected:
            self._require_camera(camera_serial)
            yield self._create_frame(profile, index)
            index += 1
            await asyncio.sleep(1 / profile.frames_per_second)

    async def start_recording(
        self,
        camera_serial: str,
        profile: StreamProfile,
        output_path: Path,
    ) -> None:
        """Begin a synthetic recording."""

        self._require_camera(camera_serial)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.touch()
        self._recording_path = output_path

    async def stop_recording(self) -> Path:
        """Stop the active synthetic recording."""

        if self._recording_path is None:
            raise CameraUnavailableError("No recording is active")
        path = self._recording_path
        self._recording_path = None
        return path

    async def close(self) -> None:
        """Release mock resources."""

    def _require_camera(self, camera_serial: str) -> None:
        if not self._connected or camera_serial != self._device.serial_number:
            raise CameraNotFoundError(f"Camera {camera_serial} was not found")

    def _create_frame(self, profile: StreamProfile, index: int) -> CameraFrame:
        color = np.zeros((profile.color_height, profile.color_width, 3), dtype=np.uint8)
        color[:, :, 1] = np.uint8(index % 255)
        depth = np.full(
            (profile.color_height, profile.color_width),
            1000 + index,
            dtype=np.uint16,
        )
        color_intrinsics = CameraIntrinsics(
            width=profile.color_width,
            height=profile.color_height,
            fx=float(profile.color_width),
            fy=float(profile.color_height),
            ppx=profile.color_width / 2,
            ppy=profile.color_height / 2,
            distortion_model="none",
        )
        depth_intrinsics = CameraIntrinsics(
            width=profile.depth_width,
            height=profile.depth_height,
            fx=float(profile.depth_width),
            fy=float(profile.depth_height),
            ppx=profile.depth_width / 2,
            ppy=profile.depth_height / 2,
            distortion_model="none",
        )
        return CameraFrame(
            frame_id=str(uuid4()),
            camera_serial=self._device.serial_number,
            captured_at_utc=utc_now(),
            color_bgr=color,
            depth_units=depth,
            depth_scale_metres=0.001,
            color_intrinsics=color_intrinsics,
            depth_intrinsics=depth_intrinsics,
            depth_to_color=CameraExtrinsics(
                rotation=(1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0),
                translation_metres=(0.0, 0.0, 0.0),
            ),
        )
