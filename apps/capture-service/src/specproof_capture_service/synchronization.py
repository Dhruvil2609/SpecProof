"""Offline capture synchronization with the platform."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from specproof_capture_service.capture_package import sha256_file
from specproof_capture_service.offline_queue import OfflineCaptureQueue
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
    ) -> UploadTarget:
        """Create or recover an upload target."""
        ...

    def complete_capture(self, *, asset_id: str, checksum_sha256: str) -> None:
        """Confirm a completed object upload."""
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
