"""Offline capture synchronization with the platform."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from specproof_capture_service.capture_package import sha256_file
from specproof_capture_service.inspection_queue import OfflineInspectionQueue
from specproof_capture_service.offline_queue import OfflineCaptureQueue, QueueState
from specproof_capture_service.storage import CaptureObjectStore


@dataclass(frozen=True)
class UploadTarget:
    """Platform-issued capture asset target."""

    asset_id: str
    object_key: str


class PlatformStationClient(Protocol):
    """Platform operations required by a station."""

    def initiate_capture(
        self,
        *,
        capture_id: str,
        package_path: Path,
        checksum_sha256: str,
        idempotency_key: str,
        encrypted: bool,
    ) -> UploadTarget:
        """Create or recover an upload target."""
        ...

    def complete_capture(self, *, asset_id: str, checksum_sha256: str) -> None:
        """Confirm a completed object upload."""
        ...

    def submit_inspection(
        self,
        *,
        payload: dict[str, object],
        payload_hash_sha256: str,
        idempotency_key: str,
    ) -> dict[str, object]:
        """Submit a sealed inspection and evidence payload idempotently."""
        ...


class CaptureSynchronizer:
    """Deliver queued packages exactly once from the station perspective."""

    def __init__(
        self,
        *,
        queue: OfflineCaptureQueue,
        platform_client: PlatformStationClient,
        object_store: CaptureObjectStore,
    ) -> None:
        self._queue = queue
        self._platform_client = platform_client
        self._object_store = object_store

    def synchronize_once(self) -> bool:
        """Process one eligible queue item."""

        item = self._queue.claim_next()
        if item is None:
            return False
        try:
            actual_checksum = sha256_file(item.package_path)
            if actual_checksum != item.package_sha256:
                raise ValueError("Queued capture package checksum does not match")
            target = self._platform_client.initiate_capture(
                capture_id=item.capture_id,
                package_path=item.package_path,
                checksum_sha256=item.package_sha256,
                idempotency_key=item.idempotency_key,
                encrypted=self._object_store.encrypted,
            )
            self._object_store.upload(
                package_path=item.package_path,
                object_key=target.object_key,
                checksum_sha256=item.package_sha256,
            )
            self._platform_client.complete_capture(
                asset_id=target.asset_id,
                checksum_sha256=item.package_sha256,
            )
            self._queue.complete(item.id)
            return True
        except Exception as error:
            self._queue.fail(item.id, str(error))
            return False


class InspectionResultSynchronizer:
    """Deliver durable inspection results after their capture upload completes."""

    def __init__(
        self,
        *,
        capture_queue: OfflineCaptureQueue,
        result_queue: OfflineInspectionQueue,
        platform_client: PlatformStationClient,
    ) -> None:
        self._capture_queue = capture_queue
        self._result_queue = result_queue
        self._platform_client = platform_client

    def synchronize_once(self) -> bool:
        """Submit one eligible inspection result without risking station-side loss."""

        completed_capture_ids = tuple(
            capture_id
            for capture_id in self._result_queue.pending_capture_ids()
            if self._capture_completed(capture_id)
        )
        item = self._result_queue.claim_for_captures(completed_capture_ids)
        if item is None:
            return False
        if not item.verify_hash():
            self._result_queue.dead_letter(item.id, "Inspection payload checksum does not match")
            return False
        try:
            self._platform_client.submit_inspection(
                payload=item.payload(),
                payload_hash_sha256=item.payload_hash_sha256,
                idempotency_key=item.idempotency_key,
            )
            self._result_queue.complete(item.id)
            return True
        except Exception as error:
            self._result_queue.fail(item.id, str(error))
            return False

    def _capture_completed(self, capture_id: str) -> bool:
        capture = self._capture_queue.get_by_capture_id(capture_id)
        return capture is not None and capture.state == QueueState.COMPLETED


class HttpPlatformStationClient:
    """JSON client for the Phase 2 platform synchronization endpoints."""

    def __init__(
        self,
        *,
        base_url: str,
        tenant_id: str,
        station_id: str,
        bearer_token: str,
        timeout_seconds: float = 5.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._tenant_id = tenant_id
        self._station_id = station_id
        self._bearer_token = bearer_token
        self._timeout_seconds = timeout_seconds

    def initiate_capture(
        self,
        *,
        capture_id: str,
        package_path: Path,
        checksum_sha256: str,
        idempotency_key: str,
        encrypted: bool,
    ) -> UploadTarget:
        """Initiate an idempotent capture upload."""

        response = self._request(
            "/api/v1/captures/initiate",
            {
                "tenantId": self._tenant_id,
                "stationId": self._station_id,
                "captureId": capture_id,
                "sizeBytes": package_path.stat().st_size,
                "checksumSha256": checksum_sha256,
                "encrypted": encrypted,
            },
            extra_headers={"Idempotency-Key": idempotency_key},
        )
        return UploadTarget(
            asset_id=str(response["assetId"]),
            object_key=str(response["objectKey"]),
        )

    def complete_capture(self, *, asset_id: str, checksum_sha256: str) -> None:
        """Confirm upload completion."""

        self._request(
            f"/api/v1/captures/{asset_id}/complete",
            {
                "tenantId": self._tenant_id,
                "checksumSha256": checksum_sha256,
            },
        )

    def submit_inspection(
        self,
        *,
        payload: dict[str, object],
        payload_hash_sha256: str,
        idempotency_key: str,
    ) -> dict[str, object]:
        """Submit an integrated inspection and canonical evidence atomically."""

        return self._request(
            "/api/v1/inspections",
            payload,
            extra_headers={
                "Idempotency-Key": idempotency_key,
                "X-Payload-SHA256": payload_hash_sha256,
            },
        )

    def _request(
        self,
        path: str,
        payload: dict[str, object],
        *,
        extra_headers: dict[str, str] | None = None,
    ) -> dict[str, object]:
        headers = {
            "Authorization": f"Bearer {self._bearer_token}",
            "Content-Type": "application/json",
        }
        headers.update(extra_headers or {})
        request = urllib.request.Request(
            f"{self._base_url}{path}",
            data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout_seconds) as response:
                body = response.read()
                return json.loads(body) if body else {}
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            raise ConnectionError(f"Platform returned HTTP {error.code}: {detail[:500]}") from error
