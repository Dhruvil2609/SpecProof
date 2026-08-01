"""Surface confidence scoring for segmented RGB-D garment data."""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

import numpy as np

from specproof_measurement_service.point_cloud import PlaneModel


@dataclass(frozen=True)
class SurfaceConfidence:
    """Surface quality scores used to decide whether measurement may proceed."""

    overall: float
    valid_depth_ratio: float
    surface_coverage: float
    plane_fit_score: float
    normal_consistency: float
    reason: str


def score_surface_confidence(
    *,
    points: np.ndarray,
    garment_mask: np.ndarray,
    capture_zone_mask: np.ndarray,
    support_plane: PlaneModel,
    normals: np.ndarray | None = None,
    maximum_plane_rms_mm: float = 2.0,
) -> SurfaceConfidence:
    """Score segmented surface quality using depth validity, coverage, and geometry."""

    _validate_points(points)
    _validate_mask(garment_mask, points.shape[:2], "garment_mask")
    _validate_mask(capture_zone_mask, points.shape[:2], "capture_zone_mask")
    if maximum_plane_rms_mm <= 0:
        raise ValueError("maximum_plane_rms_mm must be positive")

    selected = garment_mask & capture_zone_mask
    zone_pixels = int(np.count_nonzero(capture_zone_mask))
    garment_pixels = int(np.count_nonzero(selected))
    if zone_pixels == 0:
        raise ValueError("capture_zone_mask must select at least one pixel")
    if garment_pixels == 0:
        return SurfaceConfidence(
            overall=0.0,
            valid_depth_ratio=0.0,
            surface_coverage=0.0,
            plane_fit_score=0.0,
            normal_consistency=0.0,
            reason="no_garment_surface",
        )

    selected_points = points[selected]
    valid_depth = np.all(np.isfinite(selected_points), axis=1)
    valid_depth_ratio = int(np.count_nonzero(valid_depth)) / float(garment_pixels)
    surface_coverage = garment_pixels / float(zone_pixels)
    plane_fit_score = max(0.0, 1.0 - (support_plane.rms_mm / maximum_plane_rms_mm))
    normal_consistency = (
        _normal_consistency(normals, selected)
        if normals is not None
        else 1.0
    )
    overall = float(
        min(
            valid_depth_ratio,
            plane_fit_score,
            normal_consistency,
            _coverage_score(surface_coverage),
        )
    )
    reason = "ok" if overall >= 0.75 else "low_surface_confidence"
    return SurfaceConfidence(
        overall=overall,
        valid_depth_ratio=float(valid_depth_ratio),
        surface_coverage=float(surface_coverage),
        plane_fit_score=float(plane_fit_score),
        normal_consistency=float(normal_consistency),
        reason=reason,
    )


def _coverage_score(surface_coverage: float) -> float:
    if 0.05 <= surface_coverage <= 0.90:
        return 1.0
    if surface_coverage < 0.05:
        return max(0.0, surface_coverage / 0.05)
    return max(0.0, (1.0 - surface_coverage) / 0.10)


def _normal_consistency(normals: np.ndarray, mask: np.ndarray) -> float:
    if normals.shape != (*mask.shape, 3):
        raise ValueError("normals must be an HxWx3 array matching mask dimensions")
    selected = normals[mask]
    selected = selected[np.all(np.isfinite(selected), axis=1)]
    lengths = np.linalg.norm(selected, axis=1)
    selected = selected[lengths > 0]
    if selected.size == 0:
        return 0.0
    mean_normal = np.mean(selected, axis=0)
    mean_length = np.linalg.norm(mean_normal)
    if mean_length == 0:
        return 0.0
    mean_normal = mean_normal / mean_length
    alignment = np.abs(selected @ mean_normal)
    mean_alignment = cast(float, np.mean(alignment))
    return max(0.0, min(mean_alignment, 1.0))


def _validate_points(points: np.ndarray) -> None:
    if points.ndim != 3 or points.shape[2] != 3:
        raise ValueError("points must be an HxWx3 array")


def _validate_mask(mask: np.ndarray, shape: tuple[int, int], name: str) -> None:
    if mask.dtype != np.bool_ or mask.shape != shape:
        raise ValueError(f"{name} must be a boolean mask matching point dimensions")
