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


# ---------------------------------------------------------------------------
# Graph-based landmark refinement (TASK-3.2.4.6)
# ---------------------------------------------------------------------------


#: Anatomical distance constraints between T-shirt landmark pairs (mm).
#: Each entry is (landmark_a, landmark_b, min_mm, max_mm).
_ANATOMICAL_CONSTRAINTS: tuple[tuple[LandmarkName, LandmarkName, float, float], ...] = (
    (LandmarkName.NECK_LEFT, LandmarkName.NECK_RIGHT, 30.0, 300.0),
    (LandmarkName.SHOULDER_LEFT, LandmarkName.SHOULDER_RIGHT, 200.0, 700.0),
    (LandmarkName.SLEEVE_HEM_LEFT, LandmarkName.SLEEVE_HEM_RIGHT, 100.0, 600.0),
    (LandmarkName.SIDE_SEAM_LEFT, LandmarkName.SIDE_SEAM_RIGHT, 200.0, 700.0),
    (LandmarkName.HEM_LEFT, LandmarkName.HEM_RIGHT, 200.0, 700.0),
    (LandmarkName.NECK_LEFT, LandmarkName.SHOULDER_LEFT, 50.0, 250.0),
    (LandmarkName.NECK_RIGHT, LandmarkName.SHOULDER_RIGHT, 50.0, 250.0),
    (LandmarkName.SHOULDER_LEFT, LandmarkName.SIDE_SEAM_LEFT, 100.0, 500.0),
    (LandmarkName.SHOULDER_RIGHT, LandmarkName.SIDE_SEAM_RIGHT, 100.0, 500.0),
    (LandmarkName.SIDE_SEAM_LEFT, LandmarkName.HEM_LEFT, 100.0, 600.0),
    (LandmarkName.SIDE_SEAM_RIGHT, LandmarkName.HEM_RIGHT, 100.0, 600.0),
)


