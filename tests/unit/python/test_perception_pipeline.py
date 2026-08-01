from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import numpy as np
import pytest
from specproof_capture_service import CapturePackageWriter, StreamProfile
from specproof_capture_service.models import CameraExtrinsics, CameraFrame, CameraIntrinsics
from specproof_measurement_service import (
    PerceptionPipeline,
    PerceptionResult,
    estimate_background_from_border,
    write_perception_result,
)
from specproof_measurement_service.pipeline import utc_now


def _synthetic_tshirt_mask(*, front: bool = True) -> np.ndarray:
    mask = np.zeros((32, 40), dtype=np.bool_)
    mask[8:28, 13:27] = True
    mask[10:17, 6:13] = True
    mask[10:17, 27:34] = True
    if front:
        mask[8:12, 18:22] = False
    return mask


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
        camera_serial="MOCK-PIPELINE-001",
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


def _write_package(tmp_path: Path, *, front: bool = True) -> Path:
    mask = _synthetic_tshirt_mask(front=front)
    frames = [_frame(index, mask) for index in range(3)]
    package_path = tmp_path / "synthetic.spcapture"
    CapturePackageWriter().write(
        output_path=package_path,
        station_id="station-pipeline-001",
        calibration_id="calibration-pipeline-001",
        profile=StreamProfile(
            color_width=40,
            color_height=32,
            depth_width=40,
            depth_height=32,
            frames_per_second=30,
        ),
        frames=frames,
        environment={"fixture": "synthetic-tshirt"},
    )
    return package_path


@pytest.mark.unit
def test_estimate_background_from_border_uses_capture_edges() -> None:
    color = np.full((6, 8, 3), 20, dtype=np.uint8)
    depth = np.full((6, 8), 1000, dtype=np.uint16)
    color[2:4, 3:5] = 200
    depth[2:4, 3:5] = 950

    background = estimate_background_from_border(color, depth)

    assert np.array_equal(background.color_bgr[3, 4], np.array([20, 20, 20], dtype=np.uint8))
    assert int(background.depth_units[3, 4]) == 1000


@pytest.mark.unit
def test_perception_pipeline_loads_spcapture_and_returns_versioned_result(tmp_path: Path) -> None:
    package_path = _write_package(tmp_path, front=True)

    result = PerceptionPipeline().run(package_path)

    assert result.schema_version == 1
    assert result.pipeline_version == "phase-3-deterministic-v1"
    assert result.station_id == "station-pipeline-001"
    assert result.category == "t_shirt"
    assert result.orientation == "front"
    assert result.bounding_box is not None
    assert result.segmentation_area_pixels > 0
    assert len(result.landmarks) == 10


@pytest.mark.unit
def test_perception_result_canonical_json_round_trips(tmp_path: Path) -> None:
    result = PerceptionPipeline().run(_write_package(tmp_path, front=True))
    output_path = tmp_path / "perception-result.json"

    write_perception_result(result, output_path)
    loaded = PerceptionResult.model_validate_json(output_path.read_text(encoding="utf-8"))

    assert loaded == result
    assert json.loads(output_path.read_text(encoding="utf-8"))["schema_version"] == 1


@pytest.mark.unit
def test_perception_pipeline_back_neckline_requires_review(tmp_path: Path) -> None:
    package_path = _write_package(tmp_path, front=False)

    result = PerceptionPipeline().run(package_path)

    assert result.orientation == "back"
    assert result.review_required is True
