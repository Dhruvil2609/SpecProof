"""Measurement rule execution against Phase 3 perception output."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel
from specproof_geometry import Point3D, euclidean_distance_mm, projected_distance_mm
from specproof_geometry.distance import polyline_distance_mm

from specproof_measurement_service.compiler import CompiledMeasurementRule
from specproof_measurement_service.ontology import PathType, RoundingMode
from specproof_measurement_service.pipeline import (
    PerceptionLandmark,
    PerceptionResult,
    PerceptionSurfaceMapPoint,
)


class MeasurementExecutionStatus(StrEnum):
    """Status of one executed measurement before tolerance decision."""

    MEASURED = "measured"
    REVIEW = "review"
    INVALID = "invalid"


class ExecutedMeasurement(BaseModel):
    """Raw measured POM value and execution metadata."""

    pom_id: str
    canonical_name: str
    measured_value_mm: float
    target_mm: float
    lower_tolerance_mm: float
    upper_tolerance_mm: float
    deviation_mm: float
    confidence: float
    uncertainty_mm: float
    status: MeasurementExecutionStatus
    reason: str
    rule: CompiledMeasurementRule


def execute_rules(
    rules: tuple[CompiledMeasurementRule, ...],
    perception: PerceptionResult,
) -> tuple[ExecutedMeasurement, ...]:
    """Execute compiled rules against a perception result."""

    if perception.category != "t_shirt":
        return tuple(_invalid(rule, "unsupported_garment_category") for rule in rules)
    return tuple(_execute_rule(rule, perception) for rule in rules)


def _execute_rule(
    rule: CompiledMeasurementRule,
    perception: PerceptionResult,
) -> ExecutedMeasurement:
    start = _resolve_anchor(rule.start_anchor.landmark_name, perception.landmarks)
    end = _resolve_anchor(rule.end_anchor.landmark_name, perception.landmarks)
    if start is None or end is None:
        return _invalid(rule, "anchor_missing")
    start_point = _nearest_surface_point(start, perception.surface_mapping.points)
    end_point = _nearest_surface_point(end, perception.surface_mapping.points)
    if start_point is None or end_point is None:
        return _invalid(rule, "surface_point_missing")
    measured = _distance(rule.path_type, start_point, end_point)
    measured = (measured * 2.0) if rule.modifiers.doubled else measured
    measured += rule.modifiers.offset_mm
    measured = _round_value(measured, rule.modifiers.rounding)
    confidence = max(
        0.0,
        min(1.0, start.confidence * end.confidence * perception.surface_quality.overall),
    )
    uncertainty = max(1.0, (1.0 - confidence) * 8.0)
    status = (
        MeasurementExecutionStatus.REVIEW
        if confidence < rule.confidence_threshold or perception.review_required
        else MeasurementExecutionStatus.MEASURED
    )
    return ExecutedMeasurement(
        pom_id=rule.pom_id,
        canonical_name=rule.canonical_name,
        measured_value_mm=measured,
        target_mm=rule.target_mm,
        lower_tolerance_mm=rule.lower_tolerance_mm,
        upper_tolerance_mm=rule.upper_tolerance_mm,
        deviation_mm=measured - rule.target_mm,
        confidence=confidence,
        uncertainty_mm=uncertainty,
        status=status,
        reason=(
            "ok"
            if status == MeasurementExecutionStatus.MEASURED
            else "low_confidence_or_review_required"
        ),
        rule=rule,
    )


def _distance(
    path_type: PathType,
    start: PerceptionSurfaceMapPoint,
    end: PerceptionSurfaceMapPoint,
) -> float:
    first = Point3D(start.u_mm, start.v_mm, start.z_metres * 1000.0)
    second = Point3D(end.u_mm, end.v_mm, end.z_metres * 1000.0)
    if path_type == PathType.STRAIGHT:
        return euclidean_distance_mm(first, second)
    if path_type == PathType.PROJECTED:
        return projected_distance_mm(first, second)
    return polyline_distance_mm((first, second))


def _resolve_anchor(
    name: str | None,
    landmarks: tuple[PerceptionLandmark, ...],
) -> PerceptionLandmark | None:
    if name is None:
        return None
    return next(
        (
            landmark
            for landmark in landmarks
            if landmark.name == name and landmark.status == "detected"
        ),
        None,
    )


def _nearest_surface_point(
    landmark: PerceptionLandmark,
    points: tuple[PerceptionSurfaceMapPoint, ...],
) -> PerceptionSurfaceMapPoint | None:
    if not points:
        return None
    return min(
        points,
        key=lambda point: ((point.pixel_x - landmark.x) ** 2) + ((point.pixel_y - landmark.y) ** 2),
    )


def _round_value(value: float, rounding: RoundingMode) -> float:
    if rounding == RoundingMode.NONE:
        return value
    if rounding == RoundingMode.NEAREST_HALF_MM:
        return round(value * 2.0) / 2.0
    return float(round(value))


def _invalid(rule: CompiledMeasurementRule, reason: str) -> ExecutedMeasurement:
    return ExecutedMeasurement(
        pom_id=rule.pom_id,
        canonical_name=rule.canonical_name,
        measured_value_mm=0.0,
        target_mm=rule.target_mm,
        lower_tolerance_mm=rule.lower_tolerance_mm,
        upper_tolerance_mm=rule.upper_tolerance_mm,
        deviation_mm=0.0,
        confidence=0.0,
        uncertainty_mm=0.0,
        status=MeasurementExecutionStatus.INVALID,
        reason=reason,
        rule=rule,
    )
