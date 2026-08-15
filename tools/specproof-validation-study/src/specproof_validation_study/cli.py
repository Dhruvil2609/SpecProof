"""Command-line entry point for validation-study analysis."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from specproof_validation_study.analysis import analyse_study
from specproof_validation_study.io import read_observations_csv, write_report_bundle
from specproof_validation_study.models import study_input_schema


def build_parser() -> argparse.ArgumentParser:
    """Build the validation-study CLI parser."""

    parser = argparse.ArgumentParser(prog="specproof-validation-study")
    subparsers = parser.add_subparsers(dest="command", required=True)
    analyse = subparsers.add_parser("analyse", help="Analyse controlled CSV observations")
    analyse.add_argument("--input", type=Path, required=True)
    analyse.add_argument("--output-directory", type=Path, required=True)
    schema = subparsers.add_parser("schema", help="Write the versioned input JSON Schema")
    schema.add_argument("--output", type=Path, required=True)
    return parser


def main(arguments: Sequence[str] | None = None) -> int:
    """Execute one validation-study command."""

    parsed = build_parser().parse_args(arguments)
    if parsed.command == "schema":
        parsed.output.parent.mkdir(parents=True, exist_ok=True)
        parsed.output.write_text(
            json.dumps(study_input_schema(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        return 0
    observations = read_observations_csv(parsed.input)
    report = analyse_study(observations)
    write_report_bundle(observations, report, parsed.output_directory)
    return 0 if all(metric.overall_pass for metric in report.poms) else 2


if __name__ == "__main__":
    raise SystemExit(main())
