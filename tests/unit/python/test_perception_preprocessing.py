from __future__ import annotations

import numpy as np
import pytest
from specproof_capture_service.models import CameraIntrinsics
from specproof_measurement_service import (
    PlaneModel,
    build_background_model,
    detect_support_plane,
    estimate_normals,
    filter_depth,
    organized_point_cloud,
    preprocess_rgbd,
    refine_rgb_depth_registration,
    separate_garment_from_plane,
    smooth_color,
    subtract_background,
)


@pytest.fixture
def background_color() -> np.ndarray:
    return np.full((8, 10, 3), 40, dtype=np.uint8)


@pytest.fixture
def background_depth() -> np.ndarray:
    return np.full((8, 10), 1000, dtype=np.uint16)


@pytest.mark.unit
def test_background_subtraction_known_foreground_returns_expected_mask(
    background_color: np.ndarray,
    background_depth: np.ndarray,
) -> None:
    color = background_color.copy()
    depth = background_depth.copy()
    color[2:6, 3:7] = 120
    depth[2:6, 3:7] = 900
    background = build_background_model(background_color, background_depth)

    mask = subtract_background(color, depth, background)

    assert int(np.count_nonzero(mask)) == 16


@pytest.mark.unit
def test_filter_depth_removes_invalid_and_flying_pixels() -> None:
    depth = np.full((5, 5), 1000, dtype=np.uint16)
    depth[2, 2] = 65_535

    filtered = filter_depth(depth, maximum_units=5000)

    assert int(filtered[2, 2]) == 1000


@pytest.mark.unit
def test_registration_refinement_shifts_mask_by_integer_pixels() -> None:
    mask = np.zeros((5, 5), dtype=np.bool_)
    mask[2, 2] = True

    shifted = refine_rgb_depth_registration(mask, shift_x=1, shift_y=-1)

    assert shifted[1, 3] is np.True_


@pytest.mark.unit
def test_smooth_color_preserves_shape_and_dtype(background_color: np.ndarray) -> None:
    smoothed = smooth_color(background_color)

    assert smoothed.shape == background_color.shape and smoothed.dtype == np.uint8


@pytest.mark.unit
def test_preprocess_rgbd_returns_filtered_depth_and_foreground(
    background_color: np.ndarray,
    background_depth: np.ndarray,
) -> None:
    color = background_color.copy()
    depth = background_depth.copy()
    color[1:4, 1:4] = 160
    depth[1:4, 1:4] = 900
    background = build_background_model(background_color, background_depth)

    result = preprocess_rgbd(color, depth, background)

    assert result.foreground_mask.dtype == np.bool_
    assert np.count_nonzero(result.foreground_mask) == 9


@pytest.mark.unit
def test_organized_point_cloud_projects_known_center_pixel() -> None:
    depth = np.full((4, 4), 1000, dtype=np.uint16)
    intrinsics = CameraIntrinsics(
        width=4,
        height=4,
        fx=4.0,
        fy=4.0,
        ppx=2.0,
        ppy=2.0,
        distortion_model="none",
    )

    points = organized_point_cloud(depth, depth_scale_metres=0.001, intrinsics=intrinsics)

    assert points[2, 2, 2] == pytest.approx(1.0)
    assert points[2, 2, 0] == pytest.approx(0.0)


@pytest.mark.unit
def test_plane_detection_on_synthetic_plane_has_low_error() -> None:
    depth = np.full((6, 6), 1000, dtype=np.uint16)
    intrinsics = CameraIntrinsics(
        width=6,
        height=6,
        fx=6.0,
        fy=6.0,
        ppx=3.0,
        ppy=3.0,
        distortion_model="none",
    )
    points = organized_point_cloud(depth, depth_scale_metres=0.001, intrinsics=intrinsics)
    mask = np.ones((6, 6), dtype=np.bool_)

    plane = detect_support_plane(points, mask)

    assert plane.normal[2] == pytest.approx(1.0, abs=1e-6)
    assert plane.rms_mm == pytest.approx(0.0, abs=1e-6)


@pytest.mark.unit
def test_garment_plane_separation_selects_raised_region() -> None:
    points = np.zeros((5, 5, 3), dtype=np.float32)
    points[:, :, 2] = 1.0
    points[2:4, 2:4, 2] = 1.01
    plane = PlaneModel(normal=(0.0, 0.0, 1.0), offset=-1.0, rms_mm=0.0)

    garment = separate_garment_from_plane(points, plane, minimum_height_mm=4.0)

    assert int(np.count_nonzero(garment)) == 4


@pytest.mark.unit
def test_normal_estimation_returns_organized_normals() -> None:
    points = np.zeros((5, 5, 3), dtype=np.float32)
    points[:, :, 2] = 1.0

    normals = estimate_normals(points)

    assert normals.shape == points.shape
