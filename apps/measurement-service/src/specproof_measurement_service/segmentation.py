"""Deterministic garment segmentation baseline for synthetic and replay captures."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

import numpy as np


class GarmentCategory(StrEnum):
    """Supported garment category labels."""

    T_SHIRT = "t_shirt"
    UNKNOWN = "unknown"


class GarmentOrientation(StrEnum):
    """Supported garment orientation labels."""

    FRONT = "front"
    BACK = "back"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class BoundingBox:
    """Axis-aligned image-space bounding box."""

    left: int
    top: int
    width: int
    height: int


@dataclass(frozen=True)
class SegmentationResult:
    """Garment segmentation output used by later perception stages."""

    mask: np.ndarray
    boundary: np.ndarray
    bounding_box: BoundingBox | None
    category: GarmentCategory
    orientation: GarmentOrientation
    confidence: float

    @property
    def area_pixels(self) -> int:
        """Return the number of foreground garment pixels."""

        return int(np.count_nonzero(self.mask))


def segment_garment(
    *,
    foreground_mask: np.ndarray,
    depth_garment_mask: np.ndarray,
    minimum_area_pixels: int = 16,
) -> SegmentationResult:
    """Segment the garment by fusing RGB foreground and depth-above-plane masks."""

    _validate_mask(foreground_mask, "foreground_mask")
    _validate_mask(depth_garment_mask, "depth_garment_mask")
    if foreground_mask.shape != depth_garment_mask.shape:
        raise ValueError("foreground_mask and depth_garment_mask shapes must match")
    fused = foreground_mask & depth_garment_mask
    component = largest_connected_component(fused)
    if int(np.count_nonzero(component)) < minimum_area_pixels:
        empty = np.zeros_like(foreground_mask, dtype=np.bool_)
        return SegmentationResult(
            mask=empty,
            boundary=empty,
            bounding_box=None,
            category=GarmentCategory.UNKNOWN,
            orientation=GarmentOrientation.UNKNOWN,
            confidence=0.0,
        )

    boundary = extract_boundary(component)
    bounding_box = compute_bounding_box(component)
    category, category_confidence = classify_garment(component, bounding_box)
    orientation, orientation_confidence = detect_orientation(component, bounding_box)
    confidence = float(min(category_confidence, orientation_confidence, 1.0))
    return SegmentationResult(
        mask=component,
        boundary=boundary,
        bounding_box=bounding_box,
        category=category,
        orientation=orientation,
        confidence=confidence,
    )


def largest_connected_component(mask: np.ndarray) -> np.ndarray:
    """Return the largest 4-connected foreground component."""

    _validate_mask(mask, "mask")
    visited = np.zeros_like(mask, dtype=np.bool_)
    largest: list[tuple[int, int]] = []
    height, width = mask.shape
    for y_coordinate in range(height):
        for x_coordinate in range(width):
            if visited[y_coordinate, x_coordinate] or not mask[y_coordinate, x_coordinate]:
                continue
            component = _flood_fill(mask, visited, y_coordinate, x_coordinate)
            if len(component) > len(largest):
                largest = component
    output = np.zeros_like(mask, dtype=np.bool_)
    for y_coordinate, x_coordinate in largest:
        output[y_coordinate, x_coordinate] = True
    return output


def extract_boundary(mask: np.ndarray) -> np.ndarray:
    """Extract a one-pixel garment boundary from a binary mask."""

    _validate_mask(mask, "mask")
    if not np.any(mask):
        return np.zeros_like(mask, dtype=np.bool_)
    eroded = mask.copy()
    eroded[1:-1, 1:-1] = (
        mask[1:-1, 1:-1]
        & mask[:-2, 1:-1]
        & mask[2:, 1:-1]
        & mask[1:-1, :-2]
        & mask[1:-1, 2:]
    )
    eroded[0, :] = False
    eroded[-1, :] = False
    eroded[:, 0] = False
    eroded[:, -1] = False
    return mask & ~eroded


def compute_bounding_box(mask: np.ndarray) -> BoundingBox | None:
    """Compute the foreground bounding box."""

    _validate_mask(mask, "mask")
    coordinates = np.argwhere(mask)
    if coordinates.size == 0:
        return None
    y_min = int(np.min(coordinates[:, 0]))
    y_max = int(np.max(coordinates[:, 0]))
    x_min = int(np.min(coordinates[:, 1]))
    x_max = int(np.max(coordinates[:, 1]))
    return BoundingBox(
        left=x_min,
        top=y_min,
        width=x_max - x_min + 1,
        height=y_max - y_min + 1,
    )


def classify_garment(
    mask: np.ndarray,
    bounding_box: BoundingBox | None = None,
) -> tuple[GarmentCategory, float]:
    """Classify a garment using a deterministic T-shirt silhouette baseline."""

    _validate_mask(mask, "mask")
    box = bounding_box or compute_bounding_box(mask)
    if box is None:
        return GarmentCategory.UNKNOWN, 0.0
    area = int(np.count_nonzero(mask))
    coverage = area / float(box.width * box.height)
    aspect_ratio = box.width / float(box.height)
    if 0.85 <= aspect_ratio <= 2.80 and 0.35 <= coverage <= 0.92:
        confidence = 1.0 - min(abs(aspect_ratio - 1.35) / 2.0, 0.4)
        confidence -= min(abs(coverage - 0.68), 0.3)
        return GarmentCategory.T_SHIRT, float(max(0.50, min(confidence, 0.98)))
    return GarmentCategory.UNKNOWN, 0.25


def detect_orientation(
    mask: np.ndarray,
    bounding_box: BoundingBox | None = None,
) -> tuple[GarmentOrientation, float]:
    """Detect front/back orientation from neckline indentation geometry."""

    _validate_mask(mask, "mask")
    box = bounding_box or compute_bounding_box(mask)
    if box is None or box.height < 4 or box.width < 4:
        return GarmentOrientation.UNKNOWN, 0.0
    cropped = mask[box.top : box.top + box.height, box.left : box.left + box.width]
    top_band_height = max(1, box.height // 5)
    shoulder_band_start = min(box.height - 1, top_band_height)
    shoulder_band_end = min(box.height, shoulder_band_start + top_band_height)
    top_band = cropped[:top_band_height, :]
    shoulder_band = cropped[shoulder_band_start:shoulder_band_end, :]
    center_start = box.width // 3
    center_end = max(center_start + 1, (box.width * 2) // 3)
    top_center_fill = float(np.mean(top_band[:, center_start:center_end]))
    shoulder_center_fill = float(np.mean(shoulder_band[:, center_start:center_end]))
    neckline_drop = shoulder_center_fill - top_center_fill
    if neckline_drop >= 0.25:
        return GarmentOrientation.FRONT, float(min(0.99, 0.70 + neckline_drop))
    if neckline_drop <= 0.08 and shoulder_center_fill >= 0.70:
        return GarmentOrientation.BACK, 0.70
    return GarmentOrientation.UNKNOWN, 0.35


def segmentation_iou(predicted: np.ndarray, expected: np.ndarray) -> float:
    """Calculate intersection-over-union for binary segmentation masks."""

    _validate_mask(predicted, "predicted")
    _validate_mask(expected, "expected")
    if predicted.shape != expected.shape:
        raise ValueError("predicted and expected shapes must match")
    union = int(np.count_nonzero(predicted | expected))
    if union == 0:
        return 1.0
    intersection = int(np.count_nonzero(predicted & expected))
    return intersection / float(union)


def _flood_fill(
    mask: np.ndarray,
    visited: np.ndarray,
    start_y: int,
    start_x: int,
) -> list[tuple[int, int]]:
    stack = [(start_y, start_x)]
    component: list[tuple[int, int]] = []
    height, width = mask.shape
    while stack:
        y_coordinate, x_coordinate = stack.pop()
        if (
            y_coordinate < 0
            or y_coordinate >= height
            or x_coordinate < 0
            or x_coordinate >= width
            or visited[y_coordinate, x_coordinate]
            or not mask[y_coordinate, x_coordinate]
        ):
            continue
        visited[y_coordinate, x_coordinate] = True
        component.append((y_coordinate, x_coordinate))
        stack.extend(
            (
                (y_coordinate - 1, x_coordinate),
                (y_coordinate + 1, x_coordinate),
                (y_coordinate, x_coordinate - 1),
                (y_coordinate, x_coordinate + 1),
            )
        )
    return component


def _validate_mask(mask: np.ndarray, name: str) -> None:
    if mask.dtype != np.bool_ or mask.ndim != 2:
        raise ValueError(f"{name} must be a boolean HxW array")
