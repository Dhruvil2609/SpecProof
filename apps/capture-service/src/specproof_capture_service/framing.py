"""Capture zone framing validation."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from specproof_capture_service.models import CameraFrame


@dataclass(frozen=True)
class CaptureZone:
    """Rectangular capture zone in image coordinates."""

    left: int
    top: int
    width: int
    height: int
    minimum_foreground_coverage: float = 0.05
    maximum_foreground_coverage: float = 0.95
    minimum_border_clearance_px: int = 2


@dataclass(frozen=True)
class FramingResult:
    """Result of capture-zone validation."""

    valid: bool
    foreground_coverage: float
    border_clearance_px: int
    reason: str


def validate_capture_zone_framing(
    frame: CameraFrame,
    *,
    zone: CaptureZone,
    foreground_mask: np.ndarray,
) -> FramingResult:
    """Validate that foreground content is inside the configured capture zone."""

    if foreground_mask.dtype != np.bool_ or foreground_mask.shape != frame.depth_units.shape:
        raise ValueError("foreground_mask must be a boolean mask matching frame depth shape")
    if zone.width <= 0 or zone.height <= 0:
        raise ValueError("Capture zone width and height must be positive")
    image_height, image_width = frame.depth_units.shape
    if zone.left < 0 or zone.top < 0 or zone.left + zone.width > image_width:
        raise ValueError("Capture zone exceeds image width")
    if zone.top + zone.height > image_height:
        raise ValueError("Capture zone exceeds image height")

    foreground_points = np.argwhere(foreground_mask)
    if foreground_points.size == 0:
        return FramingResult(False, 0.0, 0, "no_foreground")

    zone_mask = np.zeros_like(foreground_mask, dtype=np.bool_)
    zone_mask[zone.top : zone.top + zone.height, zone.left : zone.left + zone.width] = True
    inside_count = int(np.count_nonzero(foreground_mask & zone_mask))
    total_count = int(np.count_nonzero(foreground_mask))
    if inside_count != total_count:
        return FramingResult(False, inside_count / total_count, 0, "foreground_outside_zone")

    y_coordinates = foreground_points[:, 0]
    x_coordinates = foreground_points[:, 1]
    clearance = min(
        int(np.min(x_coordinates) - zone.left),
        int(zone.left + zone.width - 1 - np.max(x_coordinates)),
        int(np.min(y_coordinates) - zone.top),
        int(zone.top + zone.height - 1 - np.max(y_coordinates)),
    )
    coverage = inside_count / float(zone.width * zone.height)
    if coverage < zone.minimum_foreground_coverage:
        return FramingResult(False, coverage, clearance, "foreground_too_small")
    if coverage > zone.maximum_foreground_coverage:
        return FramingResult(False, coverage, clearance, "foreground_too_large")
    if clearance < zone.minimum_border_clearance_px:
        return FramingResult(False, coverage, clearance, "foreground_too_close_to_border")
    return FramingResult(True, coverage, clearance, "ok")
