"""Controlled CSV input and analytical report output."""

from __future__ import annotations

import csv
import json
from html import escape
from pathlib import Path
from typing import Any, cast

from specproof_validation_study.models import StudyObservation, StudyReport


def read_observations_csv(path: Path) -> tuple[StudyObservation, ...]:
    """Read and validate normalized controlled CSV input."""

    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = tuple(csv.DictReader(handle))
    return tuple(StudyObservation.model_validate(row) for row in rows)


def write_report_bundle(
    observations: tuple[StudyObservation, ...],
    report: StudyReport,
    output_directory: Path,
) -> None:
    """Write normalized Parquet plus JSON and HTML analytical reports."""

    output_directory.mkdir(parents=True, exist_ok=True)
    _write_parquet(observations, output_directory / "observations.parquet")
    (output_directory / "report.json").write_text(
        report.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    (output_directory / "report.html").write_text(
        _render_html(report),
        encoding="utf-8",
        newline="\n",
    )


def _write_parquet(observations: tuple[StudyObservation, ...], path: Path) -> None:
    try:
        import pyarrow as pa
        import pyarrow.parquet as parquet
    except ImportError as error:
        raise RuntimeError("pyarrow is required to write validation-study Parquet") from error
    table = cast(
        Any,
        pa.Table.from_pylist(
            [observation.model_dump(mode="json") for observation in observations]
        ),
    )
    parquet.write_table(
        table,
        path,
        compression="zstd",
        version="2.6",
    )


def _render_html(report: StudyReport) -> str:
    rows = "".join(
        "<tr>"
        f"<td>{escape(metric.pom_id)}</td>"
        f"<td>{metric.same_placement_stddev_mm:.3f}</td>"
        f"<td>{metric.operator_reproducibility_p95_mm:.3f}</td>"
        f"<td>{metric.manual_bias_mm:.3f}</td>"
        f"<td>{metric.manual_mae_mm:.3f}</td>"
        f"<td>{metric.bland_altman_lower_mm:.3f} to {metric.bland_altman_upper_mm:.3f}</td>"
        f"<td>{metric.false_pass_rate:.3%}</td>"
        f"<td>{metric.false_fail_rate:.3%}</td>"
        f"<td>{metric.gauge_rr.gauge_rr_stddev_mm:.3f}</td>"
        f"<td>{'PASS' if metric.overall_pass else 'FAIL'}</td>"
        "</tr>"
        for metric in report.poms
    )
    report_json = escape(json.dumps(report.model_dump(mode="json"), sort_keys=True))
    return (
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        "<title>SpecProof Validation Study</title>"
        "<style>body{font-family:system-ui;margin:2rem;background:#101820;color:#f5f3ed}"
        "table{border-collapse:collapse;width:100%}th,td{padding:.6rem;border:1px solid #65727c}"
        "th{text-align:left;background:#1e303c}</style></head><body>"
        "<h1>SpecProof Gauge R&amp;R Validation Study</h1>"
        "<p>Results are reported per POM; weak POMs are never averaged away.</p>"
        "<table><thead><tr><th>POM</th><th>Repeatability SD</th><th>Operator P95</th>"
        "<th>Bias</th><th>MAE</th><th>Bland–Altman LoA</th><th>False pass</th>"
        "<th>False fail</th><th>Gauge R&amp;R SD</th><th>Outcome</th></tr></thead>"
        f"<tbody>{rows}</tbody></table><details><summary>Machine-readable report</summary>"
        f"<pre>{report_json}</pre></details></body></html>\n"
    )
