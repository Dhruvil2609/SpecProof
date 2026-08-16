from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, cast

import pytest
from specproof_capture_service.storage import S3CaptureObjectStore
from specproof_capture_service.synchronization import HttpPlatformStationClient


class RecordingS3Client:
    def __init__(self) -> None:
        self.extra_args: dict[str, object] | None = None

    def upload_file(
        self,
        filename: str,
        bucket: str,
        key: str,
        *,
        ExtraArgs: dict[str, object],  # noqa: N803
    ) -> None:
        assert Path(filename).is_file()
        assert bucket == "captures"
        assert key == "capture.spcapture"
        self.extra_args = ExtraArgs


@pytest.mark.unit
def test_s3_capture_store_kms_upload_includes_encryption_and_checksum(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = RecordingS3Client()
    monkeypatch.setattr(
        "specproof_capture_service.storage.boto3.client",
        lambda *_args, **_kwargs: client,
    )
    package = tmp_path / "capture.spcapture"
    package.write_bytes(b"capture")
    checksum = hashlib.sha256(package.read_bytes()).hexdigest()
    store = S3CaptureObjectStore(
        bucket_name="captures",
        endpoint_url="https://objects.example",
        server_side_encryption="aws:kms",
        kms_key_id="capture-key",
        require_encryption=True,
    )

    store.upload(
        package_path=package,
        object_key="capture.spcapture",
        checksum_sha256=checksum,
    )

    assert store.encrypted is True
    assert client.extra_args == {
        "ContentType": "application/vnd.specproof.capture+zip",
        "Metadata": {"sha256": checksum},
        "ServerSideEncryption": "aws:kms",
        "SSEKMSKeyId": "capture-key",
    }


@pytest.mark.unit
def test_s3_capture_store_production_without_encryption_rejects_configuration() -> None:
    with pytest.raises(ValueError, match="requires server-side encryption"):
        S3CaptureObjectStore(bucket_name="captures", require_encryption=True)


@pytest.mark.unit
def test_s3_capture_store_production_plain_http_rejects_configuration() -> None:
    with pytest.raises(ValueError, match="HTTPS endpoint"):
        S3CaptureObjectStore(
            bucket_name="captures",
            endpoint_url="http://objects.example",
            server_side_encryption="AES256",
            require_encryption=True,
        )


@pytest.mark.unit
def test_http_platform_client_initiate_capture_reports_encrypted_storage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    package = tmp_path / "capture.spcapture"
    package.write_bytes(b"capture")
    requests: list[dict[str, object]] = []

    class Response:
        def __enter__(self) -> Response:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self) -> bytes:
            return b'{"assetId":"asset-1","objectKey":"capture.spcapture"}'

    def urlopen(request: object, *, timeout: float) -> Response:
        del timeout
        data = cast(Any, request).data
        requests.append(cast(dict[str, object], json.loads(data)))
        return Response()

    monkeypatch.setattr("specproof_capture_service.synchronization.urllib.request.urlopen", urlopen)
    client = HttpPlatformStationClient(
        base_url="https://platform.example",
        tenant_id="tenant-1",
        station_id="station-1",
        bearer_token="token",
    )
    new_checksum = hashlib.sha256(package.read_bytes()).hexdigest()

    client.initiate_capture(
        capture_id="capture-1",
        package_path=package,
        checksum_sha256=new_checksum,
        idempotency_key="capture-1",
        encrypted=True,
    )

    assert requests == [
        {
            "tenantId": "tenant-1",
            "stationId": "station-1",
            "captureId": "capture-1",
            "sizeBytes": 7,
            "checksumSha256": new_checksum,
            "encrypted": True,
        }
    ]
