from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from specproof_capture_service.inspection_queue import (
    InspectionQueueState,
    OfflineInspectionQueue,
)
from specproof_capture_service.offline_queue import OfflineCaptureQueue
from specproof_capture_service.synchronization import InspectionResultSynchronizer


class RecordingPlatformClient:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.submissions: list[dict[str, object]] = []

    def submit_inspection(
        self,
        *,
        payload: dict[str, object],
        payload_hash_sha256: str,
        idempotency_key: str,
    ) -> dict[str, object]:
        if self.fail:
            raise ConnectionError("platform unavailable")
        self.submissions.append(
            {
                "payload": payload,
                "payloadHashSha256": payload_hash_sha256,
                "idempotencyKey": idempotency_key,
            }
        )
        return {"inspectionId": payload["inspectionId"]}


@pytest.mark.unit
def test_inspection_queue_recovers_interrupted_submission(tmp_path: Path) -> None:
    database_path = tmp_path / "inspection-results.db"
    queue = OfflineInspectionQueue(database_path)
    item = queue.enqueue(
        capture_id="capture-1",
        inspection_id="inspection-1",
        payload=_payload("inspection-1"),
    )
    claimed = queue.claim_for_captures(("capture-1",))
    assert claimed is not None
    assert claimed.state == InspectionQueueState.SUBMITTING
    queue.close()

    recovered = OfflineInspectionQueue(database_path)
    restored = recovered.get(item.id)
    assert restored is not None
    assert restored.state == InspectionQueueState.RETRYABLE_FAILURE
    assert restored.last_error == "Submission interrupted by process restart"


@pytest.mark.unit
def test_inspection_queue_replay_is_immutable_and_idempotent(tmp_path: Path) -> None:
    queue = OfflineInspectionQueue(tmp_path / "inspection-results.db")
    original = queue.enqueue(
        capture_id="capture-1",
        inspection_id="inspection-1",
        payload=_payload("inspection-1"),
    )

    replay = queue.enqueue(
        capture_id="capture-1",
        inspection_id="inspection-1",
        payload=_payload("inspection-1"),
    )

    assert replay == original
    assert replay.verify_hash() is True
    with pytest.raises(ValueError, match="Conflicting"):
        queue.enqueue(
            capture_id="capture-1",
            inspection_id="inspection-1",
            payload={**_payload("inspection-1"), "status": "Fail"},
        )


@pytest.mark.unit
def test_result_synchronizer_waits_for_capture_then_completes(tmp_path: Path) -> None:
    package_path = tmp_path / "capture.spcapture"
    package_path.write_bytes(b"capture")
    capture_queue = OfflineCaptureQueue(tmp_path / "captures.db")
    capture = capture_queue.enqueue("capture-1", package_path, "a" * 64)
    result_queue = OfflineInspectionQueue(tmp_path / "inspection-results.db")
    result = result_queue.enqueue(
        capture_id="capture-1",
        inspection_id="inspection-1",
        payload=_payload("inspection-1"),
    )
    platform = RecordingPlatformClient()
    synchronizer = InspectionResultSynchronizer(
        capture_queue=capture_queue,
        result_queue=result_queue,
        platform_client=platform,
    )

    assert synchronizer.synchronize_once() is False
    claimed_capture = capture_queue.claim_next(datetime.now(UTC))
    assert claimed_capture is not None
    capture_queue.complete(capture.id)

    assert synchronizer.synchronize_once() is True
    delivered = result_queue.get(result.id)
    assert delivered is not None
    assert delivered.state == InspectionQueueState.COMPLETED
    assert platform.submissions[0]["idempotencyKey"] == "inspection-1"


@pytest.mark.unit
def test_result_synchronizer_retries_then_dead_letters(tmp_path: Path) -> None:
    package_path = tmp_path / "capture.spcapture"
    package_path.write_bytes(b"capture")
    capture_queue = OfflineCaptureQueue(tmp_path / "captures.db")
    capture = capture_queue.enqueue("capture-1", package_path, "a" * 64)
    claimed_capture = capture_queue.claim_next(datetime.now(UTC))
    assert claimed_capture is not None
    capture_queue.complete(capture.id)
    result_queue = OfflineInspectionQueue(
        tmp_path / "inspection-results.db",
        maximum_attempts=1,
    )
    result = result_queue.enqueue(
        capture_id="capture-1",
        inspection_id="inspection-1",
        payload=_payload("inspection-1"),
    )
    synchronizer = InspectionResultSynchronizer(
        capture_queue=capture_queue,
        result_queue=result_queue,
        platform_client=RecordingPlatformClient(fail=True),
    )

    assert synchronizer.synchronize_once() is False
    failed = result_queue.get(result.id)
    assert failed is not None
    assert failed.state == InspectionQueueState.DEAD_LETTER

    result_queue.retry_dead_letter(result.id)
    retried = result_queue.get(result.id)
    assert retried is not None
    assert retried.state == InspectionQueueState.RETRYABLE_FAILURE


def _payload(inspection_id: str) -> dict[str, object]:
    return {
        "inspectionId": inspection_id,
        "captureId": "capture-1",
        "status": "Pass",
        "evidence": {"recordHashSha256": "b" * 64},
    }
