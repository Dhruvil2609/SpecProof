"""Point-cloud and surface utilities for RGB-D perception."""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import cast

import numpy as np
from specproof_capture_service.models import CameraIntrinsics


@dataclass(frozen=True)
class PlaneModel:
    """Plane equation ax + by + cz + d = 0."""

    normal: tuple[float, float, float]
    offset: float
    rms_mm: float


def organized_point_cloud(
    depth_units: np.ndarray,
    *,
    depth_scale_metres: float,
    intrinsics: CameraIntrinsics,
) -> np.ndarray:
    """Project an aligned depth image into an organized XYZ point cloud."""

    if depth_units.dtype != np.uint16 or depth_units.ndim != 2:
        raise ValueError("depth_units must be an HxW uint16 image")
    height, width = depth_units.shape
    if intrinsics.width != width or intrinsics.height != height:
        raise ValueError("Intrinsics dimensions must match depth image")
    z = depth_units.astype(np.float64) * depth_scale_metres
    x_axis = np.arange(width, dtype=np.float64)
    y_axis = np.arange(height, dtype=np.float64)
    x_coordinates, y_coordinates = cast(
        tuple[np.ndarray, np.ndarray],
        np.meshgrid(x_axis, y_axis),
    )
    x = (x_coordinates - intrinsics.ppx) * z / intrinsics.fx
    y = (y_coordinates - intrinsics.ppy) * z / intrinsics.fy
    points = np.stack((x, y, z), axis=2)
    points[depth_units == 0] = np.nan
    return points.astype(np.float32)


def estimate_normals(points: np.ndarray) -> np.ndarray:
    """Estimate organized point-cloud normals using local gradients."""

    if points.ndim != 3 or points.shape[2] != 3:
        raise ValueError("points must be an HxWx3 array")
    gradient_y, gradient_x = np.gradient(points.astype(np.float64), axis=(0, 1))
    normals = np.cross(gradient_x, gradient_y)
    lengths = np.linalg.norm(normals, axis=2, keepdims=True)
    with np.errstate(invalid="ignore", divide="ignore"):
        normals = normals / lengths
    normals[~np.isfinite(normals)] = 0.0
    return normals.astype(np.float32)


def detect_support_plane(points: np.ndarray, mask: np.ndarray) -> PlaneModel:
    """Fit a least-squares support plane to selected points."""

    if points.ndim != 3 or points.shape[2] != 3:
        raise ValueError("points must be an HxWx3 array")
    if mask.dtype != np.bool_ or mask.shape != points.shape[:2]:
        raise ValueError("mask must be a boolean array matching point dimensions")
    selected = points[mask]
    selected = selected[np.all(np.isfinite(selected), axis=1)]
    if selected.shape[0] < 3:
        raise ValueError("At least three valid points are required")
    centroid = np.mean(selected, axis=0)
    _, _, vh = cast(
        tuple[np.ndarray, np.ndarray, np.ndarray],
        np.linalg.svd(selected - centroid, full_matrices=False),
    )
    normal = vh[-1].astype(np.float64)
    if normal[2] < 0:
        normal *= -1.0
    offset = -cast(float, np.dot(normal, centroid))
    distances = selected @ normal + offset
    mean_square_distance = cast(float, np.mean(np.square(distances)))
    rms_metres = sqrt(mean_square_distance)
    rms_mm = rms_metres * 1000.0
    return PlaneModel(
        normal=(float(normal[0]), float(normal[1]), float(normal[2])),
        offset=offset,
        rms_mm=rms_mm,
    )


def separate_garment_from_plane(
    points: np.ndarray,
    plane: PlaneModel,
    *,
    minimum_height_mm: float = 2.0,
) -> np.ndarray:
    """Return mask for points above the support plane."""

    normal = np.array(plane.normal, dtype=np.float64)
    distances_mm = ((points.astype(np.float64) @ normal) + plane.offset) * 1000.0
    return np.isfinite(distances_mm) & (distances_mm >= minimum_height_mm)
