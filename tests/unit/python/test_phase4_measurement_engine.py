from __future__ import annotations

import csv
import zipfile
from pathlib import Path

from specproof_measurement_service import (
    COMPILER_VERSION,
    EvidenceRecord,
    EvidenceVersions,
    InspectionDecisionStatus,
    MeasurementExecutionStatus,
    PomDecisionStatus,
    decide_inspection,
    default_mapping_resolver,
    execute_rules,
    ontology_json_schema,
    parse_csv_tech_pack,
    parse_json_tech_pack,
    parse_xlsx_tech_pack,
    tshirt_ontology,
)
from specproof_measurement_service.compiler import compile_tech_pack
from specproof_measurement_service.pipeline import (
    PerceptionBoundingBox,
    PerceptionLandmark,
    PerceptionMesh,
    PerceptionResult,
    PerceptionSurfaceMapping,
    PerceptionSurfaceMapPoint,
    PerceptionSurfaceQuality,
)


def test_phase4_ontology_validates_against_schema() -> None:
    ontology = tshirt_ontology()
    schema = ontology_json_schema()

    assert schema["type"] == "object"
    assert ontology.ontology_version == "1.0.0"
    assert len(ontology.poms) == 6
    assert ontology.by_id("chest_width").canonical_name == "Chest Width"


def test_phase4_csv_json_and_xlsx_tech_packs_parse_and_map(tmp_path: Path) -> None:
    resolver = default_mapping_resolver(tshirt_ontology())
    rows = [
        {
            "pom": "Across Chest",
            "size": "M",
            "target_mm": "100",
            "lower_tolerance_mm": "2",
            "upper_tolerance_mm": "3",
        },
        {
            "pom": "Shoulder Width",
            "size": "M",
            "target_mm": "80",
            "lower_tolerance_mm": "2",
            "upper_tolerance_mm": "2",
        },
    ]
    csv_path = tmp_path / "tech-pack.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    json_path = tmp_path / "tech-pack.json"
    json_path.write_text(
        (
            '{"tech_pack_id":"tp-json","version":1,"brand":"Brand",'
            '"style_code":"TEE","garment_category":"t_shirt","rows":'
            f"{rows!r}".replace("'", '"')
            + "}"
        ),
        encoding="utf-8",
    )
    xlsx_path = tmp_path / "tech-pack.xlsx"
    _write_minimal_xlsx(xlsx_path, [tuple(rows[0].keys()), *[tuple(row.values()) for row in rows]])

    csv_pack = parse_csv_tech_pack(csv_path, resolver, tech_pack_id="tp-csv")
    json_pack = parse_json_tech_pack(json_path, resolver)
    xlsx_pack = parse_xlsx_tech_pack(xlsx_path, resolver, tech_pack_id="tp-xlsx")

    assert csv_pack.approved is True
    assert json_pack.imported_poms[0].canonical_pom_id == "chest_width"
    assert xlsx_pack.imported_poms[1].original_term == "Shoulder Width"
    assert len(csv_pack.version_hash_sha256) == 64


def test_phase4_referenced_tech_pack_version_is_immutable(tmp_path: Path) -> None:
    resolver = default_mapping_resolver(tshirt_ontology())
    path = _write_minimal_csv(tmp_path)
    tech_pack = parse_csv_tech_pack(path, resolver).model_copy(
        update={"referenced_by_inspection": True}
    )

    try:
        tech_pack.ensure_mutable()
    except ValueError as exc:
        assert "immutable" in str(exc)
    else:
        raise AssertionError("Referenced tech pack should reject mutation")


def test_phase4_compiler_produces_executable_rule(tmp_path: Path) -> None:
    resolver = default_mapping_resolver(tshirt_ontology())
    tech_pack = parse_csv_tech_pack(_write_minimal_csv(tmp_path), resolver)
    rules = compile_tech_pack(tech_pack, tshirt_ontology(), size_code="M")

    assert len(rules) == 1
    assert rules[0].compiler_version == COMPILER_VERSION
    assert rules[0].pom_id == "chest_width"
    assert rules[0].start_anchor.landmark_name == "side_seam_left"


def test_phase4_executor_measures_known_geometry_and_doubled_rule(tmp_path: Path) -> None:
    resolver = default_mapping_resolver(tshirt_ontology())
    tech_pack = parse_csv_tech_pack(_write_minimal_csv(tmp_path, target_mm=200.0), resolver)
    rule = compile_tech_pack(tech_pack, tshirt_ontology(), size_code="M")[0]
    doubled_rule = rule.model_copy(
        update={"modifiers": rule.modifiers.model_copy(update={"doubled": True})}
    )
    perception = _perception_result(width_mm=100.0, surface_quality=1.0)

    measured = execute_rules((rule, doubled_rule), perception)

    assert measured[0].measured_value_mm == 100.0
    assert measured[0].status == MeasurementExecutionStatus.MEASURED
    assert measured[1].measured_value_mm == 200.0


def test_phase4_decision_engine_routes_all_status_paths(tmp_path: Path) -> None:
    resolver = default_mapping_resolver(tshirt_ontology())
    tech_pack = parse_csv_tech_pack(_write_minimal_csv(tmp_path, target_mm=100.0), resolver)
    rule = compile_tech_pack(tech_pack, tshirt_ontology(), size_code="M")[0]

    pass_decision = decide_inspection(execute_rules((rule,), _perception_result(width_mm=100.0)))
    fail_decision = decide_inspection(execute_rules((rule,), _perception_result(width_mm=110.0)))
    review_decision = decide_inspection(
        execute_rules((rule,), _perception_result(width_mm=100.0, surface_quality=0.6))
    )
    invalid_decision = decide_inspection(
        execute_rules((rule,), _perception_result(width_mm=100.0, category="trouser"))
    )

    assert pass_decision.status == InspectionDecisionStatus.PASS
    assert pass_decision.measurements[0].status == PomDecisionStatus.PASS
    assert fail_decision.status == InspectionDecisionStatus.FAIL
    assert review_decision.status == InspectionDecisionStatus.REVIEW
    assert invalid_decision.status == InspectionDecisionStatus.INVALID


