"""Synthetic calibration evaluators for software acceptance gates."""

from __future__ import annotations

from dataclasses import dataclass
from math import acos, degrees
from typing import cast

import numpy as np

from specproof_capture_service.models import CalibrationMetrics, CameraFrame


@dataclass(frozen=True)
class CalibrationScene:
    """Synthetic calibration scene with known artefact and plane properties."""

    frames: tuple[CameraFrame, ...]
    expected_depth_units: int
    artefact_expected_width_px: float
    artefact_observed_width_px: float
    plane_mask: np.ndarray
    lighting_mask: np.ndarray
    expected_alignment_offset_px: float = 1.0


def evaluate_synthetic_calibration(scene: CalibrationScene) -> CalibrationMetrics:
    """Evaluate calibration metrics from synthetic or replay RGB-D frames."""

    if not scene.frames:
        raise ValueError("Calibration scene must contain at least one frame")
    frame = scene.frames[len(scene.frames) // 2]
    _validate_mask(scene.plane_mask, frame.depth_units.shape, "plane_mask")
    _validate_mask(scene.lighting_mask, frame.depth_units.shape, "lighting_mask")

    plane_depth = frame.depth_units[scene.plane_mask]
    if plane_depth.size == 0:
        raise ValueError("Plane mask must select at least one depth pixel")
    plane_depth_mm = plane_depth.astype(np.float64) * frame.depth_scale_metres * 1000.0
    plane_rms_mm = float(np.sqrt(np.mean(np.square(plane_depth_mm - np.mean(plane_depth_mm)))))

    expected_width = scene.artefact_expected_width_px
    if expected_width <= 0:
        raise ValueError("Expected artefact width must be positive")
    scale_error_percent = abs(scene.artefact_observed_width_px - expected_width) / expected_width
    scale_error_percent *= 100.0

    tilt_degrees = _estimate_tilt_degrees(frame.depth_units, scene.plane_mask)
    lighting_variation_percent = _estimate_lighting_variation_percent(
        frame.color_bgr,
        scene.lighting_mask,
    )
    alignment_valid = abs(_estimate_alignment_offset_px(frame.depth_units, scene.plane_mask))
    alignment_valid = alignment_valid <= scene.expected_alignment_offset_px

    return CalibrationMetrics(
        scale_error_percent=float(scale_error_percent),
        plane_rms_mm=plane_rms_mm,
        tilt_degrees=float(tilt_degrees),
        lighting_variation_percent=float(lighting_variation_percent),
        alignment_valid=bool(alignment_valid),
    )


def _validate_mask(mask: np.ndarray, shape: tuple[int, int], name: str) -> None:
    if mask.dtype != np.bool_ or mask.shape != shape:
        raise ValueError(f"{name} must be a boolean mask matching depth shape")


def _estimate_tilt_degrees(depth_units: np.ndarray, plane_mask: np.ndarray) -> float:
    coordinates = np.argwhere(plane_mask)
    if coordinates.shape[0] < 3:
        return 0.0
    y = coordinates[:, 0].astype(np.float64)
    x = coordinates[:, 1].astype(np.float64)
    z = depth_units[plane_mask].astype(np.float64)
    design = np.column_stack((x, y, np.ones_like(x)))
    coefficients, *_ = np.linalg.lstsq(design, z, rcond=None)
    normal = np.array([-coefficients[0], -coefficients[1], 1.0], dtype=np.float64)
    normal /= np.linalg.norm(normal)
    cosine = float(np.clip(np.dot(normal, np.array([0.0, 0.0, 1.0])), -1.0, 1.0))
    return degrees(acos(cosine))


def _estimate_lighting_variation_percent(color_bgr: np.ndarray, lighting_mask: np.ndarray) -> float:
    gray = np.mean(color_bgr.astype(np.float64), axis=2)
    values = gray[lighting_mask]
    if values.size == 0:
        raise ValueError("Lighting mask must select at least one colour pixel")
    mean = cast(float, np.mean(values))
    if mean == 0.0:
        return 0.0
    variation = cast(float, np.std(values))
    return (variation / mean) * 100.0


def _estimate_alignment_offset_px(depth_units: np.ndarray, plane_mask: np.ndarray) -> float:
    depth_edges = np.abs(np.diff(depth_units.astype(np.int32), axis=1)) > 0
    mask_edges = np.abs(np.diff(plane_mask.astype(np.int8), axis=1)) > 0
    depth_positions = np.argwhere(depth_edges)
    mask_positions = np.argwhere(mask_edges)
    if depth_positions.size == 0 or mask_positions.size == 0:
        return 0.0
    depth_mean = float(np.mean(depth_positions[:, 1].astype(np.float64)))
    mask_mean = float(np.mean(mask_positions[:, 1].astype(np.float64)))
    return depth_mean - mask_mean
