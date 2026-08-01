from __future__ import annotations

import numpy as np
import pytest
from specproof_measurement_service import (
    GarmentCategory,
    GarmentOrientation,
    classify_garment,
    compute_bounding_box,
    detect_orientation,
    extract_boundary,
    largest_connected_component,
    segment_garment,
    segmentation_iou,
)


def _synthetic_tshirt_mask(*, front: bool = True) -> np.ndarray:
    mask = np.zeros((32, 40), dtype=np.bool_)
    mask[8:28, 13:27] = True
    mask[10:17, 6:13] = True
    mask[10:17, 27:34] = True
    if front:
        mask[8:12, 18:22] = False
    return mask


@pytest.mark.unit
def test_largest_connected_component_keeps_garment_and_removes_noise() -> None:
    mask = _synthetic_tshirt_mask()
    mask[1, 1] = True
    mask[30, 38] = True

    component = largest_connected_component(mask)

    assert component[1, 1] is np.False_
    assert component[12, 20] is np.True_


@pytest.mark.unit
def test_extract_boundary_returns_only_mask_edge_pixels() -> None:
    mask = np.zeros((8, 8), dtype=np.bool_)
    mask[2:6, 2:6] = True

    boundary = extract_boundary(mask)

    assert int(np.count_nonzero(boundary)) == 12
    assert boundary[3, 3] is np.False_


@pytest.mark.unit
def test_segment_garment_fuses_rgb_and_depth_masks() -> None:
    expected = _synthetic_tshirt_mask()
    foreground = expected.copy()
    foreground[0, 0] = True
    depth = expected.copy()

    result = segment_garment(foreground_mask=foreground, depth_garment_mask=depth)

    assert result.category == GarmentCategory.T_SHIRT
    assert result.orientation == GarmentOrientation.FRONT
    assert segmentation_iou(result.mask, expected) == pytest.approx(1.0)


@pytest.mark.unit
def test_segment_garment_rejects_small_component_as_unknown() -> None:
    foreground = np.zeros((16, 16), dtype=np.bool_)
    foreground[3:5, 3:5] = True

    result = segment_garment(
        foreground_mask=foreground,
        depth_garment_mask=foreground,
        minimum_area_pixels=16,
    )

    assert result.category == GarmentCategory.UNKNOWN
    assert result.bounding_box is None


@pytest.mark.unit
def test_compute_bounding_box_returns_expected_extents() -> None:
    mask = _synthetic_tshirt_mask()

    box = compute_bounding_box(mask)

    assert box is not None
    assert (box.left, box.top, box.width, box.height) == (6, 8, 28, 20)


@pytest.mark.unit
def test_classify_garment_tshirt_silhouette_returns_tshirt() -> None:
    mask = _synthetic_tshirt_mask()

    category, confidence = classify_garment(mask)

    assert category == GarmentCategory.T_SHIRT
    assert confidence >= 0.5


@pytest.mark.unit
def test_detect_orientation_front_uses_neckline_indentation() -> None:
    mask = _synthetic_tshirt_mask(front=True)

    orientation, confidence = detect_orientation(mask)

    assert orientation == GarmentOrientation.FRONT
    assert confidence >= 0.70


@pytest.mark.unit
def test_detect_orientation_back_uses_filled_neckline() -> None:
    mask = _synthetic_tshirt_mask(front=False)

    orientation, confidence = detect_orientation(mask)

    assert orientation == GarmentOrientation.BACK
    assert confidence == pytest.approx(0.70)


@pytest.mark.unit
def test_segmentation_iou_empty_masks_returns_perfect_score() -> None:
    empty = np.zeros((4, 4), dtype=np.bool_)

    score = segmentation_iou(empty, empty)

    assert score == pytest.approx(1.0)
