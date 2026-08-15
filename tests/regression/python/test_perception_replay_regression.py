from __future__ import annotations

import time
from pathlib import Path

import pytest
from specproof_measurement_service import PerceptionPipeline

from tests.support.replay_fixture import write_replay_package


@pytest.mark.regression
def test_perception_replay_regression_canonical_json_is_stable(tmp_path: Path) -> None:
    package_path = write_replay_package(tmp_path, name="front", front=True)
    pipeline = PerceptionPipeline()

    first = pipeline.run(package_path)
    second = pipeline.run(package_path)

    assert first.to_regression_json() == second.to_regression_json()
    assert first.regression_sha256() == second.regression_sha256()


@pytest.mark.regression
def test_perception_replay_regression_landmarks_are_consistent(tmp_path: Path) -> None:
    package_path = write_replay_package(tmp_path, name="front", front=True)
    pipeline = PerceptionPipeline()

    first = pipeline.run(package_path)
    second = pipeline.run(package_path)
    first_landmarks = [
        (landmark.name, landmark.x, landmark.y, landmark.status) for landmark in first.landmarks
    ]
    second_landmarks = [
        (landmark.name, landmark.x, landmark.y, landmark.status) for landmark in second.landmarks
    ]

    assert first_landmarks == second_landmarks
    assert len(first_landmarks) == 10


@pytest.mark.regression
def test_perception_replay_regression_mesh_indices_are_valid(tmp_path: Path) -> None:
    result = PerceptionPipeline().run(write_replay_package(tmp_path, name="front", front=True))

    assert result.mesh.vertex_count == result.surface_mapping.mapped_pixel_count
    assert result.mesh.triangle_count > 0
    assert all(
        0 <= vertex_index < result.mesh.vertex_count
        for triangle in result.mesh.triangle_indices
        for vertex_index in triangle
    )


@pytest.mark.performance
def test_perception_replay_pipeline_runtime_stays_under_15_seconds(tmp_path: Path) -> None:
    packages = (
        write_replay_package(tmp_path, name="front", front=True),
        write_replay_package(tmp_path, name="back", front=False),
    )
    pipeline = PerceptionPipeline()

    started = time.perf_counter()
    results = [pipeline.run(package_path) for package_path in packages]
    elapsed_seconds = time.perf_counter() - started

    assert elapsed_seconds < 15.0
    assert all(result.schema_version == 1 for result in results)
