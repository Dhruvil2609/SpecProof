"""Camera provider abstraction."""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from pathlib import Path
from typing import Protocol

from specproof_capture_service.models import CameraDevice, CameraFrame, StreamProfile


class CameraProvider(Protocol):
    """Platform-independent camera operations."""

    async def list_devices(self) -> Sequence[CameraDevice]:
        """Return connected camera devices."""
        ...

    async def capture_frames(
        self,
        camera_serial: str,
        profile: StreamProfile,
        frame_count: int,
    ) -> Sequence[CameraFrame]:
        """Capture aligned RGB-D frames."""
        ...

    def stream_preview(
        self,
        camera_serial: str,
        profile: StreamProfile,
    ) -> AsyncIterator[CameraFrame]:
        """Yield preview frames."""
        ...

    async def start_recording(
        self,
        camera_serial: str,
        profile: StreamProfile,
        output_path: Path,
    ) -> None:
        """Begin native recording."""
        ...

    async def stop_recording(self) -> Path:
        """Stop recording and return its path."""
        ...

    async def close(self) -> None:
        """Release provider resources."""
        ...
