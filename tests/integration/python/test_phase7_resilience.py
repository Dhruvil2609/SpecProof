from __future__ import annotations

import multiprocessing
import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest
from specproof_capture_service import FlakyCameraProvider
from specproof_capture_service.calibration import CalibrationStore, create_calibration_record
from specproof_capture_service.coordinator import CaptureCoordinator
from specproof_capture_service.inspection_queue import (
    InspectionQueueState,
    OfflineInspectionQueue,
)
from specproof_capture_service.mock_provider import MockCameraProvider
from specproof_capture_service.models import (
    CalibrationMetrics,
    CalibrationMode,
    CalibrationThresholds,
    StreamProfile,
)
from specproof_capture_service.offline_queue import OfflineCaptureQueue
from specproof_capture_service.synchronization import InspectionResultSynchronizer


class UnavailablePlatformClient:
    def submit_inspection(self, **_: object) -> dict[str, object]:
        raise ConnectionError("Platform returned HTTP 503: database unavailable")


class AmbiguousDeliveryPlatformClient:
    def __init__(self) -> None:
        self.calls = 0
        self.accepted: dict[str, dict[str, object]] = {}

    def submit_inspection(
        self,
        *,
        payload: dict[str, object],
        payload_hash_sha256: str,
        idempotency_key: str,
    ) -> dict[str, object]:
        del payload_hash_sha256
        self.calls += 1
        self.accepted.setdefault(idempotency_key, payload)
        if self.calls == 1:
            raise ConnectionError("Connection dropped after platform commit")
        return self.accepted[idempotency_key]


def _claim_result_and_terminate(database_path: str) -> None:
    queue = OfflineInspectionQueue(Path(database_path))
    queue.enqueue(
        capture_id="capture-power-loss",
        inspection_id="inspection-power-loss",
        payload=_payload("inspection-power-loss", "capture-power-loss"),
    )
    claimed = queue.claim_for_captures(("capture-power-loss",))
    if claimed is None:
        os._exit(22)
    os._exit(23)


@pytest.mark.integration
def test_process_termination_after_durable_claim_recovers_without_loss(tmp_path: Path) -> None:
    database_path = tmp_path / "inspection-results.sqlite3"
    process = multiprocessing.get_context("spawn").Process(
        target=_claim_result_and_terminate,
        args=(str(database_path),),
    )

    process.start()
    process.join(timeout=15)

    assert process.exitcode == 23
    recovered = OfflineInspectionQueue(database_path)
    item = recovered.get_by_inspection_id("inspection-power-loss")
    assert item is not None
    assert item.state == InspectionQueueState.RETRYABLE_FAILURE
    assert recovered.depth() == 1
    recovered.close()


@pytest.mark.integration
def test_ambiguous_network_failure_replays_idempotently_after_dead_letter_review(
    tmp_path: Path,
) -> None:
    capture_queue = _completed_capture_queue(tmp_path, "capture-network")
    result_queue = OfflineInspectionQueue(
        tmp_path / "inspection-network.sqlite3",
        maximum_attempts=1,
    )
    queued = result_queue.enqueue(
        capture_id="capture-network",
        inspection_id="inspection-network",
        payload=_payload("inspection-network", "capture-network"),
    )
    platform = AmbiguousDeliveryPlatformClient()
    synchronizer = InspectionResultSynchronizer(
        capture_queue=capture_queue,
        result_queue=result_queue,
        platform_client=platform,
    )

    assert synchronizer.synchronize_once() is False
    failed = result_queue.get(queued.id)
    assert failed is not None and failed.state == InspectionQueueState.DEAD_LETTER
    result_queue.retry_dead_letter(queued.id)
    assert synchronizer.synchronize_once() is True

    completed = result_queue.get(queued.id)
    assert completed is not None and completed.state == InspectionQueueState.COMPLETED
    assert platform.calls == 2
    assert len(platform.accepted) == 1
    capture_queue.close()
    result_queue.close()


