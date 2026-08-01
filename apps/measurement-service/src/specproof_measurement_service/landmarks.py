"""T-shirt landmark vocabulary and deterministic contour heuristics."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

import numpy as np

from specproof_measurement_service.segmentation import BoundingBox, compute_bounding_box


class LandmarkName(StrEnum):
    """Canonical T-shirt landmark names."""

    NECK_LEFT = "neck_left"
    NECK_RIGHT = "neck_right"
    SHOULDER_LEFT = "shoulder_left"
    SHOULDER_RIGHT = "shoulder_right"
    SLEEVE_HEM_LEFT = "sleeve_hem_left"
    SLEEVE_HEM_RIGHT = "sleeve_hem_right"
    SIDE_SEAM_LEFT = "side_seam_left"
    SIDE_SEAM_RIGHT = "side_seam_right"
    HEM_LEFT = "hem_left"
    HEM_RIGHT = "hem_right"


class LandmarkStatus(StrEnum):
    """Landmark detection status."""

    DETECTED = "detected"
    OCCLUDED = "occluded"
    MISSING = "missing"


@dataclass(frozen=True)
class Landmark:
    """Detected landmark in image coordinates."""

    name: LandmarkName
    x: float
    y: float
    confidence: float
    status: LandmarkStatus


@dataclass(frozen=True)
class LandmarkSet:
    """Collection of T-shirt landmarks and seam contour samples."""

    landmarks: tuple[Landmark, ...]
    contour: tuple[tuple[int, int], ...]
    confidence: float
    review_required: bool

    def by_name(self, name: LandmarkName) -> Landmark | None:
        """Return one landmark by canonical name."""

        return next((landmark for landmark in self.landmarks if landmark.name == name), None)


T_SHIRT_LANDMARKS: tuple[LandmarkName, ...] = tuple(LandmarkName)


def detect_tshirt_landmarks(mask: np.ndarray) -> LandmarkSet:
    """Detect a baseline T-shirt landmark set from a binary garment mask."""

    _validate_mask(mask)
    box = compute_bounding_box(mask)
    if box is None:
        missing = tuple(
            Landmark(name=name, x=0.0, y=0.0, confidence=0.0, status=LandmarkStatus.MISSING)
            for name in T_SHIRT_LANDMARKS
        )
        return LandmarkSet(landmarks=missing, contour=(), confidence=0.0, review_required=True)

    contour = extract_contour_points(mask)
    rows = _row_extents(mask)
    landmarks = (
        _neck_landmark(mask, box, left=True),
        _neck_landmark(mask, box, left=False),
        _band_landmark(rows, box, LandmarkName.SHOULDER_LEFT, 0.20, left=True),
        _band_landmark(rows, box, LandmarkName.SHOULDER_RIGHT, 0.20, left=False),
        _band_landmark(rows, box, LandmarkName.SLEEVE_HEM_LEFT, 0.42, left=True),
        _band_landmark(rows, box, LandmarkName.SLEEVE_HEM_RIGHT, 0.42, left=False),
        _band_landmark(rows, box, LandmarkName.SIDE_SEAM_LEFT, 0.68, left=True),
        _band_landmark(rows, box, LandmarkName.SIDE_SEAM_RIGHT, 0.68, left=False),
        _hem_landmark(rows, box, LandmarkName.HEM_LEFT, left=True),
        _hem_landmark(rows, box, LandmarkName.HEM_RIGHT, left=False),
    )
    confidences = [landmark.confidence for landmark in landmarks]
    confidence = float(np.mean(confidences)) if confidences else 0.0
    review_required = any(landmark.status != LandmarkStatus.DETECTED for landmark in landmarks)
    return LandmarkSet(
        landmarks=landmarks,
        contour=contour,
        confidence=confidence,
        review_required=review_required,
    )


def extract_contour_points(mask: np.ndarray) -> tuple[tuple[int, int], ...]:
    """Extract sorted contour points as `(x, y)` image coordinates."""

    _validate_mask(mask)
    boundary = np.zeros_like(mask, dtype=np.bool_)
    boundary[mask] = True
    inner = mask.copy()
    inner[1:-1, 1:-1] = (
        mask[1:-1, 1:-1]
        & mask[:-2, 1:-1]
        & mask[2:, 1:-1]
        & mask[1:-1, :-2]
        & mask[1:-1, 2:]
    )
    boundary &= ~inner
    coordinates = np.argwhere(boundary)
    return tuple((int(x), int(y)) for y, x in coordinates)


def landmark_recall(
    detected: LandmarkSet,
    expected: dict[LandmarkName, tuple[float, float]],
    *,
    tolerance_px: float,
) -> float:
    """Calculate landmark recall within an image-space tolerance."""

    if tolerance_px < 0:
        raise ValueError("tolerance_px must be non-negative")
    if not expected:
        return 1.0
    hits = 0
    for name, expected_point in expected.items():
        landmark = detected.by_name(name)
        if landmark is None or landmark.status != LandmarkStatus.DETECTED:
            continue
        distance = float(np.hypot(landmark.x - expected_point[0], landmark.y - expected_point[1]))
        if distance <= tolerance_px:
            hits += 1
    return hits / float(len(expected))


def _neck_landmark(mask: np.ndarray, box: BoundingBox, *, left: bool) -> Landmark:
    name = LandmarkName.NECK_LEFT if left else LandmarkName.NECK_RIGHT
    neck_band_height = max(1, box.height // 4)
    center_start = box.left + box.width // 3
    center_end = box.left + max(box.width // 3 + 1, (box.width * 2) // 3)
    neck_band = mask[box.top : box.top + neck_band_height, center_start:center_end]
    missing = np.argwhere(~neck_band)
    if missing.size == 0:
        return Landmark(name=name, x=0.0, y=0.0, confidence=0.0, status=LandmarkStatus.OCCLUDED)
    x_values = missing[:, 1] + center_start
    y_values = missing[:, 0] + box.top
    x = float(np.min(x_values) if left else np.max(x_values))
    y = float(np.max(y_values))
    return Landmark(name=name, x=x, y=y, confidence=0.82, status=LandmarkStatus.DETECTED)


def _band_landmark(
    rows: dict[int, tuple[int, int]],
    box: BoundingBox,
    name: LandmarkName,
    vertical_ratio: float,
    *,
    left: bool,
) -> Landmark:
    target_y = box.top + int(round((box.height - 1) * vertical_ratio))
    row = _nearest_row(rows, target_y)
    if row is None:
        return Landmark(name=name, x=0.0, y=0.0, confidence=0.0, status=LandmarkStatus.MISSING)
    y, (x_min, x_max) = row
    return Landmark(
        name=name,
        x=float(x_min if left else x_max),
        y=float(y),
        confidence=0.78,
        status=LandmarkStatus.DETECTED,
    )


def _hem_landmark(
    rows: dict[int, tuple[int, int]],
    box: BoundingBox,
    name: LandmarkName,
    *,
    left: bool,
) -> Landmark:
    for y in range(box.top + box.height - 1, box.top - 1, -1):
        if y in rows:
            x_min, x_max = rows[y]
            return Landmark(
                name=name,
                x=float(x_min if left else x_max),
                y=float(y),
                confidence=0.86,
                status=LandmarkStatus.DETECTED,
            )
    return Landmark(name=name, x=0.0, y=0.0, confidence=0.0, status=LandmarkStatus.MISSING)


def _nearest_row(
    rows: dict[int, tuple[int, int]],
    target_y: int,
) -> tuple[int, tuple[int, int]] | None:
    if not rows:
        return None
    y = min(rows, key=lambda row_y: abs(row_y - target_y))
    return y, rows[y]


def _row_extents(mask: np.ndarray) -> dict[int, tuple[int, int]]:
    rows: dict[int, tuple[int, int]] = {}
    for y in range(mask.shape[0]):
        x_values = np.flatnonzero(mask[y])
        if x_values.size:
            rows[y] = (int(np.min(x_values)), int(np.max(x_values)))
    return rows


def _validate_mask(mask: np.ndarray) -> None:
    if mask.dtype != np.bool_ or mask.ndim != 2:
        raise ValueError("mask must be a boolean HxW array")