def test_phase4_evidence_record_hash_validates(tmp_path: Path) -> None:
    resolver = default_mapping_resolver(tshirt_ontology())
    tech_pack = parse_csv_tech_pack(_write_minimal_csv(tmp_path), resolver)
    rule = compile_tech_pack(tech_pack, tshirt_ontology(), size_code="M")[0]
    decision = decide_inspection(execute_rules((rule,), _perception_result(width_mm=100.0)))
    record = EvidenceRecord(
        evidence_id="evidence-1",
        tenant_id="tenant-1",
        inspection_id="inspection-1",
        capture_id="capture-1",
        capture_hash_sha256="a" * 64,
        versions=EvidenceVersions(
            calibration_record_id="calibration-1",
            model_version="phase-3-deterministic-v1",
            ontology_version="1.0.0",
            compiler_version=COMPILER_VERSION,
        ),
        decision=decision,
    ).seal()

    assert record.verify_hash() is True
    assert record.to_audit_event_payload()["event_type"] == "inspection.evidence.created"
    assert record.model_copy(update={"capture_id": "tampered"}).verify_hash() is False


def _write_minimal_csv(tmp_path: Path, *, target_mm: float = 100.0) -> Path:
    path = tmp_path / "minimal.csv"
    path.write_text(
        "pom,size,target_mm,lower_tolerance_mm,upper_tolerance_mm\n"
        f"Across Chest,M,{target_mm},2,2\n",
        encoding="utf-8",
    )
    return path


def _write_minimal_xlsx(path: Path, rows: list[tuple[str, ...]]) -> None:
    shared_values: list[str] = []
    shared_index: dict[str, int] = {}
    row_xml: list[str] = []
    for row_index, row in enumerate(rows, start=1):
        cells: list[str] = []
        for column_index, value in enumerate(row):
            column = chr(ord("A") + column_index)
            index = shared_index.setdefault(value, len(shared_values))
            if index == len(shared_values):
                shared_values.append(value)
            cells.append(f'<c r="{column}{row_index}" t="s"><v>{index}</v></c>')
        row_xml.append(f'<row r="{row_index}">{"".join(cells)}</row>')
    shared_xml = "".join(f"<si><t>{value}</t></si>" for value in shared_values)
    with zipfile.ZipFile(path, mode="w") as archive:
        archive.writestr(
            "[Content_Types].xml",
            (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                '<Default Extension="rels" '
                'ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                '<Default Extension="xml" ContentType="application/xml"/>'
                "</Types>"
            ),
        )
        archive.writestr(
            "xl/sharedStrings.xml",
            (
                '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                f"{shared_xml}</sst>"
            ),
        )
        archive.writestr(
            "xl/worksheets/sheet1.xml",
            (
                '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                f'<sheetData>{"".join(row_xml)}</sheetData></worksheet>'
            ),
        )


def _perception_result(
    *,
    width_mm: float,
    surface_quality: float = 1.0,
    category: str = "t_shirt",
) -> PerceptionResult:
    return PerceptionResult(
        capture_id="capture-1",
        station_id="station-1",
        camera_serial="camera-1",
        package_sha256="b" * 64,
        category=category,
        orientation="front",
        segmentation_confidence=1.0,
        segmentation_area_pixels=2,
        bounding_box=PerceptionBoundingBox(left=0, top=0, width=11, height=1),
        surface_quality=PerceptionSurfaceQuality(
            overall=surface_quality,
            valid_depth_ratio=1.0,
            surface_coverage=1.0,
            plane_fit_score=1.0,
            normal_consistency=1.0,
            reason="ok",
        ),
        surface_mapping=PerceptionSurfaceMapping(
            coordinate_system="uv_mm",
            mapped_pixel_count=2,
            u_min_mm=0.0,
            u_max_mm=width_mm,
            v_min_mm=0.0,
            v_max_mm=0.0,
            area_distortion_percent=0.0,
            points=(
                PerceptionSurfaceMapPoint(
                    pixel_x=0,
                    pixel_y=0,
                    x_metres=0.0,
                    y_metres=0.0,
                    z_metres=0.0,
                    u_mm=0.0,
                    v_mm=0.0,
                ),
                PerceptionSurfaceMapPoint(
                    pixel_x=10,
                    pixel_y=0,
                    x_metres=width_mm / 1000.0,
                    y_metres=0.0,
                    z_metres=0.0,
                    u_mm=width_mm,
                    v_mm=0.0,
                ),
            ),
        ),
        mesh=PerceptionMesh(
            schema_version=1,
            coordinate_system="uv_mm",
            vertex_count=2,
            triangle_count=0,
            triangle_indices=(),
        ),
        landmarks=(
            PerceptionLandmark(
                name="side_seam_left",
                x=0.0,
                y=0.0,
                confidence=1.0,
                status="detected",
            ),
            PerceptionLandmark(
                name="side_seam_right",
                x=10.0,
                y=0.0,
                confidence=1.0,
                status="detected",
            ),
        ),
        landmark_confidence=1.0,
        review_required=surface_quality < 0.75,
        metadata={"source": "unit-test"},
    )