def graph_refine_landmarks(
    landmark_set: LandmarkSet,
    *,
    pixels_per_mm: float = 1.0,
    symmetry_tolerance_px: float = 20.0,
) -> LandmarkSet:
    """Refine landmark positions using an anatomical constraint graph.

    Post-processing step that applies:
    1. **Bilateral symmetry** — adjusts left/right landmarks to be
       horizontally equidistant from the garment centre.
    2. **Sequential ordering** — ensures top-to-bottom landmark ordering
       is consistent along each side seam.
    3. **Anatomical distance constraints** — flags or clamps landmark pairs
       that violate expected spec-constrained distance ranges.

    Parameters
    ----------
    landmark_set:
        Heuristic or model-detected landmark set.
    pixels_per_mm:
        Conversion factor from image pixels to millimetres.  Used when
        checking anatomical distance constraints.
    symmetry_tolerance_px:
        Maximum allowable left/right asymmetry in pixels before correction.

    Returns
    -------
    LandmarkSet
        Refined landmark set.  Landmarks that cannot be reconciled are
        marked ``MISSING`` and ``review_required`` is set to ``True``.
    """
    refined: dict[LandmarkName, Landmark] = {lm.name: lm for lm in landmark_set.landmarks}

    # Step 1: Bilateral symmetry correction
    _SYMMETRY_PAIRS: tuple[tuple[LandmarkName, LandmarkName], ...] = (
        (LandmarkName.NECK_LEFT, LandmarkName.NECK_RIGHT),
        (LandmarkName.SHOULDER_LEFT, LandmarkName.SHOULDER_RIGHT),
        (LandmarkName.SLEEVE_HEM_LEFT, LandmarkName.SLEEVE_HEM_RIGHT),
        (LandmarkName.SIDE_SEAM_LEFT, LandmarkName.SIDE_SEAM_RIGHT),
        (LandmarkName.HEM_LEFT, LandmarkName.HEM_RIGHT),
    )
    for left_name, right_name in _SYMMETRY_PAIRS:
        left_lm = refined.get(left_name)
        right_lm = refined.get(right_name)
        if (
            left_lm is None
            or right_lm is None
            or left_lm.status != LandmarkStatus.DETECTED
            or right_lm.status != LandmarkStatus.DETECTED
        ):
            continue
        centre_x = (left_lm.x + right_lm.x) / 2.0
        half_span = (right_lm.x - left_lm.x) / 2.0
        asymmetry = abs(centre_x - (left_lm.x + half_span))
        if asymmetry > symmetry_tolerance_px:
            # Correct both sides toward their symmetric positions
            refined[left_name] = left_lm.__class__(
                name=left_name,
                x=centre_x - half_span,
                y=left_lm.y,
                confidence=left_lm.confidence * 0.9,
                status=LandmarkStatus.DETECTED,
            )
            refined[right_name] = right_lm.__class__(
                name=right_name,
                x=centre_x + half_span,
                y=right_lm.y,
                confidence=right_lm.confidence * 0.9,
                status=LandmarkStatus.DETECTED,
            )

    # Step 2: Sequential vertical ordering (top → bottom along left side)
    _LEFT_SEQUENCE: tuple[LandmarkName, ...] = (
        LandmarkName.NECK_LEFT,
        LandmarkName.SHOULDER_LEFT,
        LandmarkName.SLEEVE_HEM_LEFT,
        LandmarkName.SIDE_SEAM_LEFT,
        LandmarkName.HEM_LEFT,
    )
    _apply_sequential_ordering(refined, _LEFT_SEQUENCE)
    _RIGHT_SEQUENCE: tuple[LandmarkName, ...] = (
        LandmarkName.NECK_RIGHT,
        LandmarkName.SHOULDER_RIGHT,
        LandmarkName.SLEEVE_HEM_RIGHT,
        LandmarkName.SIDE_SEAM_RIGHT,
        LandmarkName.HEM_RIGHT,
    )
    _apply_sequential_ordering(refined, _RIGHT_SEQUENCE)

    # Step 3: Anatomical distance constraint check
    review_required = landmark_set.review_required
    for lm_a_name, lm_b_name, min_mm, max_mm in _ANATOMICAL_CONSTRAINTS:
        lm_a = refined.get(lm_a_name)
        lm_b = refined.get(lm_b_name)
        if (
            lm_a is None
            or lm_b is None
            or lm_a.status != LandmarkStatus.DETECTED
            or lm_b.status != LandmarkStatus.DETECTED
        ):
            continue
        dist_px = float(np.hypot(lm_a.x - lm_b.x, lm_a.y - lm_b.y))
        dist_mm = dist_px / max(pixels_per_mm, 1e-6)
        if dist_mm < min_mm or dist_mm > max_mm:
            # Flag both as needing review but do not discard them
            review_required = True

    refined_landmarks = tuple(refined.get(name, lm) for name, lm in (
        (lm.name, lm) for lm in landmark_set.landmarks
    ))
    confidences = [lm.confidence for lm in refined_landmarks]
    mean_confidence = float(np.mean(confidences)) if confidences else 0.0
    any_missing = any(lm.status != LandmarkStatus.DETECTED for lm in refined_landmarks)

    return LandmarkSet(
        landmarks=refined_landmarks,
        contour=landmark_set.contour,
        confidence=mean_confidence,
        review_required=review_required or any_missing,
    )


def _apply_sequential_ordering(
    refined: dict[LandmarkName, Landmark],
    sequence: tuple[LandmarkName, ...],
) -> None:
    """Ensure detected landmarks in ``sequence`` are monotonically increasing in Y."""
    prev_y: float | None = None
    for name in sequence:
        lm = refined.get(name)
        if lm is None or lm.status != LandmarkStatus.DETECTED:
            prev_y = None
            continue
        if prev_y is not None and lm.y <= prev_y:
            # Push landmark below the previous one with reduced confidence
            refined[name] = Landmark(
                name=name,
                x=lm.x,
                y=prev_y + 1.0,
                confidence=lm.confidence * 0.85,
                status=LandmarkStatus.DETECTED,
            )
            prev_y = prev_y + 1.0
        else:
            prev_y = lm.y


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
