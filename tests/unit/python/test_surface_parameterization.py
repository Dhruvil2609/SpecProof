from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import numpy as np
import pytest
from specproof_capture_service import CapturePackageWriter, StreamProfile
from specproof_capture_service.models import CameraExtrinsics, CameraFrame, CameraIntrinsics
from specproof_measurement_service import (
    PlaneModel,
    mapping_by_pixel,
    parameterize_surface,
)
from specproof_measurement_service.pipeline import PerceptionPipeline, utc_now


def _flat_grid_points(height: int, width: int, spacing_metres: float = 0.001) -> np.ndarray:
    points = np.zeros((height, width, 3), dtype=np.float32)
    for y in range(height):
        for x in range(width):
            points[y, x] = np.array(
                [x * spacing_metres, y * spacing_metres, 1.0],
                dtype=np.float32,
            )
    return points


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
        camera_serial="MOCK-MAPPING-001",
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
    package_path = tmp_path / "mapping.spcapture"
    CapturePackageWriter().write(
        output_path=package_path,
        station_id="station-mapping-001",
        calibration_id="calibration-mapping-001",
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
def test_parameterize_surface_preserves_pixel_to_3d_to_uv_mapping() -> None:
    points = _flat_grid_points(4, 5)
    mask = np.zeros((4, 5), dtype=np.bool_)
    mask[1:3, 1:4] = True
    plane = PlaneModel(normal=(0.0, 0.0, 1.0), offset=-1.0, rms_mm=0.0)

    surface_map = parameterize_surface(
        points=points,
        garment_mask=mask,
        support_plane=plane,
    )
    by_pixel = mapping_by_pixel(surface_map)

    mapped = by_pixel[(2, 1)]
    assert surface_map.mapped_pixel_count == 6
    assert mapped.x_metres == pytest.approx(0.002)
    assert mapped.y_metres == pytest.approx(0.001)
    assert mapped.u_mm == pytest.approx(1.0)
    assert mapped.v_mm == pytest.approx(0.0)


@pytest.mark.unit
def test_parameterize_surface_flat_grid_has_low_area_distortion() -> None:
    points = _flat_grid_points(5, 5)
    mask = np.ones((5, 5), dtype=np.bool_)
    plane = PlaneModel(normal=(0.0, 0.0, 1.0), offset=-1.0, rms_mm=0.0)

    surface_map = parameterize_surface(
        points=points,
        garment_mask=mask,
        support_plane=plane,
    )

    assert surface_map.area_distortion_percent == pytest.approx(0.0, abs=1e-6)
    assert surface_map.u_max_mm == pytest.approx(4.0)
    assert surface_map.v_max_mm == pytest.approx(4.0)


@pytest.mark.unit
def test_parameterize_surface_skips_invalid_3d_points() -> None:
    points = _flat_grid_points(3, 3)
    points[1, 1] = np.array([np.nan, np.nan, np.nan], dtype=np.float32)
    mask = np.ones((3, 3), dtype=np.bool_)
    plane = PlaneModel(normal=(0.0, 0.0, 1.0), offset=-1.0, rms_mm=0.0)

    surface_map = parameterize_surface(
        points=points,
        garment_mask=mask,
        support_plane=plane,
    )

    assert surface_map.mapped_pixel_count == 8
    assert (1, 1) not in mapping_by_pixel(surface_map)


@pytest.mark.unit
def test_perception_pipeline_result_includes_surface_mapping(tmp_path: Path) -> None:
    result = PerceptionPipeline().run(_write_package(tmp_path))

    assert result.surface_mapping.coordinate_system == "support_plane_uv_mm"
    assert result.surface_mapping.mapped_pixel_count == result.segmentation_area_pixels
    assert result.surface_mapping.points[0].pixel_y <= result.surface_mapping.points[-1].pixel_y
