"""Inspection decision engine for executed measurements."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel

from specproof_measurement_service.executor import ExecutedMeasurement, MeasurementExecutionStatus
from specproof_measurement_service.techpack import ToleranceDirection


class PomDecisionStatus(StrEnum):
    """Final POM decision status."""

    PASS = "PASS"
    FAIL = "FAIL"
    REVIEW = "REVIEW"
    INVALID = "INVALID"


class InspectionDecisionStatus(StrEnum):
    """Aggregate inspection decision status."""

    PASS = "PASS"
    FAIL = "FAIL"
    REVIEW = "REVIEW"
    INVALID = "INVALID"


class PomDecision(BaseModel):
    """Decision for one POM."""

    pom_id: str
    canonical_name: str
    measured_value_mm: float
    target_mm: float
    lower_tolerance_mm: float
    upper_tolerance_mm: float
    deviation_mm: float
    confidence: float
    status: PomDecisionStatus
    reason: str


class InspectionDecision(BaseModel):
    """Aggregate inspection decision."""

    status: InspectionDecisionStatus
    measurements: tuple[PomDecision, ...]
    false_pass_threshold: float


def decide_inspection(
    measurements: tuple[ExecutedMeasurement, ...],
    *,
    false_pass_threshold: float = 0.02,
) -> InspectionDecision:
    """Produce a conservative aggregate inspection decision."""

    decisions = tuple(_decide_pom(measurement) for measurement in measurements)
    if not decisions or any(decision.status == PomDecisionStatus.INVALID for decision in decisions):
        status = InspectionDecisionStatus.INVALID
    elif any(decision.status == PomDecisionStatus.REVIEW for decision in decisions):
        status = InspectionDecisionStatus.REVIEW
    elif any(decision.status == PomDecisionStatus.FAIL for decision in decisions):
        status = InspectionDecisionStatus.FAIL
    else:
        status = InspectionDecisionStatus.PASS
    if (
        status == InspectionDecisionStatus.PASS
        and _false_pass_risk(measurements) > false_pass_threshold
    ):
        status = InspectionDecisionStatus.REVIEW
    return InspectionDecision(
        status=status,
        measurements=decisions,
        false_pass_threshold=false_pass_threshold,
    )


def _decide_pom(measurement: ExecutedMeasurement) -> PomDecision:
    if measurement.status == MeasurementExecutionStatus.INVALID:
        status = PomDecisionStatus.INVALID
        reason = measurement.reason
    elif measurement.status == MeasurementExecutionStatus.REVIEW:
        status = PomDecisionStatus.REVIEW
        reason = measurement.reason
    elif _within_tolerance(measurement):
        status = PomDecisionStatus.PASS
        reason = "within_tolerance"
    else:
        status = PomDecisionStatus.FAIL
        reason = "outside_tolerance"
    return PomDecision(
        pom_id=measurement.pom_id,
        canonical_name=measurement.canonical_name,
        measured_value_mm=measurement.measured_value_mm,
        target_mm=measurement.target_mm,
        lower_tolerance_mm=measurement.lower_tolerance_mm,
        upper_tolerance_mm=measurement.upper_tolerance_mm,
        deviation_mm=measurement.deviation_mm,
        confidence=measurement.confidence,
        status=status,
        reason=reason,
    )


def _within_tolerance(measurement: ExecutedMeasurement) -> bool:
    direction = measurement.rule.tolerance_direction
    deviation = measurement.deviation_mm
    if direction == ToleranceDirection.UNILATERAL_ABOVE:
        return deviation >= -measurement.lower_tolerance_mm
    if direction == ToleranceDirection.UNILATERAL_BELOW:
        return deviation <= measurement.upper_tolerance_mm
    return -measurement.lower_tolerance_mm <= deviation <= measurement.upper_tolerance_mm


def _false_pass_risk(measurements: tuple[ExecutedMeasurement, ...]) -> float:
    if not measurements:
        return 1.0
    return max(1.0 - measurement.confidence for measurement in measurements)
