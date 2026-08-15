"""Versioned schemas for validation-study entities and analytical output."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field


class Garment(BaseModel):
    """One physical garment included in a study."""

    garment_id: str = Field(min_length=1)
    style_code: str = Field(min_length=1)
    size_code: str = Field(min_length=1)


class PomDefinition(BaseModel):
    """One approved point of measure and tolerance."""

    pom_id: str = Field(min_length=1)
    target_mm: float
    lower_tolerance_mm: float = Field(ge=0)
    upper_tolerance_mm: float = Field(ge=0)


class StudyOperator(BaseModel):
    """An anonymized operator participating in the study."""

    operator_id: str = Field(min_length=1)


class Placement(BaseModel):
    """A controlled garment placement repeat."""

    placement_id: str = Field(min_length=1)
    sequence: int = Field(gt=0)


class StudyObservation(BaseModel):
    """Normalized joined manual and automated reading."""

    schema_version: int = 1
    garment_id: str = Field(min_length=1)
    style_code: str = Field(min_length=1)
    size_code: str = Field(min_length=1)
    pom_id: str = Field(min_length=1)
    operator_id: str = Field(min_length=1)
    placement_id: str = Field(min_length=1)
    repeat: int = Field(gt=0)
    target_mm: float
    lower_tolerance_mm: float = Field(ge=0)
    upper_tolerance_mm: float = Field(ge=0)
    manual_mm: float = Field(gt=0)
    automated_mm: float = Field(gt=0)


class ValidationStudyDataset(BaseModel):
    """Versioned relational study schema before normalized analytical export."""

    schema_version: int = 1
    garments: tuple[Garment, ...]
    poms: tuple[PomDefinition, ...]
    operators: tuple[StudyOperator, ...]
    placements: tuple[Placement, ...]
    observations: tuple[StudyObservation, ...]


class StudyThresholds(BaseModel):
    """Phase 7 software acceptance thresholds."""

    repeatability_stddev_mm: float = 2.0
    reproducibility_p95_mm: float = 4.0
    manual_mae_mm: float = 5.0
    false_pass_rate: float = 0.02
    false_fail_rate: float = 0.05
    gauge_rr_stddev_mm: float = 4.0


class GaugeRrComponents(BaseModel):
    """Crossed Gauge R&R variance components in square millimetres."""

    part_variance: float = Field(ge=0)
    operator_variance: float = Field(ge=0)
    interaction_variance: float = Field(ge=0)
    repeatability_variance: float = Field(ge=0)
    reproducibility_variance: float = Field(ge=0)
    gauge_rr_variance: float = Field(ge=0)
    gauge_rr_stddev_mm: float = Field(ge=0)


class PomStudyMetrics(BaseModel):
    """Unaggregated acceptance results for one POM."""

    pom_id: str
    observation_count: int
    garment_count: int
    operator_count: int
    placement_count: int
    same_placement_stddev_mm: float
    operator_reproducibility_p95_mm: float
    manual_bias_mm: float
    manual_mae_mm: float
    bland_altman_lower_mm: float
    bland_altman_upper_mm: float
    false_pass_rate: float
    false_fail_rate: float
    gauge_rr: GaugeRrComponents
    repeatability_pass: bool
    reproducibility_pass: bool
    manual_agreement_pass: bool
    false_pass_rate_pass: bool
    false_fail_rate_pass: bool
    gauge_rr_pass: bool
    overall_pass: bool


class StudyReport(BaseModel):
    """Versioned validation-study report."""

    schema_version: int = 1
    generated_at_utc: datetime = Field(default_factory=lambda: datetime.now(UTC))
    thresholds: StudyThresholds
    poms: tuple[PomStudyMetrics, ...]


def study_input_schema() -> dict[str, object]:
    """Return the versioned normalized observation JSON Schema."""

    return ValidationStudyDataset.model_json_schema()
