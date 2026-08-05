"""Canonical POM ontology for deterministic garment measurement."""

from __future__ import annotations

import json
from enum import StrEnum

from pydantic import BaseModel, Field, model_validator

ONTOLOGY_VERSION = "1.0.0"


class AnchorType(StrEnum):
    """Supported measurement anchor categories."""

    LANDMARK = "landmark"
    SEAM = "seam"
    EDGE = "edge"
    OFFSET = "offset"


class PathType(StrEnum):
    """Supported path construction strategies."""

    STRAIGHT = "straight"
    PROJECTED = "projected"
    CONTOUR = "contour"
    GEODESIC = "geodesic"


class RoundingMode(StrEnum):
    """Supported final measurement rounding policies."""

    NONE = "none"
    NEAREST_MM = "nearest_mm"
    NEAREST_HALF_MM = "nearest_half_mm"


class MeasurementModifier(BaseModel):
    """Measurement post-processing modifiers."""

    doubled: bool = False
    offset_mm: float = 0.0
    rounding: RoundingMode = RoundingMode.NEAREST_MM


class AnchorDefinition(BaseModel):
    """One named anchor used by a canonical POM."""

    id: str
    type: AnchorType
    landmark_name: str | None = None
    fallback_landmark_names: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_landmark(self) -> AnchorDefinition:
        if self.type == AnchorType.LANDMARK and not self.landmark_name:
            raise ValueError("landmark anchors require landmark_name")
        return self


class CanonicalPom(BaseModel):
    """Canonical point-of-measure definition."""

    id: str
    canonical_name: str
    description: str
    garment_categories: tuple[str, ...]
    start_anchor: AnchorDefinition
    end_anchor: AnchorDefinition
    path_type: PathType
    modifiers: MeasurementModifier = Field(default_factory=MeasurementModifier)
    confidence_threshold: float = Field(ge=0.0, le=1.0)
    unit: str = "mm"


class PomOntology(BaseModel):
    """Semantic-versioned POM ontology document."""

    schema_version: int = 1
    ontology_version: str
    poms: tuple[CanonicalPom, ...]

    @model_validator(mode="after")
    def validate_unique_ids(self) -> PomOntology:
        ids = [pom.id for pom in self.poms]
        if len(ids) != len(set(ids)):
            raise ValueError("POM ids must be unique")
        return self

    def by_id(self, pom_id: str) -> CanonicalPom:
        """Return one canonical POM by id."""

        for pom in self.poms:
            if pom.id == pom_id:
                return pom
        raise KeyError(f"Unknown POM id: {pom_id}")

    def to_canonical_json(self) -> str:
        """Return stable canonical JSON."""

        return json.dumps(
            self.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )


def ontology_json_schema() -> dict[str, object]:
    """Return JSON Schema for ontology validation."""

    return PomOntology.model_json_schema()


def tshirt_ontology() -> PomOntology:
    """Return the MVP T-shirt ontology."""

    return PomOntology(
        ontology_version=ONTOLOGY_VERSION,
        poms=(
            _pom("chest_width", "Chest Width", "side_seam_left", "side_seam_right"),
            _pom("shoulder_width", "Shoulder Width", "shoulder_left", "shoulder_right"),
            _pom("body_length", "Body Length", "neck_left", "hem_left", PathType.PROJECTED),
            _pom("sleeve_opening", "Sleeve Opening", "sleeve_hem_left", "sleeve_hem_right"),
            _pom("hem_width", "Hem Width", "hem_left", "hem_right"),
            _pom("neck_width", "Neck Width", "neck_left", "neck_right"),
        ),
    )


def _pom(
    pom_id: str,
    name: str,
    start: str,
    end: str,
    path_type: PathType = PathType.STRAIGHT,
) -> CanonicalPom:
    return CanonicalPom(
        id=pom_id,
        canonical_name=name,
        description=f"{name} measured on a flat relaxed T-shirt.",
        garment_categories=("t_shirt",),
        start_anchor=AnchorDefinition(
            id=f"{pom_id}_start",
            type=AnchorType.LANDMARK,
            landmark_name=start,
        ),
        end_anchor=AnchorDefinition(
            id=f"{pom_id}_end",
            type=AnchorType.LANDMARK,
            landmark_name=end,
        ),
        path_type=path_type,
        confidence_threshold=0.75,
    )
