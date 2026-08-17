"""Structured tech-pack parsing and canonical POM mapping."""

from __future__ import annotations

import csv
import json
import zipfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
from pathlib import Path
from typing import cast
from xml.etree import ElementTree

from pydantic import BaseModel, Field, model_validator

from specproof_measurement_service.ontology import PomOntology


class MappingStatus(StrEnum):
    """State of a brand term to canonical POM mapping."""

    APPROVED = "approved"
    AMBIGUOUS = "ambiguous"
    UNKNOWN = "unknown"


class ToleranceDirection(StrEnum):
    """Tolerance comparison strategy."""

    BILATERAL = "bilateral"
    UNILATERAL_ABOVE = "unilateral_above"
    UNILATERAL_BELOW = "unilateral_below"
    ASYMMETRIC = "asymmetric"


class GradingRule(BaseModel):
    """Target and tolerance for one size and POM."""

    size_code: str
    target_mm: float
    lower_tolerance_mm: float
    upper_tolerance_mm: float
    tolerance_direction: ToleranceDirection = ToleranceDirection.BILATERAL


class TechPackPom(BaseModel):
    """Imported brand POM row with canonical mapping metadata."""

    original_term: str
    canonical_pom_id: str | None
    mapping_status: MappingStatus
    grading_rules: tuple[GradingRule, ...]


class TechPackVersion(BaseModel):
    """Immutable structured tech-pack version."""

    schema_version: int = 1
    tech_pack_id: str
    version: int
    brand: str
    style_code: str
    garment_category: str
    imported_poms: tuple[TechPackPom, ...]
    approved: bool = False
    referenced_by_inspection: bool = False
    version_hash_sha256: str = Field(default="")

    @model_validator(mode="after")
    def populate_hash(self) -> TechPackVersion:
        if not self.version_hash_sha256:
            payload = self.model_dump(mode="json", exclude={"version_hash_sha256"})
            canonical = json.dumps(
                payload,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            )
            self.version_hash_sha256 = sha256(canonical.encode("utf-8")).hexdigest()
        return self

    def ensure_mutable(self) -> None:
        """Raise if this version may no longer be modified."""

        if self.referenced_by_inspection:
            raise ValueError("Referenced tech-pack versions are immutable")


@dataclass(frozen=True, slots=True)
class MappingResolver:
    """Deterministic brand term resolver."""

    ontology: PomOntology
    aliases: dict[str, str]

    def resolve(self, original_term: str) -> tuple[str | None, MappingStatus]:
        """Resolve a brand POM term to a canonical id."""

        normalized = _normalize_term(original_term)
        if normalized in self.aliases:
            return self.aliases[normalized], MappingStatus.APPROVED
        matches = [
            pom.id
            for pom in self.ontology.poms
            if normalized in {_normalize_term(pom.id), _normalize_term(pom.canonical_name)}
        ]
        if len(matches) == 1:
            return matches[0], MappingStatus.APPROVED
        if matches:
            return None, MappingStatus.AMBIGUOUS
        return None, MappingStatus.UNKNOWN


def default_mapping_resolver(ontology: PomOntology) -> MappingResolver:
    """Return default aliases for MVP T-shirt tech packs."""

    return MappingResolver(
        ontology=ontology,
        aliases={
            "chest": "chest_width",
            "chest width": "chest_width",
            "across chest": "chest_width",
            "shoulder": "shoulder_width",
            "shoulder width": "shoulder_width",
            "body length": "body_length",
            "length": "body_length",
            "sleeve opening": "sleeve_opening",
            "sleeve hem": "sleeve_opening",
            "hem": "hem_width",
            "hem width": "hem_width",
            "neck": "neck_width",
            "neck width": "neck_width",
        },
    )


def parse_csv_tech_pack(
    path: Path,
    resolver: MappingResolver,
    **metadata: object,
) -> TechPackVersion:
    """Parse a structured CSV tech pack."""

    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = tuple(
            {str(key): value for key, value in row.items() if key is not None}
            for row in csv.DictReader(handle)
        )
    return _rows_to_tech_pack(rows, resolver, metadata)


def parse_json_tech_pack(path: Path, resolver: MappingResolver) -> TechPackVersion:
    """Parse a structured JSON tech pack."""

    raw_data = cast(object, json.loads(path.read_text(encoding="utf-8")))
    if not isinstance(raw_data, dict):
        raise ValueError("Tech-pack JSON must contain an object")
    data = cast(dict[object, object], raw_data)
    metadata = {str(key): value for key, value in data.items()}
    raw_rows = metadata.get("rows")
    if not isinstance(raw_rows, list):
        raise ValueError("Tech-pack JSON 'rows' must contain an array")
    rows: list[dict[str, object]] = []
    for raw_row in cast(list[object], raw_rows):
        if not isinstance(raw_row, dict):
            raise ValueError("Each tech-pack row must contain an object")
        row = cast(dict[object, object], raw_row)
        rows.append({str(key): value for key, value in row.items()})
    return _rows_to_tech_pack(rows, resolver, metadata)


