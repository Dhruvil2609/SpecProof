from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

import boto3
import pytest
from botocore.exceptions import BotoCoreError, ClientError
from specproof_capture_service.offline_queue import OfflineCaptureQueue, QueueState
from specproof_capture_service.storage import S3CaptureObjectStore
from specproof_capture_service.synchronization import CaptureSynchronizer, UploadTarget


@pytest.mark.integration
def test_capture_synchronizer_uploads_package_to_minio_and_completes_queue(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    endpoint_url = "http://127.0.0.1:9000"
    access_key = "specproof"
    secret_key = "specproof_dev_password"
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", access_key)
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", secret_key)
    monkeypatch.setenv("AWS_EC2_METADATA_DISABLED", "true")
    bucket_name = f"specproof-test-{uuid4()}"
    client = cast(
        Any,
        boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name="us-east-1",
        ),
    )
    try:
        client.create_bucket(Bucket=bucket_name)
    except (BotoCoreError, ClientError) as error:
        pytest.skip(f"Local MinIO is unavailable: {error}")

    package_path = tmp_path / "capture.spcapture"
    package_path.write_bytes(b"synthetic-capture-package")
    checksum = hashlib.sha256(package_path.read_bytes()).hexdigest()
    queue = OfflineCaptureQueue(tmp_path / "queue.sqlite3")
    queued = queue.enqueue("capture-001", package_path, checksum)

    class PlatformClient:
        completed = False

        def initiate_capture(self, **_: object) -> UploadTarget:
            return UploadTarget("asset-001", "captures/capture-001.spcapture")

        def complete_capture(self, **_: object) -> None:
            self.completed = True

    platform_client = PlatformClient()
    synchronizer = CaptureSynchronizer(
        queue=queue,
        platform_client=platform_client,
        object_store=S3CaptureObjectStore(
            bucket_name=bucket_name,
            endpoint_url=endpoint_url,
        ),
    )

    result = synchronizer.synchronize_once()
    stored = cast(
        dict[str, Any],
        client.head_object(Bucket=bucket_name, Key="captures/capture-001.spcapture"),
    )
    completed = queue.get(queued.id)
    queue.close()

    assert result is True and platform_client.completed is True
    assert stored["Metadata"]["sha256"] == checksum
    assert completed is not None and completed.state == QueueState.COMPLETED
