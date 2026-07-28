"""Deterministic multi-frame fusion."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from specproof_capture_service.models import CameraFrame


def fuse_depth_median(frames: Sequence[CameraFrame]) -> np.ndarray:
    """Fuse valid depth values using a per-pixel median."""

    if not frames:
        raise ValueError("At least one frame is required")
    expected_shape = frames[0].depth_units.shape
    if any(frame.depth_units.shape != expected_shape for frame in frames):
        raise ValueError("All depth frames must have the same shape")

    stack = np.stack([frame.depth_units for frame in frames]).astype(np.float64)
    stack[stack == 0] = np.nan
    with np.errstate(all="ignore"):
        fused = np.nanmedian(stack, axis=0)
    return np.nan_to_num(fused, nan=0.0).round().astype(np.uint16)


def select_midpoint_color(frames: Sequence[CameraFrame]) -> np.ndarray:
    """Return the temporal midpoint colour frame."""

    if not frames:
        raise ValueError("At least one frame is required")
    return frames[len(frames) // 2].color_bgr.copy()
