"""Capture workflow orchestration."""

from __future__ import annotations

import platform
from pathlib import Path
from time import perf_counter_ns

from opentelemetry import metrics

from specproof_capture_service.calibration import CalibrationStore
from specproof_capture_service.capture_package import CapturePackageWriter
from specproof_capture_service.errors import CalibrationExpiredError
from specproof_capture_service.models import CaptureManifest, StationHealth, StreamProfile
from specproof_capture_service.offline_queue import OfflineCaptureQueue
from specproof_capture_service.provider import CameraProvider

_meter = metrics.get_meter("specproof.capture.coordinator")
_capture_duration = _meter.create_histogram(
    "specproof.capture.duration",
    unit="ms",
    description="Calibrated capture and durable package queue duration",
)


class CaptureCoordinator:
    """Coordinate calibrated capture, packaging, and offline queuing."""

    def __init__(
        self,
        *,
        provider: CameraProvider,
        calibration_store: CalibrationStore,
        queue: OfflineCaptureQueue,
        capture_root: Path,
    ) -> None:
        self._provider = provider
        self._calibration_store = calibration_store
        self._queue = queue
        self._capture_root = capture_root
        self._writer = CapturePackageWriter()

    async def capture(
        self,
        *,
        station_id: str,
        camera_serial: str,
        profile: StreamProfile | None = None,
        frame_count: int = 5,
    ) -> tuple[CaptureManifest, Path, str]:
        """Capture and queue a checksummed package."""

        started = perf_counter_ns()
        if not 3 <= frame_count <= 15:
            raise ValueError("frame_count must be between 3 and 15")
        calibration = self._calibration_store.get_active(station_id, camera_serial)
        if calibration is None:
            raise CalibrationExpiredError(
                f"No active calibration exists for station {station_id} and camera {camera_serial}"
            )
        active_profile = profile or StreamProfile()
        frames = await self._provider.capture_frames(
            camera_serial,
            active_profile,
            frame_count,
        )
        temporary_name = self._capture_root / f"{frames[0].frame_id}.spcapture"
        manifest, package_sha256 = self._writer.write(
            output_path=temporary_name,
            station_id=station_id,
            calibration_id=calibration.calibration_id,
            profile=active_profile,
            frames=frames,
            environment={
                "os": platform.system(),
                "architecture": platform.machine(),
                "provider": type(self._provider).__name__,
            },
        )
        final_path = temporary_name.with_name(f"{manifest.capture_id}.spcapture")
        temporary_name.replace(final_path)
        self._queue.enqueue(manifest.capture_id, final_path, package_sha256)
        _capture_duration.record((perf_counter_ns() - started) / 1_000_000)
        return manifest, final_path, package_sha256

    async def health(self) -> StationHealth:
        """Return current camera and local storage health."""

        devices = await self._provider.list_devices()
        self._capture_root.mkdir(parents=True, exist_ok=True)
        return StationHealth(
            status="healthy" if devices else "degraded",
            camera_status="available" if devices else "unavailable",
            storage_status="available",
            clock_status="utc",
            offline_queue_depth=self._queue.depth(),
            detail=f"{len(devices)} camera(s) detected",
        )
