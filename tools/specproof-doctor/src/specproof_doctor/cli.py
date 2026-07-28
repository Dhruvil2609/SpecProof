"""Command-line interface for SpecProof environment diagnostics."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from specproof_doctor.checks import (
    CheckResult,
    CheckStatus,
    DoctorConfig,
    has_required_failures,
    run_checks,
    utc_now_iso,
)


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""

    parser = argparse.ArgumentParser(
        prog="specproof-doctor",
        description="Validate the SpecProof Phase 0 development environment.",
    )
    parser.add_argument(
        "--require-gpu", action="store_true", help="Fail when NVIDIA tooling is absent."
    )
    parser.add_argument(
        "--require-realsense",
        action="store_true",
        help="Fail when pyrealsense2 is absent.",
    )
    parser.add_argument(
        "--require-camera-stream",
        action="store_true",
        help="Fail when no RealSense camera can be enumerated.",
    )
    return parser


def format_results(results: Sequence[CheckResult], timestamp_utc: str) -> str:
    """Format check results for deterministic console output."""

    lines = [
        "SpecProof Doctor",
        f"Timestamp UTC: {timestamp_utc}",
        "",
        "STATUS  REQUIRED  CHECK                    DETAIL",
        "------  --------  -----------------------  ----------------------------------------",
    ]
    for result in results:
        required = "yes" if result.required else "no"
        lines.append(f"{result.status.value:<6}  {required:<8}  {result.name:<23}  {result.detail}")

    failed_required = sum(
        1 for result in results if result.required and result.status == CheckStatus.FAIL
    )
    skipped = sum(1 for result in results if result.status == CheckStatus.SKIP)
    passed = sum(1 for result in results if result.status == CheckStatus.PASS)
    lines.extend(
        [
            "",
            f"Summary: {passed} passed, {failed_required} required failed, {skipped} skipped",
        ]
    )
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    """Run diagnostics and return a process exit code."""

    args = build_parser().parse_args(argv)
    config = DoctorConfig(
        require_gpu=args.require_gpu,
        require_realsense=args.require_realsense,
        require_camera_stream=args.require_camera_stream,
    )
    results = run_checks(config)
    print(format_results(results, utc_now_iso()))
    return 1 if has_required_failures(results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
