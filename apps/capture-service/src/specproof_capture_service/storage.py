"""Object storage abstraction for capture packages."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

import boto3


class CaptureObjectStore(Protocol):
    """Capture object storage operations."""

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
    ) -> None:
        self._bucket_name = bucket_name
        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            region_name=region_name,
        )

    def upload(
        self,
        *,
        package_path: Path,
        object_key: str,
        checksum_sha256: str,
    ) -> None:
        """Upload with immutable checksum metadata."""

        self._client.upload_file(
            str(package_path),
            self._bucket_name,
            object_key,
            ExtraArgs={
                "ContentType": "application/vnd.specproof.capture+zip",
                "Metadata": {"sha256": checksum_sha256},
            },
        )
