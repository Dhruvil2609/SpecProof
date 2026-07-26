from datetime import timezone

import pytest

from specproof_capture_service import CaptureMetadata


@pytest.mark.unit
def test_capture_metadata_default_timestamp_is_timezone_aware_utc() -> None:
    metadata = CaptureMetadata(
        capture_id="capture-001",
        station_id="station-001",
        camera_serial="camera-001",
        checksum_sha256="abc123",
    )

    assert metadata.captured_at_utc.tzinfo == timezone.utc
