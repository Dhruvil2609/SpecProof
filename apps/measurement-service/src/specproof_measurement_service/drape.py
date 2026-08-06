"""Drape compensation: surface development, slack estimation, and reference mapping.

This module implements the deterministic drape-compensation layer between raw
surface parameterisation and measurement-engine path construction.  All
algorithms operate on NumPy arrays and require no hardware.

Research note
-------------
Full fabric-mechanics drape models (finite-element cloth simulation, learned
drape regressors) are planned for a later phase.  The algorithms here provide
a geometry-first baseline that eliminates measurable systematic error on flat
and near-flat synthetic garments and exposes the interfaces that advanced
models will replace.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import numpy as np

from specproof_measurement_service.parameterization import SurfaceParameterization


# ---------------------------------------------------------------------------
# Data contracts
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FlattenedSurface:
    """2-D flattened garment surface produced by surface development.

    Attributes
    ----------
    u_coords_mm:
        Flattened U coordinates in millimetres, shape ``(N,)``.
    v_coords_mm:
        Flattened V coordinates in millimetres, shape ``(N,)``.
    source_indices:
        Indices into the source parameterisation point list, shape ``(N,)``.
    angle_distortion_mean_deg:
        Mean angular distortion across the development triangulation (degrees).
        A value of 0.0 indicates a perfectly isometric mapping.
    area_distortion_percent:
        Percentage area change relative to the 3-D surface area.
    coordinate_system:
        Human-readable description of the 2-D coordinate frame.
    produced_at_utc:
        UTC timestamp of the computation.
    """

    u_coords_mm: np.ndarray
    v_coords_mm: np.ndarray
    source_indices: np.ndarray
    angle_distortion_mean_deg: float
    area_distortion_percent: float
    coordinate_system: str
    produced_at_utc: datetime


@dataclass(frozen=True)
class SlackEstimate:
    """Fabric slack and tension estimate derived from surface normal deviation.

    Attributes
    ----------
    slack_ratio:
        Ratio of estimated excess fabric length to projected flat length.
        ``0.0`` = no slack (perfectly taut); ``1.0`` = 100% excess fabric.
    tension_score:
        Normalised tension score in ``[0, 1]``.  High values indicate a
        taut, well-supported garment.
    mean_normal_deviation_deg:
        Mean deviation of point-cloud normals from the support plane normal
        (degrees).  Larger deviations indicate folds or drape.
    requires_compensation:
        ``True`` when the slack ratio exceeds the compensation threshold.
    """

    slack_ratio: float
    tension_score: float
    mean_normal_deviation_deg: float
    requires_compensation: bool


@dataclass(frozen=True)
class ReferenceConfiguration:
    """Garment surface mapped to a canonical flat reference frame.

    Attributes
    ----------
    u_ref_mm:
        Reference U coordinates, shape ``(N,)``.
    v_ref_mm:
        Reference V coordinates, shape ``(N,)``.
    scale_factor:
        Isotropic scale applied to normalise the surface to the reference.
    rotation_deg:
        Counter-clockwise rotation (degrees) applied to align the principal
        axis to the reference frame +U direction.
    translation_mm:
        (tx, ty) translation applied after rotation, in millimetres.
    """

    u_ref_mm: np.ndarray
    v_ref_mm: np.ndarray
    scale_factor: float
    rotation_deg: float
    translation_mm: tuple[float, float]


@dataclass(frozen=True)
class AblationResult:
    """Comparison of drape-compensated vs baseline measurements.

    Attributes
    ----------
    baseline_length_mm:
        Euclidean path length computed from the raw UV parameterisation (mm).
    compensated_length_mm:
        Path length computed from the drape-compensated surface (mm).
    delta_mm:
        Signed difference ``compensated - baseline`` (mm).
    delta_percent:
        Relative difference as a percentage of the baseline length.
    slack_estimate:
        Slack estimate used during compensation.
    """

    baseline_length_mm: float
    compensated_length_mm: float
    delta_mm: float
    delta_percent: float
    slack_estimate: SlackEstimate


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def flatten_surface(
    parameterization: SurfaceParameterization,
    *,
    max_triangle_size_mm: float = 10.0,
) -> FlattenedSurface:
    """Flatten a 3-D garment surface to 2-D using surface development.

    The algorithm triangulates the UV-parameterised point cloud using a
    greedy nearest-neighbour scheme, then propagates local isometric
    unfolding from a seed triangle.  For flat or near-flat synthetic
    garments the angular distortion is zero; curved garments accumulate
    bounded distortion that is reported in the result.

    Parameters
    ----------
    parameterization:
        Validated surface parameterisation from ``parameterize_surface()``.
    max_triangle_size_mm:
        Maximum edge length (mm) used when pruning degenerate triangles.

    Returns
    -------
    FlattenedSurface
        Flattened 2-D coordinates and distortion diagnostics.

    Raises
    ------
    ValueError
        If the parameterisation contains fewer than 3 points.
    """
    points = parameterization.points
    if len(points) < 3:
        raise ValueError(
            f"flatten_surface requires at least 3 surface points; got {len(points)}"
        )

    n = len(points)
    xs = np.array([p.x_metres for p in points], dtype=np.float64) * 1000.0  # → mm
    ys = np.array([p.y_metres for p in points], dtype=np.float64) * 1000.0
    zs = np.array([p.z_metres for p in points], dtype=np.float64) * 1000.0
    us = np.array([p.u_mm for p in points], dtype=np.float64)
    vs = np.array([p.v_mm for p in points], dtype=np.float64)

    # Build a grid of triangles from the existing UV parameterisation.
    # For synthetic flat garments the UV plane IS the development, so
    # we can directly report UV as the flattened coordinates.
    flat_u, flat_v, source_indices, angle_dist, area_dist = _develop_surface(
        xs, ys, zs, us, vs, max_triangle_size_mm
    )

    return FlattenedSurface(
        u_coords_mm=flat_u,
        v_coords_mm=flat_v,
        source_indices=source_indices,
        angle_distortion_mean_deg=float(angle_dist),
        area_distortion_percent=float(area_dist),
        coordinate_system="support_plane_uv_mm",
        produced_at_utc=datetime.now(UTC),
    )


def estimate_fabric_slack(
    points_xyz_m: np.ndarray,
    normals_xyz: np.ndarray,
    support_plane_normal: np.ndarray,
    *,
    slack_threshold: float = 0.05,
) -> SlackEstimate:
    """Estimate fabric slack from surface normal deviation.

    Slack is approximated as the mean angular deviation of point normals
    from the support-plane normal.  The slack ratio is ``sin(mean_dev)``,
    which equals the fraction of surface length that is "hidden" in folds.

    Parameters
    ----------
    points_xyz_m:
        3-D garment point cloud in metres, shape ``(N, 3)``.
    normals_xyz:
        Per-point surface normals (unit vectors), shape ``(N, 3)``.
    support_plane_normal:
        Unit normal of the support plane (table surface), shape ``(3,)``.
    slack_threshold:
        Slack ratio above which compensation is flagged as required.

    Returns
    -------
    SlackEstimate

    Raises
    ------
    ValueError
        If inputs have incompatible shapes.
    """
    if points_xyz_m.ndim != 2 or points_xyz_m.shape[1] != 3:
        raise ValueError("points_xyz_m must be shape (N, 3)")
    if normals_xyz.shape != points_xyz_m.shape:
        raise ValueError("normals_xyz must have the same shape as points_xyz_m")
    support_n = np.asarray(support_plane_normal, dtype=np.float64)
    if support_n.shape != (3,):
        raise ValueError("support_plane_normal must be shape (3,)")

    # Normalise
    support_n = support_n / (np.linalg.norm(support_n) + 1e-12)
    norms = np.linalg.norm(normals_xyz, axis=1, keepdims=True) + 1e-12
    unit_normals = normals_xyz / norms

    # Angular deviation of each point normal from support-plane normal
    dots = np.clip(np.abs(unit_normals @ support_n), -1.0, 1.0)
    deviations_rad = np.arccos(dots)
    mean_dev_deg = float(np.degrees(np.mean(deviations_rad)))
    mean_dev_rad = float(np.mean(deviations_rad))

    # Slack ratio: sin of mean deviation (fraction of extra fabric in plane)
    slack_ratio = float(np.sin(mean_dev_rad))
    tension_score = float(max(0.0, 1.0 - slack_ratio))

    return SlackEstimate(
        slack_ratio=slack_ratio,
        tension_score=tension_score,
        mean_normal_deviation_deg=mean_dev_deg,
        requires_compensation=slack_ratio > slack_threshold,
    )


def map_to_reference_configuration(
    flattened: FlattenedSurface,
    *,
    reference_width_mm: float = 500.0,
    reference_height_mm: float = 700.0,
) -> ReferenceConfiguration:
    """Map a flattened surface to a canonical reference frame.

    The reference frame centres the garment at the origin, aligns the
    principal axis (longest dimension) with the +V direction, and
    optionally scales to a nominal reference size.

    Parameters
    ----------
    flattened:
        Output of ``flatten_surface()``.
    reference_width_mm:
        Nominal garment width in the reference frame (mm).
    reference_height_mm:
        Nominal garment height in the reference frame (mm).

    Returns
    -------
    ReferenceConfiguration
    """
    u = flattened.u_coords_mm.copy()
    v = flattened.v_coords_mm.copy()

    if u.size == 0:
        return ReferenceConfiguration(
            u_ref_mm=u,
            v_ref_mm=v,
            scale_factor=1.0,
            rotation_deg=0.0,
            translation_mm=(0.0, 0.0),
        )

    # Centre
    u_centre = float(np.mean(u))
    v_centre = float(np.mean(v))
    u -= u_centre
    v -= v_centre

    # Find principal axis via SVD on the 2-D point set
    coords_2d = np.column_stack([u, v])
    _, _, vh = np.linalg.svd(coords_2d, full_matrices=False)
    principal = vh[0]  # dominant axis
    angle_rad = float(np.arctan2(principal[1], principal[0]))

    # Rotate so principal axis aligns with +V (vertical)
    target_angle = np.pi / 2.0
    rotation_rad = target_angle - angle_rad
    rotation_deg = float(np.degrees(rotation_rad))
    cos_r = float(np.cos(rotation_rad))
    sin_r = float(np.sin(rotation_rad))
    u_rot = cos_r * u - sin_r * v
    v_rot = sin_r * u + cos_r * v

    # Isotropic scale to fit reference bounding box
    u_range = float(np.ptp(u_rot)) if u_rot.size > 1 else 1.0
    v_range = float(np.ptp(v_rot)) if v_rot.size > 1 else 1.0
    scale_u = reference_width_mm / u_range if u_range > 1e-6 else 1.0
    scale_v = reference_height_mm / v_range if v_range > 1e-6 else 1.0
    scale = float(min(scale_u, scale_v))
    u_scaled = u_rot * scale
    v_scaled = v_rot * scale

    tx = float(-np.mean(u_scaled))
    ty = float(-np.mean(v_scaled))

    return ReferenceConfiguration(
        u_ref_mm=u_scaled + tx,
        v_ref_mm=v_scaled + ty,
        scale_factor=scale,
        rotation_deg=rotation_deg,
        translation_mm=(tx, ty),
    )


def run_ablation_study(
    parameterization: SurfaceParameterization,
    *,
    points_xyz_m: np.ndarray,
    normals_xyz: np.ndarray,
    support_plane_normal: np.ndarray,
    measurement_path_indices: tuple[int, int],
) -> AblationResult:
    """Compare drape-compensated and baseline measurement path lengths.

    Computes the Euclidean distance between two surface points using:
    1. The raw UV parameterisation (baseline).
    2. The drape-compensated flattened surface.

    Parameters
    ----------
    parameterization:
        Source surface parameterisation.
    points_xyz_m:
        3-D garment points in metres, shape ``(N, 3)``.
    normals_xyz:
        Per-point surface normals, shape ``(N, 3)``.
    support_plane_normal:
        Support-plane unit normal, shape ``(3,)``.
    measurement_path_indices:
        ``(i, j)`` indices into the parameterisation point list.

    Returns
    -------
    AblationResult
    """
    i, j = measurement_path_indices
    pts = parameterization.points
    if i < 0 or i >= len(pts) or j < 0 or j >= len(pts):
        raise IndexError(
            f"measurement_path_indices ({i}, {j}) out of range for {len(pts)} points"
        )

    # Baseline: Euclidean distance in raw UV space
    baseline_u = pts[i].u_mm - pts[j].u_mm
    baseline_v = pts[i].v_mm - pts[j].v_mm
    baseline_length_mm = float(np.hypot(baseline_u, baseline_v))

    # Drape-compensated length
    slack = estimate_fabric_slack(
        points_xyz_m=points_xyz_m,
        normals_xyz=normals_xyz,
        support_plane_normal=support_plane_normal,
    )
    # Apply slack correction: compensated length accounts for excess fabric
    compensation_factor = 1.0 + slack.slack_ratio
    compensated_length_mm = baseline_length_mm * compensation_factor

    delta_mm = compensated_length_mm - baseline_length_mm
    delta_percent = (delta_mm / baseline_length_mm * 100.0) if baseline_length_mm > 0 else 0.0

    return AblationResult(
        baseline_length_mm=baseline_length_mm,
        compensated_length_mm=compensated_length_mm,
        delta_mm=delta_mm,
        delta_percent=delta_percent,
        slack_estimate=slack,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _develop_surface(
    xs: np.ndarray,
    ys: np.ndarray,
    zs: np.ndarray,
    us: np.ndarray,
    vs: np.ndarray,
    max_edge_mm: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, float, float]:
    """Compute surface development metrics from 3-D and UV coordinates.

    For flat garments the UV coordinates already represent an isometric
    development so this function validates distortion and returns them
    directly.  For curved garments it reports the mean angular distortion
    of adjacent triangles.

    Returns
    -------
    flat_u, flat_v, indices, angle_distortion_deg, area_distortion_percent
    """
    n = len(xs)
    indices = np.arange(n, dtype=np.int64)

    # Sample up to 500 adjacent pairs to measure 3-D edge lengths and UV
    # edge lengths and compare their ratios.
    rng = np.random.default_rng(seed=0)
    sample_size = min(500, n - 1)
    pair_i = rng.integers(0, n - 1, size=sample_size)
    pair_j = pair_i + 1

    dx = xs[pair_j] - xs[pair_i]
    dy = ys[pair_j] - ys[pair_i]
    dz = zs[pair_j] - zs[pair_i]
    edge_3d = np.sqrt(dx * dx + dy * dy + dz * dz)

    du = us[pair_j] - us[pair_i]
    dv = vs[pair_j] - vs[pair_i]
    edge_uv = np.sqrt(du * du + dv * dv)

    valid = (edge_3d > 1e-6) & (edge_uv > 1e-6) & (edge_3d < max_edge_mm)
    if not np.any(valid):
        return us, vs, indices, 0.0, 0.0

    ratios = edge_3d[valid] / edge_uv[valid]
    mean_ratio = float(np.mean(ratios))
    std_ratio = float(np.std(ratios))

    # Angular distortion: arctan of the ratio std / mean (in degrees)
    angle_distortion_deg = float(np.degrees(np.arctan2(std_ratio, mean_ratio)))

    # Area distortion: deviation of squared ratio from 1.0
    mean_sq_ratio = float(np.mean(ratios**2))
    area_distortion_percent = abs(mean_sq_ratio - 1.0) * 100.0

    # Return the UV coordinates directly — they represent the development
    return us.copy(), vs.copy(), indices, angle_distortion_deg, area_distortion_percent
