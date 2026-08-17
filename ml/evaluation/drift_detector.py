"""Drift detection for SpecProof ML model evaluation metrics.

Compares current evaluation metrics against a baseline snapshot and flags
regressions above a configurable threshold.  Outputs a structured drift
report as JSON.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


class DriftEntry(BaseModel):
    """One metric drift entry."""

    metric_name: str
    baseline_value: float
    current_value: float
    delta: float
    delta_percent: float
    threshold_percent: float
    drifted: bool
    direction: str = Field(description="'regression' or 'improvement' or 'stable'")


class DriftReport(BaseModel):
    """Structured drift detection report."""

    model_name: str
    model_type: str
    baseline_run_id: str
    current_run_id: str
    detected_at_utc: datetime = Field(default_factory=lambda: datetime.now(UTC))
    entries: list[DriftEntry]
    any_drift_detected: bool
    drift_count: int
    summary: str
    schema_version: int = 1

    def to_canonical_json(self) -> str:
        """Return canonical UTF-8 JSON with sorted keys."""
        return json.dumps(
            self.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )


# ---------------------------------------------------------------------------
# Drift detector
# ---------------------------------------------------------------------------


class DriftDetector:
    """Detects metric regressions between evaluation runs.

    Parameters
    ----------
    baseline_path:
        Path to the baseline evaluation report JSON.
    threshold_percent:
        Percentage degradation that triggers a drift alert
        (default 5.0 → any metric drop > 5% flags drift).
    """

    def __init__(
        self,
        baseline_path: Path,
        *,
        threshold_percent: float = 5.0,
    ) -> None:
        self.baseline_path = Path(baseline_path)
        self.threshold_percent = threshold_percent
        self._baseline: dict[str, Any] = json.loads(
            self.baseline_path.read_text(encoding="utf-8")
        )

    def compare(
        self,
        current_report_path: Path,
        *,
        baseline_run_id: str = "baseline",
        current_run_id: str = "current",
    ) -> DriftReport:
        """Compare a current evaluation report against the baseline.

        Parameters
        ----------
        current_report_path:
            Path to the current evaluation report JSON.
        baseline_run_id:
            Identifier for the baseline run.
        current_run_id:
            Identifier for the current run.

        Returns
        -------
        DriftReport
        """
        current: dict[str, Any] = json.loads(
            current_report_path.read_text(encoding="utf-8")
        )

        baseline_metrics = _extract_metrics(self._baseline)
        current_metrics = _extract_metrics(current)

        entries: list[DriftEntry] = []
        for metric_name, baseline_val in baseline_metrics.items():
            if metric_name not in current_metrics:
                continue
            current_val = current_metrics[metric_name]
            delta = current_val - baseline_val
            delta_percent = (delta / abs(baseline_val) * 100.0) if abs(baseline_val) > 1e-9 else 0.0
            # Drift = regression (metric got worse)
            drifted = delta_percent < -self.threshold_percent
            if drifted:
                direction = "regression"
            elif delta_percent > self.threshold_percent:
                direction = "improvement"
            else:
                direction = "stable"

            entries.append(
                DriftEntry(
                    metric_name=metric_name,
                    baseline_value=baseline_val,
                    current_value=current_val,
                    delta=delta,
                    delta_percent=delta_percent,
                    threshold_percent=self.threshold_percent,
                    drifted=drifted,
                    direction=direction,
                )
            )

        drift_count = sum(1 for e in entries if e.drifted)
        any_drift = drift_count > 0
        if any_drift:
            drifted_names = [e.metric_name for e in entries if e.drifted]
            summary = (
                f"DRIFT DETECTED: {drift_count} metric(s) regressed beyond "
                f"{self.threshold_percent}% threshold: {', '.join(drifted_names)}"
            )
        else:
            summary = (
                f"No drift detected.  All {len(entries)} metric(s) within "
                f"{self.threshold_percent}% threshold."
            )

        return DriftReport(
            model_name=current.get("model_name", "unknown"),
            model_type=current.get("model_type", "unknown"),
            baseline_run_id=baseline_run_id,
            current_run_id=current_run_id,
            entries=entries,
            any_drift_detected=any_drift,
            drift_count=drift_count,
            summary=summary,
        )

    def save_as_baseline(self, evaluation_report_path: Path) -> None:
        """Promote a current evaluation report to become the new baseline.

        Overwrites ``self.baseline_path`` with the contents of the given report.

        Parameters
        ----------
        evaluation_report_path:
            Path to the evaluation report to promote.
        """
        content = evaluation_report_path.read_bytes()
        self.baseline_path.write_bytes(content)
        self._baseline = json.loads(content.decode("utf-8"))


# ---------------------------------------------------------------------------
# Baseline snapshot helpers
# ---------------------------------------------------------------------------


def create_baseline_snapshot(
    evaluation_report_path: Path,
    baseline_path: Path,
) -> None:
    """Copy an evaluation report to a baseline file.

    Parameters
    ----------
    evaluation_report_path:
        Source evaluation report.
    baseline_path:
        Destination baseline path.
    """
    baseline_path.parent.mkdir(parents=True, exist_ok=True)
    baseline_path.write_bytes(evaluation_report_path.read_bytes())


def write_drift_report(report: DriftReport, output_path: Path) -> None:
    """Write a drift report to disk.

    Parameters
    ----------
    report:
        Drift report to write.
    output_path:
        Destination path.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report.to_canonical_json() + "\n", encoding="utf-8", newline="\n")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _extract_metrics(report: dict[str, Any]) -> dict[str, float]:
    """Extract scalar metrics from an evaluation report dict."""
    metrics: dict[str, float] = {}

    # Overall metric
    if "overall_metric" in report:
        metrics["overall_metric"] = float(report["overall_metric"])

    # Segmentation metrics
    seg = report.get("segmentation")
    if isinstance(seg, dict):
        if "mean_iou" in seg:
            metrics["segmentation_mean_iou"] = float(seg["mean_iou"])
        if "iou_above_85" in seg:
            metrics["segmentation_iou_above_85"] = float(seg["iou_above_85"])

    # Landmark metrics
    landmarks = report.get("landmarks")
    if isinstance(landmarks, list):
        for lm in landmarks:
            if isinstance(lm, dict) and "landmark_name" in lm and "recall_at_5px" in lm:
                key = f"landmark_recall_{lm['landmark_name']}"
                metrics[key] = float(lm["recall_at_5px"])

    return metrics
