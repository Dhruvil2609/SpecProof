"""Measurement result models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MeasurementResult:
    """Result of a single point-of-measure measurement."""

    pom_id: str
    measured_value_mm: float
    confidence: float
