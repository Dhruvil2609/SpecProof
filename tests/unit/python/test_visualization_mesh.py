from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import numpy as np
import pytest
from specproof_capture_service import CapturePackageWriter, StreamProfile
from specproof_capture_service.models import CameraExtrinsics, CameraFrame, CameraIntrinsics
from specproof_measurement_service import (
    SurfaceMapPoint,
    SurfaceParameterization,
    build_indexed_mesh,
    write_indexed_mesh,
)
from specproof_measurement_service.pipeline import PerceptionPipeline, utc_now


def _surface_map_for_rectangle(width: int, height: int) -> SurfaceParameterization:
    points = tuple(
        SurfaceMapPoint(
            pixel_x=x,
            pixel_y=y,
            x_metres=x / 1000.0,
            y_metres=y / 1000.0,
            z_metres=1.0,
            u_mm=float(x),
            v_mm=float(y),
        )
        for y in range(height)
        for x in range(width)
    )
    return SurfaceParameterization(
        points=points,
        u_min_mm=0.0,
        u_max_mm=float(width - 1),
        v_min_mm=0.0,
        v_max_mm=float(height - 1),
        mapped_pixel_count=len(points),
        area_distortion_percent=0.0,
    )


def _synthetic_tshirt_mask() -> np.ndarray:
    mask = np.zeros((32, 40), dtype=np.bool_)
    mask[8:28, 13:27] = True
    mask[10:17, 6:13] = True
    mask[10:17, 27:34] = True
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
        camera_serial="MOCK-MESH-001",
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


def _write_package(tmp_path: Path) -> Path:
    mask = _synthetic_tshirt_mask()
    package_path = tmp_path / "mesh.spcapture"
    CapturePackageWriter().write(
        output_path=package_path,
        station_id="station-mesh-001",
        calibration_id="calibration-mesh-001",
        profile=StreamProfile(
            color_width=40,
            color_height=32,
            depth_width=40,
            depth_height=32,
            frames_per_second=30,
        ),
        frames=[_frame(index, mask) for index in range(3)],
    )
    return package_path


@pytest.mark.unit
def test_build_indexed_mesh_rectangular_grid_creates_two_triangles_per_cell() -> None:
    mesh = build_indexed_mesh(_surface_map_for_rectangle(width=3, height=2))

    assert mesh.vertex_count == 6
    assert mesh.triangle_count == 4
    assert mesh.triangle_indices[0] == (0, 3, 1)
    assert mesh.triangle_indices[1] == (1, 3, 4)


@pytest.mark.unit
def test_build_indexed_mesh_gap_does_not_bridge_missing_vertex() -> None:
    base = _surface_map_for_rectangle(width=3, height=3)
    points = tuple(
        point for point in base.points if not (point.pixel_x == 1 and point.pixel_y == 1)
    )
    surface_map = SurfaceParameterization(
        points=points,
        u_min_mm=0.0,
        u_max_mm=2.0,
        v_min_mm=0.0,
        v_max_mm=2.0,
        mapped_pixel_count=len(points),
        area_distortion_percent=0.0,
    )

    mesh = build_indexed_mesh(surface_map)

    assert mesh.vertex_count == 8
    assert mesh.triangle_count == 0


@pytest.mark.unit
def test_write_indexed_mesh_outputs_canonical_json(tmp_path: Path) -> None:
    mesh = build_indexed_mesh(_surface_map_for_rectangle(width=2, height=2))
    output_path = tmp_path / "mesh.json"

    write_indexed_mesh(mesh, output_path)
    loaded = json.loads(output_path.read_text(encoding="utf-8"))

    assert loaded["schema_version"] == 1
    assert loaded["vertex_count"] == 4
    assert loaded["triangle_count"] == 2
    assert output_path.read_text(encoding="utf-8").endswith("\n")


@pytest.mark.unit
def test_perception_pipeline_result_includes_mesh_metadata(tmp_path: Path) -> None:
    result = PerceptionPipeline().run(_write_package(tmp_path))

    assert result.mesh.schema_version == 1
    assert result.mesh.coordinate_system == result.surface_mapping.coordinate_system
    assert result.mesh.vertex_count == result.surface_mapping.mapped_pixel_count
    assert result.mesh.triangle_count > 0
