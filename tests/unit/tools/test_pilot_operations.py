from __future__ import annotations

import json
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[3]


@pytest.mark.unit
def test_pilot_monitoring_configuration_covers_required_operational_signals() -> None:
    alerts = (WORKSPACE / "infra/monitoring/prometheus/alerts.yml").read_text(encoding="utf-8")
    required_alerts = {
        "SpecProofOfflineStations",
        "SpecProofQueueBacklog",
        "SpecProofProcessingLatency",
        "SpecProofInspectionFailures",
        "SpecProofCalibrationExpiry",
        "SpecProofDatabaseUnavailable",
    }

    assert all(f"alert: {name}" in alerts for name in required_alerts)


@pytest.mark.unit
def test_pilot_dashboard_is_versioned_and_contains_required_panels() -> None:
    dashboard = json.loads(
        (WORKSPACE / "infra/monitoring/grafana/dashboards/phase7-pilot.json").read_text(
            encoding="utf-8"
        )
    )
    titles = {panel["title"] for panel in dashboard["panels"]}

    assert dashboard["uid"] == "specproof-phase7-pilot"
    assert {
        "Offline Stations",
        "Durable Queue Depth",
        "Inspection Latency",
        "Failures (15m)",
        "Calibration Expiry",
        "Database Available",
    }.issubset(titles)


@pytest.mark.unit
def test_pilot_documentation_package_contains_required_sections() -> None:
    documents = {
        "OPERATOR-TRAINING.md": "## Practical Assessment",
        "DEPLOYMENT-CHECKLIST.md": "## Rollback",
        "SUPPORT-RUNBOOK.md": "## Database Unavailable",
        "BACKUP-RESTORE.md": "## Restore Drill",
        "INCIDENT-RESPONSE.md": "## Severity Matrix",
    }

    assert all(
        marker in (WORKSPACE / "documentation/pilot" / filename).read_text(encoding="utf-8")
        for filename, marker in documents.items()
    )
