"""Perception preprocessing for synthetic and replay RGB-D captures."""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

import cv2
import numpy as np


@dataclass(frozen=True)
class BackgroundModel:
    """Static RGB-D capture-surface background model."""

    color_bgr: np.ndarray
    depth_units: np.ndarray

    def __post_init__(self) -> None:
        if (
            self.color_bgr.dtype != np.uint8
            or self.color_bgr.ndim != 3
            or self.color_bgr.shape[2] != 3
        ):
            raise ValueError("color_bgr must be an HxWx3 uint8 image")
        if self.depth_units.dtype != np.uint16 or self.depth_units.ndim != 2:
            raise ValueError("depth_units must be an HxW uint16 image")
        if self.color_bgr.shape[:2] != self.depth_units.shape:
            raise ValueError("Background color and depth shapes must match")


@dataclass(frozen=True)
class PreprocessingResult:
    """RGB-D preprocessing output."""

    foreground_mask: np.ndarray
    filtered_depth_units: np.ndarray
    smoothed_color_bgr: np.ndarray


def build_background_model(color_bgr: np.ndarray, depth_units: np.ndarray) -> BackgroundModel:
    """Create a validated background model."""

    return BackgroundModel(color_bgr=color_bgr.copy(), depth_units=depth_units.copy())


def subtract_background(
    color_bgr: np.ndarray,
    depth_units: np.ndarray,
    background: BackgroundModel,
    *,
    color_threshold: int = 24,
    depth_threshold_units: int = 25,
) -> np.ndarray:
    """Return a foreground mask from RGB and depth deltas."""

    _validate_frame(color_bgr, depth_units)
    if (
        color_bgr.shape != background.color_bgr.shape
        or depth_units.shape != background.depth_units.shape
    ):
        raise ValueError("Frame and background shapes must match")
    color_delta = np.max(
        np.abs(color_bgr.astype(np.int16) - background.color_bgr.astype(np.int16)),
        axis=2,
    )
    depth_delta = np.abs(depth_units.astype(np.int32) - background.depth_units.astype(np.int32))
    valid_depth = (depth_units > 0) & (background.depth_units > 0)
    return (color_delta >= color_threshold) | ((depth_delta >= depth_threshold_units) & valid_depth)


def filter_depth(
    depth_units: np.ndarray,
    *,
    minimum_units: int = 1,
    maximum_units: int = 10_000,
    median_kernel_size: int = 3,
) -> np.ndarray:
    """Remove invalid and isolated depth values."""

    if depth_units.dtype != np.uint16 or depth_units.ndim != 2:
        raise ValueError("depth_units must be an HxW uint16 image")
    filtered = depth_units.copy()
    filtered[(filtered < minimum_units) | (filtered > maximum_units)] = 0
    if median_kernel_size % 2 == 0 or median_kernel_size < 1:
        raise ValueError("median_kernel_size must be a positive odd number")
    if median_kernel_size > 1:
        filtered = cv2.medianBlur(filtered, median_kernel_size)
    return filtered


def refine_rgb_depth_registration(
    mask: np.ndarray,
    *,
    shift_x: int = 0,
    shift_y: int = 0,
) -> np.ndarray:
    """Apply integer-pixel registration refinement to a mask."""

    if mask.dtype != np.bool_ or mask.ndim != 2:
        raise ValueError("mask must be a boolean HxW array")
    refined = np.zeros_like(mask, dtype=np.bool_)
    height, width = mask.shape
    source_y_start = max(0, -shift_y)
    source_y_end = min(height, height - shift_y)
    source_x_start = max(0, -shift_x)
    source_x_end = min(width, width - shift_x)
    target_y_start = max(0, shift_y)
    target_y_end = target_y_start + (source_y_end - source_y_start)
    target_x_start = max(0, shift_x)
    target_x_end = target_x_start + (source_x_end - source_x_start)
    if source_y_end > source_y_start and source_x_end > source_x_start:
        refined[target_y_start:target_y_end, target_x_start:target_x_end] = mask[
            source_y_start:source_y_end,
            source_x_start:source_x_end,
        ]
    return refined


def smooth_color(color_bgr: np.ndarray, *, kernel_size: int = 3) -> np.ndarray:
    """Reduce RGB noise while preserving image dimensions."""

    if color_bgr.dtype != np.uint8 or color_bgr.ndim != 3 or color_bgr.shape[2] != 3:
        raise ValueError("color_bgr must be an HxWx3 uint8 image")
    if kernel_size % 2 == 0 or kernel_size < 1:
        raise ValueError("kernel_size must be a positive odd number")
    return cast(np.ndarray, cv2.GaussianBlur(color_bgr, (kernel_size, kernel_size), sigmaX=0))


def preprocess_rgbd(
    color_bgr: np.ndarray,
    depth_units: np.ndarray,
    background: BackgroundModel,
) -> PreprocessingResult:
    """Run deterministic Phase 3 preprocessing on one aligned RGB-D frame."""

    filtered_depth = filter_depth(depth_units)
    foreground_mask = subtract_background(color_bgr, filtered_depth, background)
    return PreprocessingResult(
        foreground_mask=foreground_mask,
        filtered_depth_units=filtered_depth,
        smoothed_color_bgr=smooth_color(color_bgr),
    )


def _validate_frame(color_bgr: np.ndarray, depth_units: np.ndarray) -> None:
    if color_bgr.dtype != np.uint8 or color_bgr.ndim != 3 or color_bgr.shape[2] != 3:
        raise ValueError("color_bgr must be an HxWx3 uint8 image")
    if depth_units.dtype != np.uint16 or depth_units.ndim != 2:
        raise ValueError("depth_units must be an HxW uint16 image")
    if color_bgr.shape[:2] != depth_units.shape:
        raise ValueError("Color and depth shapes must match")
