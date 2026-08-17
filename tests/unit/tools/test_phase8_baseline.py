from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[3]


@pytest.mark.unit
def test_progress_tracker_matches_authoritative_phase_task_scope() -> None:
    phase = (WORKSPACE / "docs/phases/PHASE-8_production-hardening.md").read_text(
        encoding="utf-8"
    )
    progress = (WORKSPACE / "docs/tracking/PROGRESS.md").read_text(encoding="utf-8")

    assert len(re.findall(r"^- \[[ x]\] \*\*TASK-8\.", phase, flags=re.MULTILINE)) == 50
    assert (
        "|         8 | Production Hardening          | `IN_PROGRESS`  | `BLOCKED`"
        "     |      50 |      17 |      34% |"
    ) in progress
    assert (
        "| **Total** |                               |                |"
        "               | **418** | **343** |  **82%** |"
    ) in progress


@pytest.mark.unit
def test_quality_gate_schema_declares_each_production_gate_once() -> None:
    schema = json.loads(
        (WORKSPACE / "schemas/release/quality-gate-evidence.schema.json").read_text(
            encoding="utf-8"
        )
    )
    gate_ids = schema["$defs"]["gateEvidence"]["properties"]["gateId"]["enum"]

    assert gate_ids == [f"QG-{index:02d}" for index in range(1, 16)]
    assert schema["properties"]["gates"]["minItems"] == 15
    assert schema["properties"]["gates"]["maxItems"] == 15


@pytest.mark.unit
def test_threat_model_covers_release_station_and_tenant_boundaries() -> None:
    threat_model = (WORKSPACE / "docs/security/THREAT-MODEL.md").read_text(encoding="utf-8")

    assert all(
        marker in threat_model
        for marker in (
            "## Trust Boundaries",
            "## Threat Register",
            "Cross-tenant data access",
            "Compromised installer or update",
            "## Deferred and External Risks",
        )
    )
