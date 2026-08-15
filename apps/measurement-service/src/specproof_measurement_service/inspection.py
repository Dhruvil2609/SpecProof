"""Integrated station inspection orchestration and platform payload mapping."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from time import perf_counter_ns
from typing import TypeVar
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, model_validator
from specproof_capture_service.capture_package import CapturePackageReader
from specproof_capture_service.models import CaptureManifest

from specproof_measurement_service.compiler import (
    COMPILER_VERSION,
    CompiledMeasurementRule,
    compile_tech_pack,
)
from specproof_measurement_service.decision import InspectionDecision, decide_inspection
from specproof_measurement_service.evidence import EvidenceRecord, EvidenceVersions
from specproof_measurement_service.executor import ExecutedMeasurement, execute_rules
from specproof_measurement_service.ontology import PomOntology, tshirt_ontology
from specproof_measurement_service.pipeline import PerceptionPipeline, PerceptionResult
from specproof_measurement_service.techpack import TechPackVersion


class InspectionContext(BaseModel):
    """Identifiers and production selections required for one inspection."""

    tenant_id: UUID
    station_id: UUID
    inspection_id: UUID
    capture_id: UUID
    calibration_id: UUID
    station_code: str = Field(min_length=1)
    order_code: str = Field(min_length=1)
    style_code: str = Field(min_length=1)
    size_code: str = Field(min_length=1)
    batch_id: UUID | None = None
    tech_pack_id: UUID
    tech_pack_version: int = Field(gt=0)


class InspectionPipelineRequest(BaseModel):
    """Validated input for the integrated inspection pipeline."""

    context: InspectionContext
    package_path: Path
    tech_pack: TechPackVersion
    previous_evidence_hash_sha256: str | None = Field(
        default=None,
        pattern=r"^[a-f0-9]{64}$",
    )

    @model_validator(mode="after")
    def validate_version_bindings(self) -> InspectionPipelineRequest:
        if self.tech_pack.tech_pack_id != str(self.context.tech_pack_id):
            raise ValueError("tech_pack_id does not match the selected tech pack")
        if self.tech_pack.version != self.context.tech_pack_version:
            raise ValueError("tech_pack_version does not match the selected tech pack")
        if self.tech_pack.style_code != self.context.style_code:
            raise ValueError("style_code does not match the selected tech pack")
        return self


class StageTiming(BaseModel):
    """Monotonic elapsed time for one pipeline stage."""

    stage: str
    duration_ms: float = Field(ge=0)


class PlatformInspectionSubmission(BaseModel):
    """Canonical payload accepted by the platform inspection endpoint."""

    tenant_id: UUID
    inspection_id: UUID
    capture_id: UUID
    station_id: UUID
    batch_id: UUID | None
    station_code: str
    order_code: str
    style_code: str
    size_code: str
    result: dict[str, object]
    evidence: dict[str, object]

    def to_canonical_payload(self) -> dict[str, object]:
        """Return the platform JSON contract with camel-case property names."""

        return {
            "tenantId": str(self.tenant_id),
            "inspectionId": str(self.inspection_id),
            "captureId": str(self.capture_id),
            "stationId": str(self.station_id),
            "batchId": None if self.batch_id is None else str(self.batch_id),
            "stationCode": self.station_code,
            "orderCode": self.order_code,
            "styleCode": self.style_code,
            "sizeCode": self.size_code,
            "result": self.result,
            "evidence": self.evidence,
        }


class InspectionPipelineResult(BaseModel):
    """Typed output from perception through sealed evidence."""

    context: InspectionContext
    perception: PerceptionResult
    compiled_rules: tuple[CompiledMeasurementRule, ...]
    measurements: tuple[ExecutedMeasurement, ...]
    decision: InspectionDecision
    evidence: EvidenceRecord
    stage_timings: tuple[StageTiming, ...]
    processing_status: str = "completed"
    platform_submission: PlatformInspectionSubmission


ResultType = TypeVar("ResultType")


class InspectionPipeline:
    """Execute the complete local inspection path without duplicating measurement logic."""

    def __init__(
        self,
        *,
        perception_pipeline: PerceptionPipeline | None = None,
        ontology: PomOntology | None = None,
    ) -> None:
        self._perception_pipeline = perception_pipeline or PerceptionPipeline()
        self._ontology = ontology or tshirt_ontology()

    def run(self, request: InspectionPipelineRequest) -> InspectionPipelineResult:
        """Run one `.spcapture` package through decision and sealed evidence."""

        total_started = perf_counter_ns()
        timings: list[StageTiming] = []

        manifest = self._timed(
            "context_validation",
            lambda: self._validate_capture_context(request),
            timings,
        )
        perception = self._timed(
            "perception",
            lambda: self._perception_pipeline.run(request.package_path),
            timings,
        )
        rules = self._timed(
            "compilation",
            lambda: compile_tech_pack(
                request.tech_pack,
                self._ontology,
                size_code=request.context.size_code,
            ),
            timings,
        )
        measurements = self._timed(
            "measurement",
            lambda: execute_rules(rules, perception),
            timings,
        )
        decision = self._timed(
            "decision",
            lambda: decide_inspection(measurements),
            timings,
        )
        evidence = self._timed(
            "evidence",
            lambda: self._seal_evidence(request, perception, decision),
            timings,
        )
        submission = self._platform_submission(
            request,
            perception,
            decision,
            evidence,
            manifest.captured_at_utc.isoformat(),
        )
        timings.append(StageTiming(stage="total", duration_ms=_elapsed_ms(total_started)))
        return InspectionPipelineResult(
            context=request.context,
            perception=perception,
            compiled_rules=rules,
            measurements=measurements,
            decision=decision,
            evidence=evidence,
            stage_timings=tuple(timings),
            platform_submission=submission,
        )

    @staticmethod
    def _timed(
        stage: str,
        operation: Callable[[], ResultType],
        timings: list[StageTiming],
    ) -> ResultType:
        started = perf_counter_ns()
        result = operation()
        timings.append(StageTiming(stage=stage, duration_ms=_elapsed_ms(started)))
        return result

    @staticmethod
    def _validate_capture_context(request: InspectionPipelineRequest) -> CaptureManifest:
        manifest = CapturePackageReader().read_manifest(request.package_path)
        context = request.context
        bindings = {
            "capture_id": (manifest.capture_id, str(context.capture_id)),
            "station_id": (manifest.station_id, str(context.station_id)),
            "calibration_id": (manifest.calibration_id, str(context.calibration_id)),
        }
        for name, (actual, expected) in bindings.items():
            if actual != expected:
                raise ValueError(f"{name} does not match the capture package")
        return manifest

    def _seal_evidence(
        self,
        request: InspectionPipelineRequest,
        perception: PerceptionResult,
        decision: InspectionDecision,
    ) -> EvidenceRecord:
        return EvidenceRecord(
            evidence_id=str(uuid4()),
            tenant_id=str(request.context.tenant_id),
            inspection_id=str(request.context.inspection_id),
            capture_id=str(request.context.capture_id),
            capture_hash_sha256=perception.package_sha256,
            versions=EvidenceVersions(
                calibration_record_id=str(request.context.calibration_id),
                model_version=perception.pipeline_version,
                ontology_version=self._ontology.ontology_version,
                compiler_version=COMPILER_VERSION,
            ),
            decision=decision,
            previous_hash_sha256=request.previous_evidence_hash_sha256,
        ).seal()

    @staticmethod
    def _platform_submission(
        request: InspectionPipelineRequest,
        perception: PerceptionResult,
        decision: InspectionDecision,
        evidence: EvidenceRecord,
        captured_at_utc: str,
    ) -> PlatformInspectionSubmission:
        measurements = [
            {
                "pomId": measurement.pom_id,
                "canonicalName": measurement.canonical_name,
                "measuredValueMm": measurement.measured_value_mm,
                "targetValueMm": measurement.target_mm,
                "lowerToleranceMm": measurement.lower_tolerance_mm,
                "upperToleranceMm": measurement.upper_tolerance_mm,
                "deviationMm": measurement.deviation_mm,
                "confidence": measurement.confidence,
                "status": measurement.status.value.title(),
                "overlay": [],
            }
            for measurement in decision.measurements
        ]
        status = decision.status.value.title()
        result: dict[str, object] = {
            "inspectionId": str(request.context.inspection_id),
            "stationId": str(request.context.station_id),
            "cameraSerial": perception.camera_serial,
            "capturedAtUtc": captured_at_utc,
            "measurements": measurements,
            "status": status,
            "evidenceRecordHash": evidence.record_hash_sha256,
        }
        evidence_payload: dict[str, object] = {
            "evidenceId": evidence.evidence_id,
            "tenantId": evidence.tenant_id,
            "inspectionId": evidence.inspection_id,
            "captureId": evidence.capture_id,
            "captureHashSha256": evidence.capture_hash_sha256,
            "producedAtUtc": evidence.produced_at_utc.isoformat(),
            "versions": {
                "calibrationRecordId": evidence.versions.calibration_record_id,
                "modelVersion": evidence.versions.model_version,
                "ontologyVersion": evidence.versions.ontology_version,
                "compilerVersion": evidence.versions.compiler_version,
                "techPackId": str(request.context.tech_pack_id),
                "techPackVersion": request.context.tech_pack_version,
            },
            "measurements": measurements,
            "status": status,
            "previousHashSha256": evidence.previous_hash_sha256,
            "recordHashSha256": evidence.record_hash_sha256,
            "signature": None,
        }
        return PlatformInspectionSubmission(
            tenant_id=request.context.tenant_id,
            inspection_id=request.context.inspection_id,
            capture_id=request.context.capture_id,
            station_id=request.context.station_id,
            batch_id=request.context.batch_id,
            station_code=request.context.station_code,
            order_code=request.context.order_code,
            style_code=request.context.style_code,
            size_code=request.context.size_code,
            result=result,
            evidence=evidence_payload,
        )


def _elapsed_ms(started_ns: int) -> float:
    return (perf_counter_ns() - started_ns) / 1_000_000
