from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pytest
from specproof_capture_service.calibration import (
    CalibrationStore,
    calibration_is_acceptable,
    create_calibration_record,
)
from specproof_capture_service.capture_package import CapturePackageReader, CapturePackageWriter
from specproof_capture_service.coordinator import CaptureCoordinator
from specproof_capture_service.errors import CalibrationExpiredError, CameraNotFoundError
from specproof_capture_service.fusion import fuse_depth_median, select_midpoint_color
from specproof_capture_service.identity import InMemoryCredentialStore, StationIdentity
from specproof_capture_service.mock_provider import MockCameraProvider
from specproof_capture_service.models import (
    CalibrationMetrics,
    CalibrationMode,
    CalibrationThresholds,
    StreamProfile,
)
from specproof_capture_service.offline_queue import OfflineCaptureQueue, QueueState
from specproof_capture_service.replay_provider import CaptureReplayProvider
from specproof_capture_service.synchronization import CaptureSynchronizer, UploadTarget


@pytest.fixture
def small_profile() -> StreamProfile:
    return StreamProfile(
        color_width=8,
        color_height=6,
        depth_width=8,
        depth_height=6,
        frames_per_second=30,
    )


@pytest.fixture
def passing_metrics() -> CalibrationMetrics:
    return CalibrationMetrics(
        scale_error_percent=0.05,
        plane_rms_mm=1.0,
        tilt_degrees=0.25,
        lighting_variation_percent=5.0,
        alignment_valid=True,
    )


@pytest.mark.unit
def test_calibration_is_acceptable_metrics_within_thresholds_returns_true(
    passing_metrics: CalibrationMetrics,
) -> None:
    assert calibration_is_acceptable(passing_metrics, CalibrationThresholds()) is True


@pytest.mark.unit
def test_calibration_is_acceptable_scale_error_exceeds_threshold_returns_false(
    passing_metrics: CalibrationMetrics,
) -> None:
    rejected = passing_metrics.model_copy(update={"scale_error_percent": 0.11})

    assert calibration_is_acceptable(rejected, CalibrationThresholds()) is False


@pytest.mark.unit
def test_create_calibration_record_daily_mode_expires_in_24_hours(
    passing_metrics: CalibrationMetrics,
) -> None:
    record = create_calibration_record(
        version=1,
        station_id="station-001",
        camera_serial="MOCK-001",
        operator_id="operator-001",
        artefact_id="artefact-001",
        mode=CalibrationMode.DAILY,
        metrics=passing_metrics,
        thresholds=CalibrationThresholds(),
    )

    lifetime = record.expires_at_utc - record.calibrated_at_utc

    assert lifetime.total_seconds() == 24 * 60 * 60


@pytest.mark.unit
async def test_mock_provider_unknown_serial_raises_camera_not_found(
    small_profile: StreamProfile,
) -> None:
    provider = MockCameraProvider()

    with pytest.raises(CameraNotFoundError):
        await provider.capture_frames("UNKNOWN", small_profile, 3)


@pytest.mark.unit
async def test_mock_provider_capture_returns_aligned_frames(
    small_profile: StreamProfile,
) -> None:
    provider = MockCameraProvider()

    frames = await provider.capture_frames("MOCK-001", small_profile, 3)

    assert all(frame.color_bgr.shape[:2] == frame.depth_units.shape for frame in frames)


@pytest.mark.unit
async def test_fusion_valid_and_missing_depth_returns_per_pixel_median(
    small_profile: StreamProfile,
) -> None:
    frames = list(await MockCameraProvider().capture_frames("MOCK-001", small_profile, 3))
    frames[0].depth_units[0, 0] = 0
    frames[1].depth_units[0, 0] = 900
    frames[2].depth_units[0, 0] = 1100

    fused = fuse_depth_median(frames)

    assert fused[0, 0] == 1000


@pytest.mark.unit
async def test_select_midpoint_color_returns_middle_frame(
    small_profile: StreamProfile,
) -> None:
    frames = await MockCameraProvider().capture_frames("MOCK-001", small_profile, 5)

    selected = select_midpoint_color(frames)

    assert np.array_equal(selected, frames[2].color_bgr)


@pytest.mark.unit
async def test_capture_package_round_trip_validates_manifest_and_checksums(
    tmp_path: Path,
    small_profile: StreamProfile,
) -> None:
    frames = await MockCameraProvider().capture_frames("MOCK-001", small_profile, 3)
    package_path = tmp_path / "capture.spcapture"

    manifest, digest = CapturePackageWriter().write(
        output_path=package_path,
        station_id="station-001",
        calibration_id="calibration-001",
        profile=small_profile,
        frames=frames,
    )
    loaded = CapturePackageReader().read_manifest(package_path)

    assert loaded == manifest and len(digest) == 64


@pytest.mark.unit
async def test_replay_provider_reads_recorded_frames(
    tmp_path: Path,
    small_profile: StreamProfile,
) -> None:
    frames = await MockCameraProvider().capture_frames("MOCK-001", small_profile, 3)
    package_path = tmp_path / "capture.spcapture"
    CapturePackageWriter().write(
        output_path=package_path,
        station_id="station-001",
        calibration_id="calibration-001",
        profile=small_profile,
        frames=frames,
    )
    replay = CaptureReplayProvider(package_path)

    replayed = await replay.capture_frames("MOCK-001", small_profile, 3)

    assert np.array_equal(replayed[1].depth_units, frames[1].depth_units)


