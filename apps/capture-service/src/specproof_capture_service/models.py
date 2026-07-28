"""Typed camera, frame, and calibration models."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, field_validator


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""

    return datetime.now(UTC)


class StreamProfile(BaseModel):
    """RGB-D stream dimensions and frame rate."""

    color_width: int = Field(default=1280, gt=0)
    color_height: int = Field(default=720, gt=0)
    depth_width: int = Field(default=848, gt=0)
    depth_height: int = Field(default=480, gt=0)
    frames_per_second: int = Field(default=30, ge=1, le=90)


class CameraIntrinsics(BaseModel):
    """Pinhole camera intrinsics."""

    width: int = Field(gt=0)
    height: int = Field(gt=0)
    fx: float = Field(gt=0)
    fy: float = Field(gt=0)
    ppx: float
    ppy: float
    distortion_model: str
    coefficients: tuple[float, ...] = ()


class CameraExtrinsics(BaseModel):
    """Rigid transform between depth and colour sensors."""

    rotation: tuple[float, ...] = Field(min_length=9, max_length=9)
    translation_metres: tuple[float, ...] = Field(min_length=3, max_length=3)


class CameraDevice(BaseModel):
    """Enumerated camera information."""

    serial_number: str = Field(min_length=1)
    name: str = Field(min_length=1)
    firmware_version: str
    usb_type: str
    active_profile: StreamProfile | None = None


class CameraFrame(BaseModel):
    """Aligned RGB-D frame in memory."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    frame_id: str
    camera_serial: str
    captured_at_utc: datetime
    color_bgr: np.ndarray
    depth_units: np.ndarray
    depth_scale_metres: float = Field(gt=0)
    color_intrinsics: CameraIntrinsics
    depth_intrinsics: CameraIntrinsics
    depth_to_color: CameraExtrinsics

    @field_validator("captured_at_utc")
    @classmethod
    def validate_utc(cls, value: datetime) -> datetime:
        """Require timezone-aware UTC timestamps."""

        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("captured_at_utc must be timezone-aware")
        return value.astimezone(UTC)

    @field_validator("color_bgr")
    @classmethod
    def validate_color(cls, value: np.ndarray) -> np.ndarray:
        """Require an unsigned 8-bit BGR image."""

        if value.dtype != np.uint8 or value.ndim != 3 or value.shape[2] != 3:
            raise ValueError("color_bgr must be an HxWx3 uint8 array")
        return value

    @field_validator("depth_units")
    @classmethod
    def validate_depth(cls, value: np.ndarray) -> np.ndarray:
        """Require an unsigned 16-bit depth image."""

        if value.dtype != np.uint16 or value.ndim != 2:
            raise ValueError("depth_units must be an HxW uint16 array")
        return value


class CalibrationMode(StrEnum):
    """Supported calibration workflows."""

    DAILY = "daily"
    FULL = "full"


class CalibrationThresholds(BaseModel):
    """Configurable calibration acceptance thresholds."""

    full_validity_days: int = Field(default=30, gt=0)
    daily_validity_hours: int = Field(default=24, gt=0)
    maximum_scale_error_percent: float = Field(default=0.1, gt=0)
    maximum_plane_rms_mm: float = Field(default=2.0, gt=0)
    maximum_tilt_degrees: float = Field(default=0.5, gt=0)
    maximum_lighting_variation_percent: float = Field(default=10.0, gt=0)


class CalibrationMetrics(BaseModel):
    """Measured calibration quality values."""

    scale_error_percent: float = Field(ge=0)
    plane_rms_mm: float = Field(ge=0)
    tilt_degrees: float = Field(ge=0)
    lighting_variation_percent: float = Field(ge=0)
    alignment_valid: bool


class CalibrationRecord(BaseModel):
    """Immutable, versioned calibration record."""

    calibration_id: str
    version: int = Field(gt=0)
    station_id: str
    camera_serial: str
    operator_id: str
    artefact_id: str
    mode: CalibrationMode
    metrics: CalibrationMetrics
    calibrated_at_utc: datetime
    expires_at_utc: datetime
    checksum_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    valid: bool


class CaptureManifest(BaseModel):
    """Platform-neutral capture package manifest."""

    schema_version: int = 1
    capture_id: str
    station_id: str
    camera_serial: str
    captured_at_utc: datetime
    frame_count: int = Field(ge=1)
    profile: StreamProfile
    depth_scale_metres: float = Field(gt=0)
    calibration_id: str
    environment: dict[str, str] = Field(default_factory=dict)
    files: tuple[str, ...]


class StationHealth(BaseModel):
    """Capture station health snapshot."""

    status: str
    checked_at_utc: datetime = Field(default_factory=utc_now)
    camera_status: str
    storage_status: str
    clock_status: str
    offline_queue_depth: int = Field(ge=0)
    detail: str = ""
