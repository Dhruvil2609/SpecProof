from __future__ import annotations

import json
from pathlib import Path

import pytest
from specproof_validation_study import analyse_study
from specproof_validation_study.cli import main
from specproof_validation_study.io import read_observations_csv

FIXTURE_ROOT = Path("tests/fixtures/validation-study/v1")


@pytest.mark.unit
def test_passing_fixture_meets_every_per_pom_threshold() -> None:
    observations = read_observations_csv(FIXTURE_ROOT / "passing.csv")

    report = analyse_study(observations)

    metric = report.poms[0]
    assert metric.pom_id == "chest_width"
    assert metric.same_placement_stddev_mm < 2
    assert metric.operator_reproducibility_p95_mm < 4
    assert metric.manual_mae_mm < 5
    assert metric.false_pass_rate == 0
    assert metric.false_fail_rate == 0
    assert metric.overall_pass is True


@pytest.mark.unit
def test_failing_fixture_exposes_weak_pom_without_aggregation() -> None:
    passing = read_observations_csv(FIXTURE_ROOT / "passing.csv")
    failing = tuple(
        row.model_copy(update={"pom_id": "body_length"})
        for row in read_observations_csv(FIXTURE_ROOT / "failing.csv")
    )

    report = analyse_study((*passing, *failing))

    assert [metric.pom_id for metric in report.poms] == ["body_length", "chest_width"]
    assert report.poms[0].overall_pass is False
    assert report.poms[0].false_fail_rate > 0
    assert report.poms[1].overall_pass is True


@pytest.mark.unit
def test_cli_writes_schema_and_returns_failure_for_failing_study(tmp_path: Path) -> None:
    schema_path = tmp_path / "study-observation-v1.schema.json"

    assert main(["schema", "--output", str(schema_path)]) == 0
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    assert schema["properties"]["schema_version"]["default"] == 1

    output_directory = tmp_path / "failing-report"
    exit_code = main(
        [
            "analyse",
            "--input",
            str(FIXTURE_ROOT / "failing.csv"),
            "--output-directory",
            str(output_directory),
        ]
    )
    assert exit_code == 2
    assert (output_directory / "observations.parquet").read_bytes()[:4] == b"PAR1"
    assert "chest_width" in (output_directory / "report.html").read_text(encoding="utf-8")
    assert json.loads((output_directory / "report.json").read_text(encoding="utf-8"))["poms"]
