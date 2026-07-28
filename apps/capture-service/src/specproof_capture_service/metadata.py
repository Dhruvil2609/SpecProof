"""Capture metadata models."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field


class CaptureMetadata(BaseModel):
    """Metadata persisted beside a capture asset."""

    capture_id: str
    station_id: str
    camera_serial: str
    checksum_sha256: str
    captured_at_utc: datetime = Field(default_factory=lambda: datetime.now(UTC))
