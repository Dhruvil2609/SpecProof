"""Repeatable Phase 7 pipeline benchmarks and ONNX provider qualification."""

from __future__ import annotations

import argparse
import json
import statistics
import time
import tracemalloc
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import TypeVar, cast

import onnxruntime as ort
from pydantic import BaseModel

from specproof_measurement_service.inspection import InspectionPipeline, InspectionPipelineRequest


class BenchmarkSummary(BaseModel):
    """Stable benchmark output for software and pilot gates."""

    warmup_iterations: int
    measured_iterations: int
    p50_ms: float
    p95_ms: float
    maximum_ms: float
    cpu_ms: float
    peak_memory_bytes: int
    software_gate_pass: bool
    pilot_target_pass: bool


class OnnxProviderQualification(BaseModel):
    """Available ONNX Runtime providers and CUDA acceptance state."""

    selected_providers: tuple[str, ...]
    cuda_available: bool
    cuda_acceptance: str
    detail: str


ResultType = TypeVar("ResultType")


def benchmark_operation(
    operation: Callable[[], ResultType],
    *,
    warmup_iterations: int = 1,
    measured_iterations: int = 5,
) -> BenchmarkSummary:
    """Measure warm runtime latency, process CPU, and Python peak allocations."""

    if warmup_iterations < 0 or measured_iterations < 1:
        raise ValueError("Benchmark iteration counts are invalid")
    for _ in range(warmup_iterations):
        operation()
    tracemalloc.start()
    cpu_started = time.process_time_ns()
    durations: list[float] = []
    for _ in range(measured_iterations):
        started = time.perf_counter_ns()
        operation()
        durations.append((time.perf_counter_ns() - started) / 1_000_000)
    cpu_ms = (time.process_time_ns() - cpu_started) / 1_000_000
    _, peak_memory = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    p95 = _percentile(durations, 95)
    return BenchmarkSummary(
        warmup_iterations=warmup_iterations,
        measured_iterations=measured_iterations,
        p50_ms=statistics.median(durations),
        p95_ms=p95,
        maximum_ms=max(durations),
        cpu_ms=cpu_ms,
        peak_memory_bytes=peak_memory,
        software_gate_pass=p95 < 15_000,
        pilot_target_pass=p95 < 5_000,
    )


def select_onnx_providers(*, prefer_cuda: bool = True) -> OnnxProviderQualification:
    """Select CUDA when available and leave hardware acceptance explicitly pending otherwise."""

    provider_names = cast(Sequence[str], ort.get_available_providers())
    available = tuple(provider_names)
    cuda_available = "CUDAExecutionProvider" in available
    selected = (
        ("CUDAExecutionProvider", "CPUExecutionProvider")
        if prefer_cuda and cuda_available
        else ("CPUExecutionProvider",)
    )
    return OnnxProviderQualification(
        selected_providers=selected,
        cuda_available=cuda_available,
        cuda_acceptance="available" if cuda_available else "pending",
        detail=(
            "CUDAExecutionProvider is available for smoke qualification."
            if cuda_available
            else (
                "Qualified GPU is unavailable; CPU provider selected and GPU acceptance "
                "remains pending."
            )
        ),
    )


def cuda_smoke_test(model_path: Path) -> OnnxProviderQualification:
    """Construct an ONNX session with selected providers as a provider smoke test."""

    qualification = select_onnx_providers()
    ort.InferenceSession(str(model_path), providers=list(qualification.selected_providers))
    return qualification


def _percentile(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    rank = (len(ordered) - 1) * (percentile / 100)
    lower = int(rank)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = rank - lower
    return ordered[lower] + ((ordered[upper] - ordered[lower]) * fraction)


def main(arguments: Sequence[str] | None = None) -> int:
    """Benchmark an integrated inspection request JSON file."""

    parser = argparse.ArgumentParser(prog="specproof-integration-benchmark")
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--warmups", type=int, default=1)
    parser.add_argument("--iterations", type=int, default=5)
    parsed = parser.parse_args(arguments)
    request = InspectionPipelineRequest.model_validate_json(
        parsed.request.read_text(encoding="utf-8")
    )
    pipeline = InspectionPipeline()
    summary = benchmark_operation(
        lambda: pipeline.run(request),
        warmup_iterations=parsed.warmups,
        measured_iterations=parsed.iterations,
    )
    payload = {
        "benchmark": summary.model_dump(mode="json"),
        "onnx": select_onnx_providers().model_dump(mode="json"),
    }
    parsed.output.parent.mkdir(parents=True, exist_ok=True)
    parsed.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return 0 if summary.software_gate_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())
