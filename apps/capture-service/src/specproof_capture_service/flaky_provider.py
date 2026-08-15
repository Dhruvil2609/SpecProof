"""Deterministic camera failure injection for resilience qualification."""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from pathlib import Path

from specproof_capture_service.errors import CameraUnavailableError
from specproof_capture_service.models import CameraDevice, CameraFrame, StreamProfile
from specproof_capture_service.provider import CameraProvider


class FlakyCameraProvider:
    """Wrap a camera provider and fail a bounded number of capture attempts."""

    def __init__(self, provider: CameraProvider, *, capture_failures: int = 1) -> None:
        if capture_failures < 0:
            raise ValueError("capture_failures cannot be negative")
        self._provider = provider
        self._remaining_capture_failures = capture_failures
        self.capture_attempts = 0

    async def list_devices(self) -> Sequence[CameraDevice]:
        """Delegate device enumeration."""

        return await self._provider.list_devices()

    async def capture_frames(
        self,
        camera_serial: str,
        profile: StreamProfile,
        frame_count: int,
    ) -> Sequence[CameraFrame]:
        """Inject configured transient crashes before delegating capture."""

        self.capture_attempts += 1
        if self._remaining_capture_failures > 0:
            self._remaining_capture_failures -= 1
            raise CameraUnavailableError("Injected camera process crash")
        return await self._provider.capture_frames(camera_serial, profile, frame_count)

    async def stream_preview(
        self,
        camera_serial: str,
        profile: StreamProfile,
    ) -> AsyncIterator[CameraFrame]:
        """Delegate preview streaming."""

        async for frame in self._provider.stream_preview(camera_serial, profile):
            yield frame

    async def start_recording(
        self,
        camera_serial: str,
        profile: StreamProfile,
        output_path: Path,
    ) -> None:
        """Delegate recording startup."""

        await self._provider.start_recording(camera_serial, profile, output_path)

    async def stop_recording(self) -> Path:
        """Delegate recording shutdown."""

        return await self._provider.stop_recording()

    async def close(self) -> None:
        """Delegate resource cleanup."""

        await self._provider.close()
