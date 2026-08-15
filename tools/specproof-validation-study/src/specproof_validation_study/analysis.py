"""Per-POM measurement-system analysis and crossed Gauge R&R."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from math import sqrt

import numpy as np

from specproof_validation_study.models import (
    GaugeRrComponents,
    PomStudyMetrics,
    StudyObservation,
    StudyReport,
    StudyThresholds,
)


def analyse_study(
    observations: Iterable[StudyObservation],
    thresholds: StudyThresholds | None = None,
) -> StudyReport:
    """Compute independent acceptance metrics for every POM."""

    active_thresholds = thresholds or StudyThresholds()
    by_pom: dict[str, list[StudyObservation]] = defaultdict(list)
    for observation in observations:
        by_pom[observation.pom_id].append(observation)
    if not by_pom:
        raise ValueError("At least one validation-study observation is required")
    metrics = tuple(
        _analyse_pom(pom_id, rows, active_thresholds)
        for pom_id, rows in sorted(by_pom.items())
    )
    return StudyReport(thresholds=active_thresholds, poms=metrics)


def _analyse_pom(
    pom_id: str,
    rows: list[StudyObservation],
    thresholds: StudyThresholds,
) -> PomStudyMetrics:
    automated = np.asarray([row.automated_mm for row in rows], dtype=np.float64)
    manual = np.asarray([row.manual_mm for row in rows], dtype=np.float64)
    differences = automated - manual
    repeatability = _same_placement_stddev(rows)
    reproducibility = _operator_reproducibility(rows)
    bias = float(np.mean(differences))
    mae = float(np.mean(np.abs(differences)))
    difference_stddev = float(np.std(differences, ddof=1)) if len(differences) > 1 else 0.0
    false_pass_rate, false_fail_rate = _classification_error_rates(rows)
    gauge_rr = _crossed_gauge_rr(rows)
    pass_flags = (
        repeatability <= thresholds.repeatability_stddev_mm,
        reproducibility <= thresholds.reproducibility_p95_mm,
        mae <= thresholds.manual_mae_mm,
        false_pass_rate <= thresholds.false_pass_rate,
        false_fail_rate <= thresholds.false_fail_rate,
        gauge_rr.gauge_rr_stddev_mm <= thresholds.gauge_rr_stddev_mm,
    )
    return PomStudyMetrics(
        pom_id=pom_id,
        observation_count=len(rows),
        garment_count=len({row.garment_id for row in rows}),
        operator_count=len({row.operator_id for row in rows}),
        placement_count=len({row.placement_id for row in rows}),
        same_placement_stddev_mm=repeatability,
        operator_reproducibility_p95_mm=reproducibility,
        manual_bias_mm=bias,
        manual_mae_mm=mae,
        bland_altman_lower_mm=bias - (1.96 * difference_stddev),
        bland_altman_upper_mm=bias + (1.96 * difference_stddev),
        false_pass_rate=false_pass_rate,
        false_fail_rate=false_fail_rate,
        gauge_rr=gauge_rr,
        repeatability_pass=pass_flags[0],
        reproducibility_pass=pass_flags[1],
        manual_agreement_pass=pass_flags[2],
        false_pass_rate_pass=pass_flags[3],
        false_fail_rate_pass=pass_flags[4],
        gauge_rr_pass=pass_flags[5],
        overall_pass=all(pass_flags),
    )


def _same_placement_stddev(rows: list[StudyObservation]) -> float:
    groups: dict[tuple[str, str, str], list[float]] = defaultdict(list)
    for row in rows:
        groups[(row.garment_id, row.operator_id, row.placement_id)].append(row.automated_mm)
    standard_deviations = [
        float(np.std(values, ddof=1)) if len(values) > 1 else 0.0
        for values in groups.values()
    ]
    return float(np.percentile(standard_deviations, 95))


def _operator_reproducibility(rows: list[StudyObservation]) -> float:
    cell_values: dict[tuple[str, str, str], list[float]] = defaultdict(list)
    for row in rows:
        cell_values[(row.garment_id, row.placement_id, row.operator_id)].append(
            row.automated_mm
        )
    comparisons: dict[tuple[str, str], list[float]] = defaultdict(list)
    for (garment_id, placement_id, _operator_id), values in cell_values.items():
        comparisons[(garment_id, placement_id)].append(float(np.mean(values)))
    ranges = [max(values) - min(values) for values in comparisons.values() if len(values) > 1]
    return float(np.percentile(ranges, 95)) if ranges else 0.0


def _classification_error_rates(rows: list[StudyObservation]) -> tuple[float, float]:
    false_passes = 0
    false_fails = 0
    manual_fails = 0
    manual_passes = 0
    for row in rows:
        lower = row.target_mm - row.lower_tolerance_mm
        upper = row.target_mm + row.upper_tolerance_mm
        manual_pass = lower <= row.manual_mm <= upper
        automated_pass = lower <= row.automated_mm <= upper
        if manual_pass:
            manual_passes += 1
            false_fails += int(not automated_pass)
        else:
            manual_fails += 1
            false_passes += int(automated_pass)
    return (
        false_passes / manual_fails if manual_fails else 0.0,
        false_fails / manual_passes if manual_passes else 0.0,
    )


def _crossed_gauge_rr(rows: list[StudyObservation]) -> GaugeRrComponents:
    parts = sorted({row.garment_id for row in rows})
    operators = sorted({row.operator_id for row in rows})
    cells: dict[tuple[str, str], list[float]] = defaultdict(list)
    for row in rows:
        cells[(row.garment_id, row.operator_id)].append(row.automated_mm)
    if len(parts) < 2 or len(operators) < 2 or not cells:
        return GaugeRrComponents(
            part_variance=0,
            operator_variance=0,
            interaction_variance=0,
            repeatability_variance=0,
            reproducibility_variance=0,
            gauge_rr_variance=0,
            gauge_rr_stddev_mm=0,
        )
    repeats = min(len(values) for values in cells.values())
    if repeats < 2 or len(cells) != len(parts) * len(operators):
        raise ValueError("Crossed Gauge R&R requires a balanced part/operator study")
    balanced = {
        key: np.asarray(values[:repeats], dtype=np.float64) for key, values in cells.items()
    }
    all_values = np.concatenate(tuple(balanced.values()))
    grand_mean = float(np.mean(all_values))
    part_means = {
        part: float(np.mean(np.concatenate([balanced[(part, operator)] for operator in operators])))
        for part in parts
    }
    operator_means = {
        operator: float(np.mean(np.concatenate([balanced[(part, operator)] for part in parts])))
        for operator in operators
    }
    cell_means = {key: float(np.mean(values)) for key, values in balanced.items()}
    part_ss = len(operators) * repeats * sum(
        (mean - grand_mean) ** 2 for mean in part_means.values()
    )
    operator_ss = len(parts) * repeats * sum(
        (mean - grand_mean) ** 2 for mean in operator_means.values()
    )
    interaction_ss = repeats * sum(
        (
            cell_means[(part, operator)]
            - part_means[part]
            - operator_means[operator]
            + grand_mean
        )
        ** 2
        for part in parts
        for operator in operators
    )
    error_ss = sum(
        float(np.sum((values - cell_means[key]) ** 2)) for key, values in balanced.items()
    )
    part_ms = part_ss / (len(parts) - 1)
    operator_ms = operator_ss / (len(operators) - 1)
    interaction_ms = interaction_ss / ((len(parts) - 1) * (len(operators) - 1))
    error_ms = error_ss / (len(parts) * len(operators) * (repeats - 1))
    part_variance = max((part_ms - interaction_ms) / (len(operators) * repeats), 0.0)
    operator_variance = max((operator_ms - interaction_ms) / (len(parts) * repeats), 0.0)
    interaction_variance = max((interaction_ms - error_ms) / repeats, 0.0)
    reproducibility_variance = operator_variance + interaction_variance
    gauge_rr_variance = error_ms + reproducibility_variance
    return GaugeRrComponents(
        part_variance=part_variance,
        operator_variance=operator_variance,
        interaction_variance=interaction_variance,
        repeatability_variance=error_ms,
        reproducibility_variance=reproducibility_variance,
        gauge_rr_variance=gauge_rr_variance,
        gauge_rr_stddev_mm=sqrt(gauge_rr_variance),
    )
