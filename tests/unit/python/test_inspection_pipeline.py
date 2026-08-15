from __future__ import annotations

import csv
from pathlib import Path
from uuid import UUID, uuid4

import numpy as np
import pytest
from specproof_capture_service import CapturePackageWriter, StreamProfile
from specproof_capture_service.capture_package import CapturePackageReader
from specproof_capture_service.models import CameraExtrinsics, CameraFrame, CameraIntrinsics
from specproof_measurement_service import (
    InspectionContext,
    InspectionPipeline,
    InspectionPipelineRequest,
    TechPackVersion,
    default_mapping_resolver,
    parse_csv_tech_pack,
    tshirt_ontology,
)
from specproof_measurement_service.pipeline import utc_now


@pytest.mark.unit
def test_inspection_pipeline_runs_to_sealed_platform_payload(tmp_path: Path) -> None:
    station_id = uuid4()
    calibration_id = uuid4()
    package_path = _write_package(tmp_path, station_id, calibration_id)
    manifest = CapturePackageReader().read_manifest(package_path)
    tech_pack_id = uuid4()
    tech_pack = _tech_pack(tmp_path, tech_pack_id)
    context = InspectionContext(
        tenant_id=uuid4(),
        station_id=station_id,
        inspection_id=uuid4(),
        capture_id=UUID(manifest.capture_id),
        calibration_id=calibration_id,
        order_code="ORDER-100",
        style_code="TEE-100",
        size_code="M",
        tech_pack_id=tech_pack_id,
        tech_pack_version=1,
    )

    result = InspectionPipeline().run(
        InspectionPipelineRequest(
            context=context,
            package_path=package_path,
            tech_pack=tech_pack,
        )
    )

    payload = result.platform_submission.to_canonical_payload()
    assert result.processing_status == "completed"
    assert result.evidence.verify_hash() is True
    assert result.evidence.inspection_id == str(context.inspection_id)
    assert payload["inspectionId"] == str(context.inspection_id)
    evidence_payload = payload["evidence"]
    assert isinstance(evidence_payload, dict)
    assert evidence_payload["recordHashSha256"] == result.evidence.record_hash_sha256
    assert [timing.stage for timing in result.stage_timings] == [
        "context_validation",
        "perception",
        "compilation",
        "measurement",
        "decision",
        "evidence",
        "total",
    ]


@pytest.mark.unit
def test_inspection_pipeline_rejects_capture_context_mismatch(tmp_path: Path) -> None:
    station_id = uuid4()
    calibration_id = uuid4()
    package_path = _write_package(tmp_path, station_id, calibration_id)
    manifest = CapturePackageReader().read_manifest(package_path)
    tech_pack_id = uuid4()

    request = InspectionPipelineRequest(
        context=InspectionContext(
            tenant_id=uuid4(),
            station_id=uuid4(),
            inspection_id=uuid4(),
            capture_id=UUID(manifest.capture_id),
            calibration_id=calibration_id,
            order_code="ORDER-100",
            style_code="TEE-100",
            size_code="M",
            tech_pack_id=tech_pack_id,
            tech_pack_version=1,
        ),
        package_path=package_path,
        tech_pack=_tech_pack(tmp_path, tech_pack_id),
    )

    with pytest.raises(ValueError, match="station_id"):
        InspectionPipeline().run(request)


@pytest.mark.unit
def test_inspection_request_rejects_wrong_tech_pack_binding(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="tech_pack_id"):
        InspectionPipelineRequest(
            context=InspectionContext(
                tenant_id=uuid4(),
                station_id=uuid4(),
                inspection_id=uuid4(),
                capture_id=uuid4(),
                calibration_id=uuid4(),
                order_code="ORDER-100",
                style_code="TEE-100",
                size_code="M",
                tech_pack_id=uuid4(),
                tech_pack_version=1,
            ),
            package_path=tmp_path / "capture.spcapture",
            tech_pack=_tech_pack(tmp_path, uuid4()),
        )


def _tech_pack(tmp_path: Path, tech_pack_id: UUID) -> TechPackVersion:
    path = tmp_path / f"{tech_pack_id}.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=(
                "pom",
                "size",
                "target_mm",
                "lower_tolerance_mm",
                "upper_tolerance_mm",
            ),
        )
        writer.writeheader()
        writer.writerow(
            {
                "pom": "Across Chest",
                "size": "M",
                "target_mm": "100",
                "lower_tolerance_mm": "2",
                "upper_tolerance_mm": "2",
            }
        )
    return parse_csv_tech_pack(
        path,
        default_mapping_resolver(tshirt_ontology()),
        tech_pack_id=str(tech_pack_id),
        version=1,
        brand="Synthetic",
        style_code="TEE-100",
        garment_category="t_shirt",
    )


def _write_package(tmp_path: Path, station_id: UUID, calibration_id: UUID) -> Path:
    mask = np.zeros((32, 40), dtype=np.bool_)
    mask[8:28, 13:27] = True
    mask[10:17, 6:13] = True
    mask[10:17, 27:34] = True
    mask[8:12, 18:22] = False
    frames = [_frame(index, mask) for index in range(3)]
    package_path = tmp_path / "integrated.spcapture"
    CapturePackageWriter().write(
        output_path=package_path,
        station_id=str(station_id),
        calibration_id=str(calibration_id),
        profile=StreamProfile(
            color_width=40,
            color_height=32,
            depth_width=40,
            depth_height=32,
            frames_per_second=30,
        ),
        frames=frames,
        environment={"fixture": "phase-7-integration"},
    )
    return package_path


def _frame(index: int, mask: np.ndarray) -> CameraFrame:
    color = np.full((32, 40, 3), 40, dtype=np.uint8)
    color[mask] = np.array([80, 140, 180], dtype=np.uint8)
    depth = np.full((32, 40), 1000, dtype=np.uint16)
    depth[mask] = np.uint16(990 + index)
    intrinsics = CameraIntrinsics(
        width=40,
        height=32,
        fx=40.0,
        fy=32.0,
        ppx=20.0,
        ppy=16.0,
        distortion_model="none",
    )
    return CameraFrame(
        frame_id=str(uuid4()),
        camera_serial="MOCK-INTEGRATION-001",
        captured_at_utc=utc_now(),
        color_bgr=color,
        depth_units=depth,
        depth_scale_metres=0.001,
        color_intrinsics=intrinsics,
        depth_intrinsics=intrinsics,
        depth_to_color=CameraExtrinsics(
            rotation=(1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0),
            translation_metres=(0.0, 0.0, 0.0),
        ),
    )
