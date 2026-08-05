"""Distance utilities for deterministic measurement tests."""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt


@dataclass(frozen=True, slots=True)
class Point3D:
    """A point in millimetre-space."""

    x_mm: float
    y_mm: float
    z_mm: float


def euclidean_distance_mm(first: Point3D, second: Point3D) -> float:
    """Return the straight-line distance between two 3D points in millimetres."""

    delta_x = second.x_mm - first.x_mm
    delta_y = second.y_mm - first.y_mm
    delta_z = second.z_mm - first.z_mm
    return sqrt((delta_x * delta_x) + (delta_y * delta_y) + (delta_z * delta_z))


def projected_distance_mm(first: Point3D, second: Point3D) -> float:
    """Return distance projected onto the flattened XY garment plane."""

    delta_x = second.x_mm - first.x_mm
    delta_y = second.y_mm - first.y_mm
    return sqrt((delta_x * delta_x) + (delta_y * delta_y))


def polyline_distance_mm(points: tuple[Point3D, ...]) -> float:
    """Return total distance along an ordered polyline."""

    if len(points) < 2:
        return 0.0
    return sum(
        euclidean_distance_mm(first, second)
        for first, second in zip(points, points[1:], strict=True)
    )
