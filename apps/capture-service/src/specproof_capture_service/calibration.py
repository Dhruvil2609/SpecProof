"""Calibration evaluation and record storage."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

from specproof_capture_service.models import (
    CalibrationMetrics,
    CalibrationMode,
    CalibrationRecord,
    CalibrationThresholds,
    utc_now,
)


def calibration_is_acceptable(
    metrics: CalibrationMetrics,
    thresholds: CalibrationThresholds,
) -> bool:
    """Return whether all calibration gates pass."""

    return (
        metrics.alignment_valid
        and metrics.scale_error_percent <= thresholds.maximum_scale_error_percent
        and metrics.plane_rms_mm <= thresholds.maximum_plane_rms_mm
        and metrics.tilt_degrees <= thresholds.maximum_tilt_degrees
        and metrics.lighting_variation_percent <= thresholds.maximum_lighting_variation_percent
    )


def create_calibration_record(
    *,
    version: int,
    station_id: str,
    camera_serial: str,
    operator_id: str,
    artefact_id: str,
    mode: CalibrationMode,
    metrics: CalibrationMetrics,
    thresholds: CalibrationThresholds,
) -> CalibrationRecord:
    """Create an immutable calibration record and checksum."""

    calibrated_at = utc_now()
    validity = (
        timedelta(days=thresholds.full_validity_days)
        if mode == CalibrationMode.FULL
        else timedelta(hours=thresholds.daily_validity_hours)
    )
    payload = {
        "version": version,
        "station_id": station_id,
        "camera_serial": camera_serial,
        "operator_id": operator_id,
        "artefact_id": artefact_id,
        "mode": mode.value,
        "metrics": metrics.model_dump(mode="json"),
        "calibrated_at_utc": calibrated_at.isoformat(),
        "expires_at_utc": (calibrated_at + validity).isoformat(),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return CalibrationRecord(
        calibration_id=str(uuid4()),
        version=version,
        station_id=station_id,
        camera_serial=camera_serial,
        operator_id=operator_id,
        artefact_id=artefact_id,
        mode=mode,
        metrics=metrics,
        calibrated_at_utc=calibrated_at,
        expires_at_utc=calibrated_at + validity,
        checksum_sha256=hashlib.sha256(canonical).hexdigest(),
        valid=calibration_is_acceptable(metrics, thresholds),
    )


class CalibrationStore:
    """Filesystem-backed immutable calibration store."""

    def __init__(self, root: Path) -> None:
        self._root = root

    def save(self, record: CalibrationRecord) -> Path:
        """Persist a new record without overwriting an existing version."""

        directory = self._root / record.station_id / record.camera_serial
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{record.version:06d}-{record.calibration_id}.json"
        path.write_text(record.model_dump_json(indent=2), encoding="utf-8", newline="\n")
        return path

    def get_active(self, station_id: str, camera_serial: str) -> CalibrationRecord | None:
        """Return the latest valid, unexpired calibration."""

        directory = self._root / station_id / camera_serial
        if not directory.exists():
            return None
        now = utc_now()
        records = [
            CalibrationRecord.model_validate_json(path.read_text(encoding="utf-8"))
            for path in directory.glob("*.json")
        ]
        active = [record for record in records if record.valid and record.expires_at_utc > now]
        return max(active, key=lambda record: record.version, default=None)

    def next_version(self, station_id: str, camera_serial: str) -> int:
        """Return the next immutable version number."""

        directory = self._root / station_id / camera_serial
        if not directory.exists():
            return 1
        versions = [int(path.name.split("-", maxsplit=1)[0]) for path in directory.glob("*.json")]
        return max(versions, default=0) + 1


CalibrationEvaluator = Callable[[str, CalibrationMode], CalibrationMetrics]


def fixed_calibration_evaluator(
    metrics: CalibrationMetrics,
) -> CalibrationEvaluator:
    """Return a deterministic evaluator for mock and replay environments."""

    def evaluate(_: str, __: CalibrationMode) -> CalibrationMetrics:
        return metrics

    return evaluate
