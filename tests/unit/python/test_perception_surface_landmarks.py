from __future__ import annotations

import numpy as np
import pytest
from specproof_measurement_service import (
    T_SHIRT_LANDMARKS,
    LandmarkName,
    LandmarkStatus,
    PlaneModel,
    detect_tshirt_landmarks,
    extract_contour_points,
    landmark_recall,
    score_surface_confidence,
)


def _synthetic_tshirt_mask(*, front: bool = True) -> np.ndarray:
    mask = np.zeros((32, 40), dtype=np.bool_)
    mask[8:28, 13:27] = True
    mask[10:17, 6:13] = True
    mask[10:17, 27:34] = True
    if front:
        mask[8:12, 18:22] = False
    return mask


def _flat_points(shape: tuple[int, int], z_metres: float = 1.0) -> np.ndarray:
    points = np.zeros((*shape, 3), dtype=np.float32)
    points[:, :, 2] = z_metres
    return points


@pytest.mark.unit
def test_score_surface_confidence_clean_surface_returns_high_confidence() -> None:
    garment_mask = _synthetic_tshirt_mask()
    zone_mask = np.ones_like(garment_mask, dtype=np.bool_)
    points = _flat_points(garment_mask.shape)
    normals = np.zeros_like(points)
    normals[:, :, 2] = 1.0
    plane = PlaneModel(normal=(0.0, 0.0, 1.0), offset=-1.0, rms_mm=0.25)

    score = score_surface_confidence(
        points=points,
        garment_mask=garment_mask,
        capture_zone_mask=zone_mask,
        support_plane=plane,
        normals=normals,
    )

    assert score.overall >= 0.75
    assert score.reason == "ok"


@pytest.mark.unit
def test_score_surface_confidence_missing_depth_requires_review() -> None:
    garment_mask = _synthetic_tshirt_mask()
    zone_mask = np.ones_like(garment_mask, dtype=np.bool_)
    points = _flat_points(garment_mask.shape)
    points[garment_mask, 2] = np.nan
    plane = PlaneModel(normal=(0.0, 0.0, 1.0), offset=-1.0, rms_mm=0.25)

    score = score_surface_confidence(
        points=points,
        garment_mask=garment_mask,
        capture_zone_mask=zone_mask,
        support_plane=plane,
    )

    assert score.overall == pytest.approx(0.0)
    assert score.reason == "low_surface_confidence"


@pytest.mark.unit
def test_score_surface_confidence_bad_plane_fit_lowers_score() -> None:
    garment_mask = _synthetic_tshirt_mask()
    zone_mask = np.ones_like(garment_mask, dtype=np.bool_)
    points = _flat_points(garment_mask.shape)
    plane = PlaneModel(normal=(0.0, 0.0, 1.0), offset=-1.0, rms_mm=3.0)

    score = score_surface_confidence(
        points=points,
        garment_mask=garment_mask,
        capture_zone_mask=zone_mask,
        support_plane=plane,
    )

    assert score.plane_fit_score == pytest.approx(0.0)
    assert score.reason == "low_surface_confidence"


@pytest.mark.unit
def test_tshirt_landmark_vocabulary_contains_expected_landmarks() -> None:
    assert T_SHIRT_LANDMARKS == (
        LandmarkName.NECK_LEFT,
        LandmarkName.NECK_RIGHT,
        LandmarkName.SHOULDER_LEFT,
        LandmarkName.SHOULDER_RIGHT,
        LandmarkName.SLEEVE_HEM_LEFT,
        LandmarkName.SLEEVE_HEM_RIGHT,
        LandmarkName.SIDE_SEAM_LEFT,
        LandmarkName.SIDE_SEAM_RIGHT,
        LandmarkName.HEM_LEFT,
        LandmarkName.HEM_RIGHT,
    )


@pytest.mark.unit
def test_detect_tshirt_landmarks_front_mask_detects_all_required_points() -> None:
    landmarks = detect_tshirt_landmarks(_synthetic_tshirt_mask(front=True))

    assert landmarks.review_required is False
    assert len(landmarks.landmarks) == len(T_SHIRT_LANDMARKS)
    assert all(landmark.status == LandmarkStatus.DETECTED for landmark in landmarks.landmarks)
    assert landmarks.by_name(LandmarkName.NECK_LEFT) is not None


@pytest.mark.unit
def test_detect_tshirt_landmarks_back_mask_marks_neckline_occluded() -> None:
    landmarks = detect_tshirt_landmarks(_synthetic_tshirt_mask(front=False))
    neck_left = landmarks.by_name(LandmarkName.NECK_LEFT)
    neck_right = landmarks.by_name(LandmarkName.NECK_RIGHT)

    assert landmarks.review_required is True
    assert neck_left is not None
    assert neck_right is not None
    assert neck_left.status == LandmarkStatus.OCCLUDED
    assert neck_right.status == LandmarkStatus.OCCLUDED


@pytest.mark.unit
def test_detect_tshirt_landmarks_empty_mask_marks_missing() -> None:
    landmarks = detect_tshirt_landmarks(np.zeros((16, 16), dtype=np.bool_))

    assert landmarks.review_required is True
    assert all(landmark.status == LandmarkStatus.MISSING for landmark in landmarks.landmarks)


@pytest.mark.unit
def test_extract_contour_points_returns_image_coordinates() -> None:
    mask = np.zeros((6, 6), dtype=np.bool_)
    mask[2:5, 1:4] = True

    contour = extract_contour_points(mask)

    assert (1, 2) in contour
    assert (2, 3) not in contour


@pytest.mark.unit
def test_landmark_recall_counts_detected_landmarks_within_tolerance() -> None:
    landmarks = detect_tshirt_landmarks(_synthetic_tshirt_mask(front=True))
    neck_left = landmarks.by_name(LandmarkName.NECK_LEFT)
    hem_right = landmarks.by_name(LandmarkName.HEM_RIGHT)
    assert neck_left is not None
    assert hem_right is not None
    expected = {
        LandmarkName.NECK_LEFT: (neck_left.x, neck_left.y),
        LandmarkName.HEM_RIGHT: (hem_right.x + 20.0, hem_right.y),
    }

    recall = landmark_recall(landmarks, expected, tolerance_px=2.0)

    assert recall == pytest.approx(0.5)
