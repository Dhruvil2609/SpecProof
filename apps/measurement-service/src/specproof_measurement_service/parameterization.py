"""2D surface parameterisation with preserved image and 3D mappings."""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import cast

import numpy as np

from specproof_measurement_service.point_cloud import PlaneModel


@dataclass(frozen=True)
class SurfaceMapPoint:
    """One preserved mapping from image pixel to 3D point and 2D UV coordinate."""

    pixel_x: int
    pixel_y: int
    x_metres: float
    y_metres: float
    z_metres: float
    u_mm: float
    v_mm: float


@dataclass(frozen=True)
class SurfaceParameterization:
    """Flattened surface coordinate map for measurement paths."""

    points: tuple[SurfaceMapPoint, ...]
    u_min_mm: float
    u_max_mm: float
    v_min_mm: float
    v_max_mm: float
    mapped_pixel_count: int
    area_distortion_percent: float
    coordinate_system: str = "support_plane_uv_mm"


def parameterize_surface(
    *,
    points: np.ndarray,
    garment_mask: np.ndarray,
    support_plane: PlaneModel,
) -> SurfaceParameterization:
    """Project segmented 3D garment points onto a stable support-plane UV basis."""

    _validate_points(points)
    _validate_mask(garment_mask, points.shape[:2])
    normal, u_axis, v_axis = _plane_basis(support_plane)
    _ = normal
    coordinates = np.argwhere(garment_mask)
    mapped: list[SurfaceMapPoint] = []
    raw_uv: list[tuple[float, float]] = []
    for pixel_y, pixel_x in coordinates:
        point = points[int(pixel_y), int(pixel_x)].astype(np.float64)
        if not np.all(np.isfinite(point)):
            continue
        u_metres = cast(float, np.dot(point, u_axis))
        v_metres = cast(float, np.dot(point, v_axis))
        raw_uv.append((u_metres, v_metres))
        mapped.append(
            SurfaceMapPoint(
                pixel_x=int(pixel_x),
                pixel_y=int(pixel_y),
                x_metres=float(point[0]),
                y_metres=float(point[1]),
                z_metres=float(point[2]),
                u_mm=u_metres * 1000.0,
                v_mm=v_metres * 1000.0,
            )
        )

    if not mapped:
        return SurfaceParameterization(
            points=(),
            u_min_mm=0.0,
            u_max_mm=0.0,
            v_min_mm=0.0,
            v_max_mm=0.0,
            mapped_pixel_count=0,
            area_distortion_percent=0.0,
        )

    u_min = min(u for u, _ in raw_uv)
    v_min = min(v for _, v in raw_uv)
    normalized = tuple(
        SurfaceMapPoint(
            pixel_x=point.pixel_x,
            pixel_y=point.pixel_y,
            x_metres=point.x_metres,
            y_metres=point.y_metres,
            z_metres=point.z_metres,
            u_mm=point.u_mm - (u_min * 1000.0),
            v_mm=point.v_mm - (v_min * 1000.0),
        )
        for point in mapped
    )
    u_values = [point.u_mm for point in normalized]
    v_values = [point.v_mm for point in normalized]
    return SurfaceParameterization(
        points=normalized,
        u_min_mm=min(u_values),
        u_max_mm=max(u_values),
        v_min_mm=min(v_values),
        v_max_mm=max(v_values),
        mapped_pixel_count=len(normalized),
        area_distortion_percent=_area_distortion_percent(points, garment_mask, normalized),
    )


def mapping_by_pixel(
    parameterization: SurfaceParameterization,
) -> dict[tuple[int, int], SurfaceMapPoint]:
    """Index surface mappings by `(pixel_x, pixel_y)` for landmark lookup."""

    return {(point.pixel_x, point.pixel_y): point for point in parameterization.points}


def _plane_basis(support_plane: PlaneModel) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    normal = np.array(support_plane.normal, dtype=np.float64)
    normal_length = np.linalg.norm(normal)
    if normal_length == 0:
        raise ValueError("support_plane normal must be non-zero")
    normal /= normal_length
    image_x = np.array([1.0, 0.0, 0.0], dtype=np.float64)
    u_axis = image_x - (cast(float, np.dot(image_x, normal)) * normal)
    if np.linalg.norm(u_axis) < 1e-9:
        image_y = np.array([0.0, 1.0, 0.0], dtype=np.float64)
        u_axis = image_y - (cast(float, np.dot(image_y, normal)) * normal)
    u_axis /= np.linalg.norm(u_axis)
    v_axis = np.cross(normal, u_axis)
    v_axis /= np.linalg.norm(v_axis)
    return normal, u_axis, v_axis


def _area_distortion_percent(
    points: np.ndarray,
    garment_mask: np.ndarray,
    mapped: tuple[SurfaceMapPoint, ...],
) -> float:
    by_pixel = {(point.pixel_x, point.pixel_y): point for point in mapped}
    ratios: list[float] = []
    height, width = garment_mask.shape
    for y in range(height):
        for x in range(width):
            current = by_pixel.get((x, y))
            if current is None:
                continue
            if x + 1 < width and garment_mask[y, x + 1]:
                right = by_pixel.get((x + 1, y))
                if right is not None:
                    ratios.append(_distance_ratio(points[y, x], points[y, x + 1], current, right))
            if y + 1 < height and garment_mask[y + 1, x]:
                below = by_pixel.get((x, y + 1))
                if below is not None:
                    ratios.append(_distance_ratio(points[y, x], points[y + 1, x], current, below))
    if not ratios:
        return 0.0
    mean_error = cast(float, np.mean(np.abs(np.array(ratios, dtype=np.float64) - 1.0)))
    return mean_error * 100.0


def _distance_ratio(
    first_3d: np.ndarray,
    second_3d: np.ndarray,
    first_2d: SurfaceMapPoint,
    second_2d: SurfaceMapPoint,
) -> float:
    distance_3d = float(np.linalg.norm(first_3d.astype(np.float64) - second_3d.astype(np.float64)))
    distance_2d = sqrt(
        ((first_2d.u_mm - second_2d.u_mm) / 1000.0) ** 2
        + ((first_2d.v_mm - second_2d.v_mm) / 1000.0) ** 2
    )
    if distance_3d == 0:
        return 1.0
    return distance_2d / distance_3d


def _validate_points(points: np.ndarray) -> None:
    if points.ndim != 3 or points.shape[2] != 3:
        raise ValueError("points must be an HxWx3 array")


def _validate_mask(mask: np.ndarray, shape: tuple[int, int]) -> None:
    if mask.dtype != np.bool_ or mask.shape != shape:
        raise ValueError("garment_mask must be a boolean mask matching points")
