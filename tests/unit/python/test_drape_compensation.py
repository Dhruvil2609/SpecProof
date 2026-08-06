"""Tests for drape compensation: surface development, slack estimation, reference mapping, ablation.

Tests use synthetic flat and near-flat garment fixtures to verify:
- T-3.009: Surface development preserves local distances (0% distortion on flat grid)
- Slack estimation from normal deviation
- Reference configuration idempotency
- Ablation study delta calculation
"""

from __future__ import annotations

import math
from datetime import timezone

import numpy as np
import pytest

from specproof_measurement_service.drape import (
    AblationResult,
    FlattenedSurface,
    ReferenceConfiguration,
    SlackEstimate,
    estimate_fabric_slack,
    flatten_surface,
    map_to_reference_configuration,
    run_ablation_study,
)
from specproof_measurement_service.parameterization import (
    SurfaceMapPoint,
    SurfaceParameterization,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _flat_grid_parameterization(rows: int = 10, cols: int = 10) -> SurfaceParameterization:
    """Build a perfectly flat (Z=0) synthetic garment grid parameterisation."""
    points: list[SurfaceMapPoint] = []
    for r in range(rows):
        for c in range(cols):
            u_mm = float(c * 10.0)
            v_mm = float(r * 10.0)
            points.append(
                SurfaceMapPoint(
                    pixel_x=c,
                    pixel_y=r,
                    x_metres=float(c) * 0.01,
                    y_metres=float(r) * 0.01,
                    z_metres=0.0,
                    u_mm=u_mm,
                    v_mm=v_mm,
                )
            )
    n = len(points)
    all_u = [p.u_mm for p in points]
    all_v = [p.v_mm for p in points]
    return SurfaceParameterization(
        points=tuple(points),
        u_min_mm=float(min(all_u)),
        u_max_mm=float(max(all_u)),
        v_min_mm=float(min(all_v)),
        v_max_mm=float(max(all_v)),
        mapped_pixel_count=n,
        area_distortion_percent=0.0,
        coordinate_system="support_plane_uv_mm",
    )


def _flat_points_and_normals(
    rows: int = 10, cols: int = 10
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (points_xyz_m, normals, support_plane_normal) for a flat Z=0 garment."""
    points = np.zeros((rows * cols, 3), dtype=np.float64)
    normals = np.zeros_like(points)
    for r in range(rows):
        for c in range(cols):
            idx = r * cols + c
            points[idx] = [float(c) * 0.01, float(r) * 0.01, 0.0]
            normals[idx] = [0.0, 0.0, 1.0]  # all pointing up
    support_plane_normal = np.array([0.0, 0.0, 1.0], dtype=np.float64)
    return points, normals, support_plane_normal


# ---------------------------------------------------------------------------
# flatten_surface
# ---------------------------------------------------------------------------


class TestFlattenSurface:
    @pytest.mark.unit
    def test_flat_grid_zero_area_distortion(self) -> None:
        """T-3.009 — surface development on flat synthetic grid: area distortion ≈ 0%."""
        param = _flat_grid_parameterization()
        result = flatten_surface(param)
        # Flat grid: area distortion must be close to zero
        assert result.area_distortion_percent == pytest.approx(0.0, abs=5.0)

    @pytest.mark.unit
    def test_flat_grid_angle_distortion_near_zero(self) -> None:
        """Surface development on a flat grid: angle distortion is minimal."""
        param = _flat_grid_parameterization()
        result = flatten_surface(param)
        assert result.angle_distortion_mean_deg == pytest.approx(0.0, abs=15.0)

    @pytest.mark.unit
    def test_returns_correct_point_count(self) -> None:
        """Flattened surface has same number of points as parameterisation."""
        param = _flat_grid_parameterization(5, 5)
        result = flatten_surface(param)
        assert len(result.u_coords_mm) == len(param.points)
        assert len(result.v_coords_mm) == len(param.points)

    @pytest.mark.unit
    def test_returns_flattened_surface_instance(self) -> None:
        """flatten_surface returns a FlattenedSurface dataclass."""
        param = _flat_grid_parameterization()
        result = flatten_surface(param)
        assert isinstance(result, FlattenedSurface)

    @pytest.mark.unit
    def test_coordinate_system_label(self) -> None:
        """Coordinate system label is set to 'support_plane_uv_mm'."""
        param = _flat_grid_parameterization()
        result = flatten_surface(param)
        assert result.coordinate_system == "support_plane_uv_mm"

    @pytest.mark.unit
    def test_produced_at_utc_is_timezone_aware(self) -> None:
        """produced_at_utc is a timezone-aware UTC datetime."""
        param = _flat_grid_parameterization()
        result = flatten_surface(param)
        assert result.produced_at_utc.tzinfo is not None
        assert result.produced_at_utc.tzinfo == timezone.utc

    @pytest.mark.unit
    def test_raises_on_fewer_than_3_points(self) -> None:
        """flatten_surface raises ValueError when fewer than 3 points are given."""
        tiny = SurfaceParameterization(
            points=(
                SurfaceMapPoint(0, 0, 0.0, 0.0, 0.0, 0.0, 0.0),
                SurfaceMapPoint(1, 0, 0.01, 0.0, 0.0, 10.0, 0.0),
            ),
            u_min_mm=0.0,
            u_max_mm=10.0,
            v_min_mm=0.0,
            v_max_mm=0.0,
            mapped_pixel_count=2,
            area_distortion_percent=0.0,
        )
        with pytest.raises(ValueError, match="at least 3 surface points"):
            flatten_surface(tiny)

    @pytest.mark.unit
    def test_source_indices_cover_all_points(self) -> None:
        """Source indices span the full point range."""
        param = _flat_grid_parameterization(4, 4)
        result = flatten_surface(param)
        assert int(np.max(result.source_indices)) < len(param.points)


# ---------------------------------------------------------------------------
# estimate_fabric_slack
# ---------------------------------------------------------------------------


class TestEstimateFabricSlack:
    @pytest.mark.unit
    def test_flat_garment_zero_slack(self) -> None:
        """Perfectly flat garment (all normals = support normal) → slack_ratio ≈ 0."""
        points, normals, support_n = _flat_points_and_normals()
        result = estimate_fabric_slack(
            points_xyz_m=points,
            normals_xyz=normals,
            support_plane_normal=support_n,
        )
        assert result.slack_ratio == pytest.approx(0.0, abs=0.01)

    @pytest.mark.unit
    def test_flat_garment_tension_score_near_one(self) -> None:
        """Flat garment → tension_score ≈ 1.0."""
        points, normals, support_n = _flat_points_and_normals()
        result = estimate_fabric_slack(
            points_xyz_m=points, normals_xyz=normals, support_plane_normal=support_n
        )
        assert result.tension_score == pytest.approx(1.0, abs=0.01)

    @pytest.mark.unit
    def test_flat_garment_no_compensation_required(self) -> None:
        """Flat garment does not require drape compensation."""
        points, normals, support_n = _flat_points_and_normals()
        result = estimate_fabric_slack(
            points_xyz_m=points, normals_xyz=normals, support_plane_normal=support_n
        )
        assert result.requires_compensation is False

    @pytest.mark.unit
    def test_folded_garment_positive_slack(self) -> None:
        """Garment normals at 45° to support → slack_ratio ≈ sin(45°) ≈ 0.707."""
        points, normals, support_n = _flat_points_and_normals()
        # Tilt all normals 45° from vertical
        tilted_normals = np.column_stack(
            [
                np.full(len(normals), math.sin(math.radians(45))),
                np.zeros(len(normals)),
                np.full(len(normals), math.cos(math.radians(45))),
            ]
        )
        result = estimate_fabric_slack(
            points_xyz_m=points, normals_xyz=tilted_normals, support_plane_normal=support_n
        )
        assert result.slack_ratio == pytest.approx(math.sin(math.radians(45)), abs=0.05)

    @pytest.mark.unit
    def test_returns_slack_estimate_instance(self) -> None:
        """estimate_fabric_slack returns a SlackEstimate."""
        points, normals, support_n = _flat_points_and_normals()
        result = estimate_fabric_slack(
            points_xyz_m=points, normals_xyz=normals, support_plane_normal=support_n
        )
        assert isinstance(result, SlackEstimate)

    @pytest.mark.unit
    def test_raises_on_wrong_points_shape(self) -> None:
        """Raises ValueError for non-(N,3) points array."""
        bad_points = np.zeros((10, 2))
        normals = np.zeros((10, 3))
        support_n = np.array([0.0, 0.0, 1.0])
        with pytest.raises(ValueError, match="must be shape"):
            estimate_fabric_slack(
                points_xyz_m=bad_points,
                normals_xyz=normals,
                support_plane_normal=support_n,
            )

    @pytest.mark.unit
    def test_raises_on_mismatched_normals_shape(self) -> None:
        """Raises ValueError when normals shape differs from points shape."""
        points = np.zeros((10, 3))
        bad_normals = np.zeros((5, 3))
        support_n = np.array([0.0, 0.0, 1.0])
        with pytest.raises(ValueError, match="same shape"):
            estimate_fabric_slack(
                points_xyz_m=points,
                normals_xyz=bad_normals,
                support_plane_normal=support_n,
            )


# ---------------------------------------------------------------------------
# map_to_reference_configuration
# ---------------------------------------------------------------------------


class TestMapToReferenceConfiguration:
    @pytest.mark.unit
    def test_returns_reference_configuration_instance(self) -> None:
        """map_to_reference_configuration returns a ReferenceConfiguration."""
        param = _flat_grid_parameterization()
        flattened = flatten_surface(param)
        result = map_to_reference_configuration(flattened)
        assert isinstance(result, ReferenceConfiguration)

    @pytest.mark.unit
    def test_output_centred_at_origin(self) -> None:
        """Reference coordinates are approximately zero-mean."""
        param = _flat_grid_parameterization()
        flattened = flatten_surface(param)
        result = map_to_reference_configuration(flattened)
        assert float(np.mean(result.u_ref_mm)) == pytest.approx(0.0, abs=1.0)
        assert float(np.mean(result.v_ref_mm)) == pytest.approx(0.0, abs=1.0)

    @pytest.mark.unit
    def test_scale_factor_positive(self) -> None:
        """Scale factor must be a positive number."""
        param = _flat_grid_parameterization()
        flattened = flatten_surface(param)
        result = map_to_reference_configuration(flattened)
        assert result.scale_factor > 0.0

    @pytest.mark.unit
    def test_idempotent_on_already_centred_surface(self) -> None:
        """Mapping an already-centred surface to the same reference is stable."""
        param = _flat_grid_parameterization()
        flattened = flatten_surface(param)
        ref1 = map_to_reference_configuration(flattened, reference_width_mm=400.0)
        # Construct a synthetic FlattenedSurface from the reference output
        from specproof_measurement_service.drape import FlattenedSurface
        from datetime import datetime, timezone

        re_flattened = FlattenedSurface(
            u_coords_mm=ref1.u_ref_mm,
            v_coords_mm=ref1.v_ref_mm,
            source_indices=flattened.source_indices,
            angle_distortion_mean_deg=0.0,
            area_distortion_percent=0.0,
            coordinate_system="support_plane_uv_mm",
            produced_at_utc=datetime.now(timezone.utc),
        )
        ref2 = map_to_reference_configuration(re_flattened, reference_width_mm=400.0)
        # Both should be centred at origin
        assert float(np.mean(ref2.u_ref_mm)) == pytest.approx(0.0, abs=2.0)
        assert float(np.mean(ref2.v_ref_mm)) == pytest.approx(0.0, abs=2.0)

    @pytest.mark.unit
    def test_empty_surface_handled_gracefully(self) -> None:
        """Empty flattened surface returns zero-size reference without error."""
        from datetime import datetime, timezone

        empty = FlattenedSurface(
            u_coords_mm=np.array([], dtype=np.float64),
            v_coords_mm=np.array([], dtype=np.float64),
            source_indices=np.array([], dtype=np.int64),
            angle_distortion_mean_deg=0.0,
            area_distortion_percent=0.0,
            coordinate_system="support_plane_uv_mm",
            produced_at_utc=datetime.now(timezone.utc),
        )
        result = map_to_reference_configuration(empty)
        assert result.u_ref_mm.size == 0
        assert result.v_ref_mm.size == 0


# ---------------------------------------------------------------------------
# run_ablation_study
# ---------------------------------------------------------------------------


class TestRunAblationStudy:
    @pytest.mark.unit
    def test_flat_garment_delta_near_zero(self) -> None:
        """Flat garment (zero slack) → compensation delta ≈ 0 mm."""
        param = _flat_grid_parameterization(5, 5)
        points, normals, support_n = _flat_points_and_normals(5, 5)
        result = run_ablation_study(
            parameterization=param,
            points_xyz_m=points,
            normals_xyz=normals,
            support_plane_normal=support_n,
            measurement_path_indices=(0, 24),
        )
        assert isinstance(result, AblationResult)
        assert result.delta_mm == pytest.approx(0.0, abs=2.0)

    @pytest.mark.unit
    def test_baseline_length_positive(self) -> None:
        """Baseline measurement path length is positive."""
        param = _flat_grid_parameterization(5, 5)
        points, normals, support_n = _flat_points_and_normals(5, 5)
        result = run_ablation_study(
            parameterization=param,
            points_xyz_m=points,
            normals_xyz=normals,
            support_plane_normal=support_n,
            measurement_path_indices=(0, 4),
        )
        assert result.baseline_length_mm > 0.0

    @pytest.mark.unit
    def test_compensated_ge_baseline_for_positive_slack(self) -> None:
        """With positive slack, compensated length ≥ baseline length."""
        param = _flat_grid_parameterization(5, 5)
        points, normals, _ = _flat_points_and_normals(5, 5)
        # 30° tilted normals → positive slack
        tilted = np.column_stack(
            [
                np.full(len(normals), math.sin(math.radians(30))),
                np.zeros(len(normals)),
                np.full(len(normals), math.cos(math.radians(30))),
            ]
        )
        support_n = np.array([0.0, 0.0, 1.0])
        result = run_ablation_study(
            parameterization=param,
            points_xyz_m=points,
            normals_xyz=tilted,
            support_plane_normal=support_n,
            measurement_path_indices=(0, 4),
        )
        assert result.compensated_length_mm >= result.baseline_length_mm

    @pytest.mark.unit
    def test_delta_equals_compensated_minus_baseline(self) -> None:
        """delta_mm == compensated_length_mm - baseline_length_mm."""
        param = _flat_grid_parameterization(5, 5)
        points, normals, support_n = _flat_points_and_normals(5, 5)
        result = run_ablation_study(
            parameterization=param,
            points_xyz_m=points,
            normals_xyz=normals,
            support_plane_normal=support_n,
            measurement_path_indices=(0, 10),
        )
        expected_delta = result.compensated_length_mm - result.baseline_length_mm
        assert result.delta_mm == pytest.approx(expected_delta, abs=1e-9)

    @pytest.mark.unit
    def test_raises_on_out_of_range_indices(self) -> None:
        """IndexError raised when measurement path indices are out of range."""
        param = _flat_grid_parameterization(3, 3)
        points, normals, support_n = _flat_points_and_normals(3, 3)
        with pytest.raises(IndexError):
            run_ablation_study(
                parameterization=param,
                points_xyz_m=points,
                normals_xyz=normals,
                support_plane_normal=support_n,
                measurement_path_indices=(0, 9999),
            )
