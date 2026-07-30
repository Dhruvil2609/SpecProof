from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from specproof_capture_service import (
    CalibrationScene,
    CapturePackageWriter,
    CaptureReplayProvider,
    CaptureZone,
    MockCameraProvider,
    StreamProfile,
    calibration_is_acceptable,
    evaluate_synthetic_calibration,
    validate_capture_zone_framing,
    validate_replay_corpus,
    validate_replay_package,
)
from specproof_capture_service.capture_package import sha256_file
from specproof_capture_service.models import CalibrationThresholds, CameraFrame


@pytest.fixture
def profile() -> StreamProfile:
    return StreamProfile(
        color_width=16,
        color_height=12,
        depth_width=16,
        depth_height=12,
        frames_per_second=30,
    )


@pytest.fixture
async def frames(profile: StreamProfile) -> tuple[CameraFrame, ...]:
    captured = await MockCameraProvider().capture_frames("MOCK-001", profile, 5)
    return tuple(captured)


@pytest.mark.unit
async def test_synthetic_calibration_evaluator_flat_scene_passes_thresholds(
    frames: tuple[CameraFrame, ...],
) -> None:
    frame = frames[2]
    plane_mask = np.zeros(frame.depth_units.shape, dtype=np.bool_)
    plane_mask[2:10, 3:13] = True
    lighting_mask = np.ones(frame.depth_units.shape, dtype=np.bool_)
    scene = CalibrationScene(
        frames=frames,
        expected_depth_units=1000,
        artefact_expected_width_px=100.0,
        artefact_observed_width_px=100.05,
        plane_mask=plane_mask,
        lighting_mask=lighting_mask,
    )

    metrics = evaluate_synthetic_calibration(scene)

    assert calibration_is_acceptable(metrics, CalibrationThresholds()) is True


@pytest.mark.unit
async def test_synthetic_calibration_evaluator_rejects_scale_error(
    frames: tuple[CameraFrame, ...],
) -> None:
    frame = frames[2]
    scene = CalibrationScene(
        frames=frames,
        expected_depth_units=1000,
        artefact_expected_width_px=100.0,
        artefact_observed_width_px=101.0,
        plane_mask=np.ones(frame.depth_units.shape, dtype=np.bool_),
        lighting_mask=np.ones(frame.depth_units.shape, dtype=np.bool_),
    )

    metrics = evaluate_synthetic_calibration(scene)

    assert calibration_is_acceptable(metrics, CalibrationThresholds()) is False


@pytest.mark.unit
async def test_capture_zone_framing_accepts_centered_foreground(
    frames: tuple[CameraFrame, ...],
) -> None:
    foreground = np.zeros(frames[0].depth_units.shape, dtype=np.bool_)
    foreground[4:8, 5:11] = True

    result = validate_capture_zone_framing(
        frames[0],
        zone=CaptureZone(left=2, top=2, width=12, height=8),
        foreground_mask=foreground,
    )

    assert result.valid is True and result.reason == "ok"


@pytest.mark.unit
async def test_capture_zone_framing_rejects_foreground_outside_zone(
    frames: tuple[CameraFrame, ...],
) -> None:
    foreground = np.zeros(frames[0].depth_units.shape, dtype=np.bool_)
    foreground[0:3, 0:3] = True

    result = validate_capture_zone_framing(
        frames[0],
        zone=CaptureZone(left=2, top=2, width=12, height=8),
        foreground_mask=foreground,
    )

    assert result.valid is False and result.reason == "foreground_outside_zone"


@pytest.mark.unit
async def test_replay_validation_accepts_valid_package(
    tmp_path: Path,
    profile: StreamProfile,
    frames: tuple[CameraFrame, ...],
) -> None:
    package_path = tmp_path / "valid.spcapture"
    CapturePackageWriter().write(
        output_path=package_path,
        station_id="station-001",
        calibration_id="calibration-001",
        profile=profile,
        frames=frames[:3],
    )

    result = validate_replay_package(package_path)
    corpus = validate_replay_corpus(tmp_path)

    assert result.valid is True and result.package_sha256 == sha256_file(package_path)
    assert len(corpus) == 1 and corpus[0].valid is True


@pytest.mark.unit
def test_replay_validation_rejects_corrupt_package(tmp_path: Path) -> None:
    package_path = tmp_path / "corrupt.spcapture"
    package_path.write_bytes(b"not-a-zip")

    result = validate_replay_package(package_path)

    assert result.valid is False and result.capture_id is None


@pytest.mark.integration
async def test_full_capture_workflow_package_can_be_replayed(
    tmp_path: Path,
    profile: StreamProfile,
    frames: tuple[CameraFrame, ...],
) -> None:
    package_path = tmp_path / "workflow.spcapture"
    manifest, digest = CapturePackageWriter().write(
        output_path=package_path,
        station_id="station-001",
        calibration_id="calibration-001",
        profile=profile,
        frames=frames[:3],
        environment={"provider": "MockCameraProvider"},
    )
    replay = CaptureReplayProvider(package_path)

    replayed = await replay.capture_frames("MOCK-001", profile, 3)

    assert manifest.frame_count == 3 and len(digest) == 64
    assert np.array_equal(replayed[2].depth_units, frames[2].depth_units)