@pytest.mark.integration
def test_checksum_corruption_moves_immutable_result_to_dead_letter(tmp_path: Path) -> None:
    capture_queue = _completed_capture_queue(tmp_path, "capture-corrupt")
    database_path = tmp_path / "inspection-corrupt.sqlite3"
    result_queue = OfflineInspectionQueue(database_path)
    queued = result_queue.enqueue(
        capture_id="capture-corrupt",
        inspection_id="inspection-corrupt",
        payload=_payload("inspection-corrupt", "capture-corrupt"),
    )
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "UPDATE inspection_result_queue SET payload_json = '{}' WHERE id = ?",
            (queued.id,),
        )
    synchronizer = InspectionResultSynchronizer(
        capture_queue=capture_queue,
        result_queue=result_queue,
        platform_client=AmbiguousDeliveryPlatformClient(),
    )

    assert synchronizer.synchronize_once() is False

    corrupted = result_queue.get(queued.id)
    assert corrupted is not None
    assert corrupted.state == InspectionQueueState.DEAD_LETTER
    assert corrupted.last_error == "Inspection payload checksum does not match"
    capture_queue.close()
    result_queue.close()


@pytest.mark.integration
def test_database_unavailability_keeps_station_result_durable_for_retry(tmp_path: Path) -> None:
    capture_queue = _completed_capture_queue(tmp_path, "capture-database")
    database_path = tmp_path / "inspection-database.sqlite3"
    result_queue = OfflineInspectionQueue(database_path)
    queued = result_queue.enqueue(
        capture_id="capture-database",
        inspection_id="inspection-database",
        payload=_payload("inspection-database", "capture-database"),
    )
    synchronizer = InspectionResultSynchronizer(
        capture_queue=capture_queue,
        result_queue=result_queue,
        platform_client=UnavailablePlatformClient(),
    )

    assert synchronizer.synchronize_once() is False
    result_queue.close()
    capture_queue.close()

    recovered = OfflineInspectionQueue(database_path)
    item = recovered.get(queued.id)
    assert item is not None
    assert item.state == InspectionQueueState.RETRYABLE_FAILURE
    assert recovered.depth() == 1
    recovered.close()


@pytest.mark.integration
async def test_flaky_camera_crash_recovers_and_queues_capture(tmp_path: Path) -> None:
    station_id = "station-camera-recovery"
    camera_serial = "MOCK-RESILIENCE-001"
    calibration_store = CalibrationStore(tmp_path / "calibrations")
    calibration_store.save(
        create_calibration_record(
            version=1,
            station_id=station_id,
            camera_serial=camera_serial,
            operator_id="operator-resilience",
            artefact_id="artefact-resilience",
            mode=CalibrationMode.FULL,
            metrics=CalibrationMetrics(
                scale_error_percent=0.01,
                plane_rms_mm=0.5,
                tilt_degrees=0.1,
                lighting_variation_percent=1.0,
                alignment_valid=True,
            ),
            thresholds=CalibrationThresholds(),
        )
    )
    queue = OfflineCaptureQueue(tmp_path / "capture-queue.sqlite3")
    provider = FlakyCameraProvider(
        MockCameraProvider(camera_serial),
        capture_failures=2,
    )
    coordinator = CaptureCoordinator(
        provider=provider,
        calibration_store=calibration_store,
        queue=queue,
        capture_root=tmp_path / "captures",
        maximum_capture_attempts=3,
        recovery_delay_seconds=0,
    )

    manifest, package_path, _ = await coordinator.capture(
        station_id=station_id,
        camera_serial=camera_serial,
        profile=StreamProfile(
            color_width=8,
            color_height=6,
            depth_width=8,
            depth_height=6,
            frames_per_second=30,
        ),
        frame_count=3,
    )

    assert provider.capture_attempts == 3
    assert package_path.exists()
    assert queue.get_by_capture_id(manifest.capture_id) is not None
    queue.close()


def _completed_capture_queue(tmp_path: Path, capture_id: str) -> OfflineCaptureQueue:
    package_path = tmp_path / f"{capture_id}.spcapture"
    package_path.write_bytes(b"capture")
    queue = OfflineCaptureQueue(tmp_path / f"{capture_id}.sqlite3")
    queued = queue.enqueue(capture_id, package_path, "a" * 64)
    claimed = queue.claim_next(datetime.now(UTC))
    if claimed is None:
        raise RuntimeError("Capture queue did not return the seeded item")
    queue.complete(queued.id)
    return queue


def _payload(inspection_id: str, capture_id: str) -> dict[str, object]:
    return {
        "inspectionId": inspection_id,
        "captureId": capture_id,
        "status": "Pass",
        "evidence": {"recordHashSha256": "b" * 64},
    }
