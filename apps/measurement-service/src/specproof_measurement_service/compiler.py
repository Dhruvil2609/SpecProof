"""Compile approved tech-pack POMs into executable measurement rules."""

from __future__ import annotations

from pydantic import BaseModel

from specproof_measurement_service.ontology import (
    AnchorDefinition,
    MeasurementModifier,
    PathType,
    PomOntology,
)
from specproof_measurement_service.techpack import (
    MappingStatus,
    TechPackVersion,
    ToleranceDirection,
)

COMPILER_VERSION = "phase-4-compiler-v1"


class CompiledMeasurementRule(BaseModel):
    """Executable measurement rule."""

    schema_version: int = 1
    compiler_version: str
    ontology_version: str
    tech_pack_id: str
    tech_pack_version: int
    pom_id: str
    canonical_name: str
    original_term: str
    size_code: str
    target_mm: float
    lower_tolerance_mm: float
    upper_tolerance_mm: float
    tolerance_direction: ToleranceDirection
    start_anchor: AnchorDefinition
    end_anchor: AnchorDefinition
    path_type: PathType
    modifiers: MeasurementModifier
    confidence_threshold: float
    unit: str


def compile_tech_pack(
    tech_pack: TechPackVersion,
    ontology: PomOntology,
    *,
    size_code: str,
) -> tuple[CompiledMeasurementRule, ...]:
    """Compile approved tech-pack rows for one size."""

    if not tech_pack.approved:
        raise ValueError("Tech pack must be approved before compilation")
    rules: list[CompiledMeasurementRule] = []
    for imported_pom in tech_pack.imported_poms:
        if (
            imported_pom.mapping_status != MappingStatus.APPROVED
            or imported_pom.canonical_pom_id is None
        ):
            raise ValueError(f"POM mapping is not approved: {imported_pom.original_term}")
        grading_rule = next(
            (rule for rule in imported_pom.grading_rules if rule.size_code == size_code),
            None,
        )
        if grading_rule is None:
            continue
        pom = ontology.by_id(imported_pom.canonical_pom_id)
        rules.append(
            CompiledMeasurementRule(
                compiler_version=COMPILER_VERSION,
                ontology_version=ontology.ontology_version,
                tech_pack_id=tech_pack.tech_pack_id,
                tech_pack_version=tech_pack.version,
                pom_id=pom.id,
                canonical_name=pom.canonical_name,
                original_term=imported_pom.original_term,
                size_code=size_code,
                target_mm=grading_rule.target_mm,
                lower_tolerance_mm=grading_rule.lower_tolerance_mm,
                upper_tolerance_mm=grading_rule.upper_tolerance_mm,
                tolerance_direction=grading_rule.tolerance_direction,
                start_anchor=pom.start_anchor,
                end_anchor=pom.end_anchor,
                path_type=pom.path_type,
                modifiers=pom.modifiers,
                confidence_threshold=pom.confidence_threshold,
                unit=pom.unit,
            )
        )
    return tuple(rules)
