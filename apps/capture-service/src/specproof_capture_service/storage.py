"""Object storage abstraction for capture packages."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

import boto3


class CaptureObjectStore(Protocol):
    """Capture object storage operations."""

    @property
    def encrypted(self) -> bool:
        """Return whether uploaded objects are encrypted at rest."""
        ...

    def upload(
        self,
        *,
        package_path: Path,
        object_key: str,
        checksum_sha256: str,
    ) -> None:
        """Upload a capture package."""


class S3CaptureObjectStore:
    """S3-compatible capture storage implementation."""

    def __init__(
        self,
        *,
        bucket_name: str,
        endpoint_url: str | None = None,
        region_name: str = "us-east-1",
        server_side_encryption: str | None = None,
        kms_key_id: str | None = None,
        require_encryption: bool = False,
    ) -> None:
        if server_side_encryption not in {None, "AES256", "aws:kms"}:
            raise ValueError("server_side_encryption must be AES256 or aws:kms")
        if server_side_encryption == "aws:kms" and not kms_key_id:
            raise ValueError("kms_key_id is required for aws:kms encryption")
        if require_encryption and server_side_encryption is None:
            raise ValueError("Production capture storage requires server-side encryption")
        if require_encryption and endpoint_url is not None and not endpoint_url.startswith("https://"):
            raise ValueError("Production capture storage requires an HTTPS endpoint")
        self._bucket_name = bucket_name
        self._server_side_encryption = server_side_encryption
        self._kms_key_id = kms_key_id
        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            region_name=region_name,
        )

    @property
    def encrypted(self) -> bool:
        """Return whether S3 server-side encryption is configured."""

        return self._server_side_encryption is not None

    def upload(
        self,
        *,
        package_path: Path,
        object_key: str,
        checksum_sha256: str,
    ) -> None:
        """Upload with immutable checksum metadata."""

        extra_args: dict[str, object] = {
            "ContentType": "application/vnd.specproof.capture+zip",
            "Metadata": {"sha256": checksum_sha256},
        }
        if self._server_side_encryption is not None:
            extra_args["ServerSideEncryption"] = self._server_side_encryption
        if self._kms_key_id is not None:
            extra_args["SSEKMSKeyId"] = self._kms_key_id
        self._client.upload_file(
            str(package_path),
            self._bucket_name,
            object_key,
            ExtraArgs=extra_args,
        )
