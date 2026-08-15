from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import numpy as np
from specproof_capture_service import CapturePackageWriter, StreamProfile
from specproof_capture_service.models import CameraExtrinsics, CameraFrame, CameraIntrinsics
from specproof_measurement_service.pipeline import utc_now


def synthetic_tshirt_mask(*, front: bool = True) -> np.ndarray:
    mask = np.zeros((32, 40), dtype=np.bool_)
    mask[8:28, 13:27] = True
    mask[10:17, 6:13] = True
    mask[10:17, 27:34] = True
    if front:
        mask[8:12, 18:22] = False
    return mask


def capture_frame(index: int, mask: np.ndarray, *, serial: str) -> CameraFrame:
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
        camera_serial=serial,
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


def write_replay_package(tmp_path: Path, *, name: str, front: bool = True) -> Path:
    mask = synthetic_tshirt_mask(front=front)
    serial = f"MOCK-REPLAY-{name.upper()}"
    package_path = tmp_path / f"{name}.spcapture"
    CapturePackageWriter().write(
        output_path=package_path,
        station_id=f"station-{name}",
        calibration_id=f"calibration-{name}",
        profile=StreamProfile(
            color_width=40,
            color_height=32,
            depth_width=40,
            depth_height=32,
            frames_per_second=30,
        ),
        frames=[capture_frame(index, mask, serial=serial) for index in range(3)],
        environment={"fixture": name},
    )
    return package_path
