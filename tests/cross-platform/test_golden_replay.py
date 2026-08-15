from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from specproof_measurement_service import PerceptionPipeline

from tests.support.replay_fixture import write_replay_package


@pytest.mark.cross_platform
def test_synthetic_replay_matches_checked_in_golden_with_numeric_tolerance(
    tmp_path: Path,
) -> None:
    repository_root = Path(__file__).resolve().parents[2]
    golden = json.loads(
        (
            repository_root
            / "tests"
            / "fixtures"
            / "cross-platform"
            / "v1"
            / "golden-fingerprints.json"
        ).read_text(encoding="utf-8")
    )

    result = PerceptionPipeline().run(
        write_replay_package(tmp_path, name="front", front=True)
    )

    assert result.category == golden["category"]
    assert result.orientation == golden["orientation"]
    assert result.mesh.vertex_count == golden["meshVertexCount"]
    assert result.mesh.triangle_count == golden["meshTriangleCount"]
    assert result.surface_mapping.mapped_pixel_count == golden["mappedPixelCount"]
    expected_landmarks = {landmark["name"]: landmark for landmark in golden["landmarks"]}
    tolerance = float(golden["coordinateTolerance"])
    assert set(expected_landmarks) == {landmark.name for landmark in result.landmarks}
    for landmark in result.landmarks:
        expected = expected_landmarks[landmark.name]
        assert landmark.x == pytest.approx(expected["x"], abs=tolerance)
        assert landmark.y == pytest.approx(expected["y"], abs=tolerance)
        assert landmark.confidence == pytest.approx(expected["confidence"], abs=tolerance)
        assert landmark.status == expected["status"]
    fingerprint = {
        "category": result.category,
        "orientation": result.orientation,
        "meshVertexCount": result.mesh.vertex_count,
        "meshTriangleCount": result.mesh.triangle_count,
        "mappedPixelCount": result.surface_mapping.mapped_pixel_count,
        "landmarks": [
            {
                "name": landmark.name,
                "x": round(landmark.x, 6),
                "y": round(landmark.y, 6),
                "confidence": round(landmark.confidence, 6),
                "status": landmark.status,
            }
            for landmark in result.landmarks
        ],
    }
    fingerprint_sha256 = hashlib.sha256(
        json.dumps(fingerprint, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    assert fingerprint_sha256 == golden["fingerprintSha256"]
