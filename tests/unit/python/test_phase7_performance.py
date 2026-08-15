from __future__ import annotations

import pytest
from specproof_measurement_service.performance import benchmark_operation, select_onnx_providers

from tools.performance.profile_platform_queries import (
    PROFILE_QUERIES,
    psycopg_connection_string,
)


@pytest.mark.unit
def test_benchmark_summary_reports_acceptance_percentiles_and_resources() -> None:
    calls: list[int] = []

    summary = benchmark_operation(
        lambda: calls.append(len(calls)),
        warmup_iterations=2,
        measured_iterations=5,
    )

    assert len(calls) == 7
    assert summary.p50_ms >= 0
    assert summary.p95_ms <= summary.maximum_ms
    assert summary.cpu_ms >= 0
    assert summary.peak_memory_bytes >= 0
    assert summary.software_gate_pass is True
    assert summary.pilot_target_pass is True


@pytest.mark.unit
def test_onnx_provider_selection_has_cpu_fallback_and_explicit_cuda_gate() -> None:
    qualification = select_onnx_providers()

    assert "CPUExecutionProvider" in qualification.selected_providers
    assert qualification.cuda_acceptance in {"available", "pending"}
    if not qualification.cuda_available:
        assert qualification.cuda_acceptance == "pending"


@pytest.mark.unit
def test_platform_profiler_covers_phase7_query_shapes() -> None:
    assert set(PROFILE_QUERIES) == {
        "dashboard",
        "inspection_history",
        "station_health",
        "queue_claim",
        "batch_summary",
        "dashboard_evidence",
    }
    assert all("EXPLAIN" not in query.upper() for query in PROFILE_QUERIES.values())


@pytest.mark.unit
def test_platform_profiler_converts_repository_database_connection_string() -> None:
    result = psycopg_connection_string(
        "Host=localhost;Port=55432;Database=specproof_test;"
        "Username=Admin;Password=Admin@123"
    )

    assert result == (
        "host='localhost' port='55432' dbname='specproof_test' "
        "user='Admin' password='Admin@123'"
    )