@pytest.mark.unit
def test_offline_queue_duplicate_capture_is_idempotent(tmp_path: Path) -> None:
    queue = OfflineCaptureQueue(tmp_path / "queue.sqlite3")

    first = queue.enqueue("capture-001", tmp_path / "capture.spcapture", "a" * 64)
    second = queue.enqueue("capture-001", tmp_path / "capture.spcapture", "a" * 64)

    depth = queue.depth()
    queue.close()
    assert first.id == second.id and depth == 1


@pytest.mark.unit
def test_in_memory_credential_store_round_trips_station_identity() -> None:
    store = InMemoryCredentialStore()
    identity = StationIdentity(station_id="station-001", credential="secret-value")

    store.save(identity)

    assert store.load() == identity


@pytest.mark.unit
def test_offline_queue_failed_upload_schedules_retry(tmp_path: Path) -> None:
    queue = OfflineCaptureQueue(tmp_path / "queue.sqlite3")
    queue.enqueue("capture-001", tmp_path / "capture.spcapture", "a" * 64)
    claimed = queue.claim_next(datetime.now(UTC))
    assert claimed is not None

    queue.fail(claimed.id, "network unavailable", datetime.now(UTC))
    failed = queue.get(claimed.id)

    queue.close()
    assert failed is not None and failed.state == QueueState.FAILED


@pytest.mark.unit
def test_offline_queue_restart_recovers_uploading_item(tmp_path: Path) -> None:
    database_path = tmp_path / "queue.sqlite3"
    queue = OfflineCaptureQueue(database_path)
    queue.enqueue("capture-001", tmp_path / "capture.spcapture", "a" * 64)
    claimed = queue.claim_next()
    assert claimed is not None
    queue.close()

    recovered_queue = OfflineCaptureQueue(database_path)
    recovered = recovered_queue.get(claimed.id)

    recovered_queue.close()
    assert recovered is not None and recovered.state == QueueState.FAILED


@pytest.mark.unit
async def test_coordinator_without_active_calibration_blocks_capture(
    tmp_path: Path,
    small_profile: StreamProfile,
) -> None:
    queue = OfflineCaptureQueue(tmp_path / "queue.sqlite3")
    coordinator = CaptureCoordinator(
        provider=MockCameraProvider(),
        calibration_store=CalibrationStore(tmp_path / "calibrations"),
        queue=queue,
        capture_root=tmp_path / "captures",
    )

    with pytest.raises(CalibrationExpiredError):
        await coordinator.capture(
            station_id="station-001",
            camera_serial="MOCK-001",
            profile=small_profile,
            frame_count=3,
        )
    queue.close()


@pytest.mark.unit
async def test_coordinator_active_calibration_creates_and_queues_package(
    tmp_path: Path,
    small_profile: StreamProfile,
    passing_metrics: CalibrationMetrics,
) -> None:
    store = CalibrationStore(tmp_path / "calibrations")
    store.save(
        create_calibration_record(
            version=1,
            station_id="station-001",
            camera_serial="MOCK-001",
            operator_id="operator-001",
            artefact_id="artefact-001",
            mode=CalibrationMode.FULL,
            metrics=passing_metrics,
            thresholds=CalibrationThresholds(),
        )
    )
    queue = OfflineCaptureQueue(tmp_path / "queue.sqlite3")
    coordinator = CaptureCoordinator(
        provider=MockCameraProvider(),
        calibration_store=store,
        queue=queue,
        capture_root=tmp_path / "captures",
    )

    manifest, package_path, digest = await coordinator.capture(
        station_id="station-001",
        camera_serial="MOCK-001",
        profile=small_profile,
        frame_count=3,
    )

    depth = queue.depth()
    queue.close()
    assert package_path.exists() and depth == 1 and len(digest) == 64
    assert manifest.camera_serial == "MOCK-001"


@pytest.mark.unit
def test_synchronizer_valid_package_uploads_and_completes_queue(tmp_path: Path) -> None:
    package_path = tmp_path / "capture.spcapture"
    package_path.write_bytes(b"capture-payload")
    digest = hashlib.sha256(package_path.read_bytes()).hexdigest()
    queue = OfflineCaptureQueue(tmp_path / "queue.sqlite3")
    queued = queue.enqueue("capture-001", package_path, digest)

    class PlatformClient:
        completed = False

        def initiate_capture(self, **_: object) -> UploadTarget:
            return UploadTarget("asset-001", "captures/capture-001.spcapture")

        def complete_capture(self, **_: object) -> None:
            self.completed = True

    class ObjectStore:
        uploaded = False

        @property
        def encrypted(self) -> bool:
            return True

        def upload(self, **_: object) -> None:
            self.uploaded = True

    platform_client = PlatformClient()
    object_store = ObjectStore()
    synchronizer = CaptureSynchronizer(
        queue=queue,
        platform_client=platform_client,
        object_store=object_store,
    )

    result = synchronizer.synchronize_once()

    completed = queue.get(queued.id)
    queue.close()
    assert result is True and platform_client.completed and object_store.uploaded
    assert completed is not None and completed.state == QueueState.COMPLETED
