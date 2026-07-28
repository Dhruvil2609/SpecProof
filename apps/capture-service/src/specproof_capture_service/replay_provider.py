"""Replay provider for `.spcapture` packages."""

from __future__ import annotations

import asyncio
import json
import zipfile
from collections.abc import AsyncIterator, Sequence
from pathlib import Path

import cv2
import numpy as np

from specproof_capture_service.capture_package import CapturePackageReader
from specproof_capture_service.errors import CameraNotFoundError, CameraUnavailableError
from specproof_capture_service.models import (
    CameraDevice,
    CameraExtrinsics,
    CameraFrame,
    CameraIntrinsics,
    StreamProfile,
)


class CaptureReplayProvider:
    """Replay aligned frames from a validated capture package."""

    def __init__(self, package_path: Path) -> None:
        self._package_path = package_path
        self._manifest = CapturePackageReader().read_manifest(package_path)

    async def list_devices(self) -> Sequence[CameraDevice]:
        """Return the camera represented by the package."""

        return [
            CameraDevice(
                serial_number=self._manifest.camera_serial,
                name="SpecProof Capture Replay",
                firmware_version="recorded",
                usb_type="replay",
                active_profile=self._manifest.profile,
            )
        ]

    async def capture_frames(
        self,
        camera_serial: str,
        profile: StreamProfile,
        frame_count: int,
    ) -> Sequence[CameraFrame]:
        """Return recorded frames in deterministic order."""

        if camera_serial != self._manifest.camera_serial:
            raise CameraNotFoundError(f"Camera {camera_serial} was not found in replay")
        frames = await asyncio.to_thread(self._load_frames)
        if frame_count > len(frames):
            raise CameraUnavailableError("Replay package contains fewer frames than requested")
        return frames[:frame_count]

    async def stream_preview(
        self,
        camera_serial: str,
        profile: StreamProfile,
    ) -> AsyncIterator[CameraFrame]:
        """Loop recorded frames at the requested frame rate."""

        frames = await self.capture_frames(camera_serial, profile, self._manifest.frame_count)
        while True:
            for frame in frames:
                yield frame
                await asyncio.sleep(1 / profile.frames_per_second)

    async def start_recording(
        self,
        camera_serial: str,
        profile: StreamProfile,
        output_path: Path,
    ) -> None:
        """Reject recording during replay."""

        raise CameraUnavailableError("Replay providers cannot create native recordings")

    async def stop_recording(self) -> Path:
        """Reject recording during replay."""

        raise CameraUnavailableError("Replay providers cannot create native recordings")

    async def close(self) -> None:
        """Release replay resources."""

    def _load_frames(self) -> list[CameraFrame]:
        with zipfile.ZipFile(self._package_path, mode="r") as archive:
            color_intrinsics = CameraIntrinsics.model_validate_json(
                archive.read("calibration/color-intrinsics.json")
            )
            depth_intrinsics = CameraIntrinsics.model_validate_json(
                archive.read("calibration/depth-intrinsics.json")
            )
            extrinsics = CameraExtrinsics.model_validate_json(
                archive.read("calibration/depth-to-color.json")
            )
            result: list[CameraFrame] = []
            for index in range(self._manifest.frame_count):
                metadata = json.loads(
                    archive.read(f"frames/{index:03d}-metadata.json").decode("utf-8")
                )
                color = self._decode_image(
                    archive.read(f"frames/{index:03d}-color.png"),
                    cv2.IMREAD_COLOR,
                )
                depth = self._decode_image(
                    archive.read(f"frames/{index:03d}-depth.png"),
                    cv2.IMREAD_UNCHANGED,
                )
                result.append(
                    CameraFrame(
                        frame_id=metadata["frame_id"],
                        camera_serial=self._manifest.camera_serial,
                        captured_at_utc=metadata["captured_at_utc"],
                        color_bgr=color,
                        depth_units=depth,
                        depth_scale_metres=self._manifest.depth_scale_metres,
                        color_intrinsics=color_intrinsics,
                        depth_intrinsics=depth_intrinsics,
                        depth_to_color=extrinsics,
                    )
                )
            return result

    @staticmethod
    def _decode_image(payload: bytes, mode: int) -> np.ndarray:
        image = cv2.imdecode(np.frombuffer(payload, dtype=np.uint8), mode)
        if image is None:
            raise CameraUnavailableError("Replay image could not be decoded")
        return image