def parse_xlsx_tech_pack(
    path: Path,
    resolver: MappingResolver,
    **metadata: object,
) -> TechPackVersion:
    """Parse a structured XLSX tech pack from the first worksheet."""

    rows = _read_first_xlsx_sheet(path)
    return _rows_to_tech_pack(rows, resolver, metadata)


def _read_first_xlsx_sheet(path: Path) -> tuple[dict[str, object], ...]:
    with zipfile.ZipFile(path, mode="r") as archive:
        shared_strings = _read_shared_strings(archive)
        sheet_xml = archive.read("xl/worksheets/sheet1.xml")
    namespace = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    root = ElementTree.fromstring(sheet_xml)
    parsed_rows: list[list[str]] = []
    for row in root.findall(".//x:sheetData/x:row", namespace):
        values: list[str] = []
        for cell in row.findall("x:c", namespace):
            cell_type = cell.attrib.get("t")
            value = cell.find("x:v", namespace)
            if value is None or value.text is None:
                values.append("")
            elif cell_type == "s":
                values.append(shared_strings[int(value.text)])
            else:
                values.append(value.text)
        parsed_rows.append(values)
    if not parsed_rows:
        return ()
    headers = parsed_rows[0]
    return tuple(dict(zip(headers, row, strict=True)) for row in parsed_rows[1:])


def _read_shared_strings(archive: zipfile.ZipFile) -> tuple[str, ...]:
    try:
        payload = archive.read("xl/sharedStrings.xml")
    except KeyError:
        return ()
    namespace = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    root = ElementTree.fromstring(payload)
    strings: list[str] = []
    for item in root.findall("x:si", namespace):
        text = "".join(node.text or "" for node in item.findall(".//x:t", namespace))
        strings.append(text)
    return tuple(strings)


def _rows_to_tech_pack(
    rows: Sequence[Mapping[str, object]],
    resolver: MappingResolver,
    metadata: Mapping[str, object],
) -> TechPackVersion:
    poms: dict[str, list[GradingRule]] = {}
    for row in rows:
        original_term = str(row.get("pom") or row.get("original_term") or row.get("name"))
        size_code = str(row.get("size") or row.get("size_code"))
        target_mm = _to_float(row.get("target_mm") or row.get("target"), default=0.0)
        lower = _to_float(
            row.get("lower_tolerance_mm")
            or row.get("tolerance_minus_mm")
            or row.get("tolerance"),
            default=0.0,
        )
        upper = _to_float(
            row.get("upper_tolerance_mm")
            or row.get("tolerance_plus_mm")
            or row.get("tolerance"),
            default=0.0,
        )
        poms.setdefault(original_term, []).append(
            GradingRule(
                size_code=size_code,
                target_mm=target_mm,
                lower_tolerance_mm=abs(lower),
                upper_tolerance_mm=abs(upper),
            )
        )
    imported: list[TechPackPom] = []
    for original_term, rules in poms.items():
        canonical_id, status = resolver.resolve(original_term)
        imported.append(
            TechPackPom(
                original_term=original_term,
                canonical_pom_id=canonical_id,
                mapping_status=status,
                grading_rules=tuple(rules),
            )
        )
    return TechPackVersion(
        tech_pack_id=str(metadata.get("tech_pack_id", "tech-pack")),
        version=_to_int(metadata.get("version"), default=1),
        brand=str(metadata.get("brand", "Unknown")),
        style_code=str(metadata.get("style_code", "UNKNOWN")),
        garment_category=str(metadata.get("garment_category", "t_shirt")),
        imported_poms=tuple(imported),
        approved=all(pom.mapping_status == MappingStatus.APPROVED for pom in imported),
    )


def _to_float(value: object, *, default: float) -> float:
    if value is None or value == "":
        return default
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise ValueError(f"Expected a numeric tech-pack value, received {type(value).__name__}")
    return float(value)


def _to_int(value: object, *, default: int) -> int:
    if value is None or value == "":
        return default
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise ValueError(f"Expected an integer tech-pack value, received {type(value).__name__}")
    return int(value)


def _normalize_term(value: str) -> str:
    return " ".join(value.replace("_", " ").replace("-", " ").strip().lower().split())
