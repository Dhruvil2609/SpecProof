from __future__ import annotations

from specproof_doctor.checks import CheckResult, CheckStatus, has_required_failures, utc_now_iso
from specproof_doctor.cli import format_results


def test_format_results_outputs_rows_and_summary() -> None:
    results = [
        CheckResult("Git", CheckStatus.PASS, "git version 2.53.0"),
        CheckResult("NVIDIA GPU", CheckStatus.SKIP, "optional", required=False),
        CheckResult("Docker daemon", CheckStatus.FAIL, "not running"),
    ]

    output = format_results(results, "2026-07-25T13:15:00Z")

    assert "PASS    yes       Git" in output
    assert "SKIP    no        NVIDIA GPU" in output
    assert "FAIL    yes       Docker daemon" in output
    assert "Summary: 1 passed, 1 required failed, 1 skipped" in output


def test_has_required_failures_ignores_optional_skips() -> None:
    results = [
        CheckResult("Git", CheckStatus.PASS, "ok"),
        CheckResult("NVIDIA GPU", CheckStatus.SKIP, "optional", required=False),
    ]

    assert has_required_failures(results) is False


def test_utc_now_iso_uses_z_suffix() -> None:
    result = utc_now_iso()

    assert result.endswith("Z")
    assert "+00:00" not in result
