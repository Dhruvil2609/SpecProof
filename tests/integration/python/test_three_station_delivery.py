from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from uuid import uuid4

import pytest
from specproof_capture_service.inspection_queue import OfflineInspectionQueue
from specproof_capture_service.offline_queue import OfflineCaptureQueue
from specproof_capture_service.synchronization import InspectionResultSynchronizer


class ConcurrentPlatformClient:
    def __init__(self) -> None:
        self._lock = Lock()
        self.submissions: list[dict[str, object]] = []

    def submit_inspection(
        self,
        *,
        payload: dict[str, object],
        payload_hash_sha256: str,
        idempotency_key: str,
    ) -> dict[str, object]:
        with self._lock:
            self.submissions.append(
                {
                    "payload": payload,
                    "payloadHashSha256": payload_hash_sha256,
                    "idempotencyKey": idempotency_key,
                }
            )
        return {"inspectionId": payload["inspectionId"]}


@pytest.mark.integration
def test_three_stations_submit_unique_inspections_concurrently(tmp_path: Path) -> None:
    platform = ConcurrentPlatformClient()
    synchronizers: list[InspectionResultSynchronizer] = []
    capture_queues: list[OfflineCaptureQueue] = []
    result_queues: list[OfflineInspectionQueue] = []
    expected_station_ids: set[str] = set()
    expected_inspection_ids: set[str] = set()
    for index in range(3):
        station_id = str(uuid4())
        capture_id = str(uuid4())
        inspection_id = str(uuid4())
        expected_station_ids.add(station_id)
        expected_inspection_ids.add(inspection_id)
        station_root = tmp_path / f"station-{index}"
        package_path = station_root / "capture.spcapture"
        package_path.parent.mkdir(parents=True)
        package_path.write_bytes(f"capture-{index}".encode())
        capture_queue = OfflineCaptureQueue(station_root / "captures.db")
        capture = capture_queue.enqueue(capture_id, package_path, "a" * 64)
        assert capture_queue.claim_next(datetime.now(UTC)) is not None
        capture_queue.complete(capture.id)
        result_queue = OfflineInspectionQueue(station_root / "inspection-results.db")
        capture_queues.append(capture_queue)
        result_queues.append(result_queue)
        result_queue.enqueue(
            capture_id=capture_id,
            inspection_id=inspection_id,
            payload={
                "tenantId": "11111111-1111-1111-1111-111111111111",
                "stationId": station_id,
                "captureId": capture_id,
                "inspectionId": inspection_id,
                "evidence": {"recordHashSha256": "b" * 64},
            },
        )
        synchronizers.append(
            InspectionResultSynchronizer(
                capture_queue=capture_queue,
                result_queue=result_queue,
                platform_client=platform,
            )
        )

    with ThreadPoolExecutor(max_workers=3) as executor:
        delivered = list(executor.map(lambda sync: sync.synchronize_once(), synchronizers))

    assert delivered == [True, True, True]
    submitted_payloads = [submission["payload"] for submission in platform.submissions]
    assert all(isinstance(payload, dict) for payload in submitted_payloads)
    submitted_stations = {
        str(payload["stationId"])
        for payload in submitted_payloads
        if isinstance(payload, dict)
    }
    submitted_inspections = {
        str(payload["inspectionId"])
        for payload in submitted_payloads
        if isinstance(payload, dict)
    }
    assert submitted_stations == expected_station_ids
    assert submitted_inspections == expected_inspection_ids
    for queue in capture_queues:
        queue.close()
    for queue in result_queues:
        queue.close()
