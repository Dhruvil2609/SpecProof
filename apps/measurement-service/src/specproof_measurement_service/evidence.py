"""Canonical evidence records for measurement inspections."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from hashlib import sha256

from pydantic import BaseModel, Field

from specproof_measurement_service.decision import InspectionDecision


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""

    return datetime.now(UTC)


class EvidenceVersions(BaseModel):
    """Version bindings used to produce evidence."""

    calibration_record_id: str
    model_version: str
    ontology_version: str
    compiler_version: str


class EvidenceRecord(BaseModel):
    """Tamper-detectable inspection evidence package."""

    schema_version: int = 1
    evidence_id: str
    tenant_id: str
    inspection_id: str
    capture_id: str
    capture_hash_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    produced_at_utc: datetime = Field(default_factory=utc_now)
    versions: EvidenceVersions
    decision: InspectionDecision
    previous_hash_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    record_hash_sha256: str = Field(default="")

    def canonical_payload(self) -> dict[str, object]:
        """Return payload used for hash calculation."""

        return self.model_dump(mode="json", exclude={"record_hash_sha256"})

    def to_canonical_json(self) -> str:
        """Return stable canonical JSON including record hash."""

        return json.dumps(
            self.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )

    def compute_hash(self) -> str:
        """Compute the SHA-256 hash over canonical evidence payload."""

        canonical = json.dumps(
            self.canonical_payload(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        return sha256(canonical.encode("utf-8")).hexdigest()

    def seal(self) -> EvidenceRecord:
        """Return this evidence record with a populated hash."""

        return self.model_copy(update={"record_hash_sha256": self.compute_hash()})

    def verify_hash(self) -> bool:
        """Return true when the stored hash matches the canonical payload."""

        return self.record_hash_sha256 == self.compute_hash()

    def to_audit_event_payload(self) -> dict[str, object]:
        """Return append-only audit event payload."""

        return {
            "event_type": "inspection.evidence.created",
            "entity_type": "inspection",
            "entity_id": self.inspection_id,
            "payload": self.model_dump(mode="json"),
        }
