"""MLflow experiment tracking abstraction for SpecProof ML pipelines.

Provides a thin wrapper around MLflow that:
- Logs parameters, metrics, and artefacts with UTC timestamps.
- Falls back to a ``NoOpTracker`` for offline / CI testing.
- Never exposes MLflow internals to training code.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Abstract interface
# ---------------------------------------------------------------------------


class ExperimentTracker(ABC):
    """Abstract experiment tracker interface."""

    @abstractmethod
    def start_run(self, run_name: str, tags: dict[str, str] | None = None) -> str:
        """Start a new experiment run and return its run ID."""

    @abstractmethod
    def end_run(self) -> None:
        """End the current run."""

    @abstractmethod
    def log_param(self, key: str, value: Any) -> None:
        """Log a scalar parameter."""

    @abstractmethod
    def log_params(self, params: dict[str, Any]) -> None:
        """Log multiple parameters at once."""

    @abstractmethod
    def log_metric(self, key: str, value: float, step: int | None = None) -> None:
        """Log a scalar metric, optionally at a given step."""

    @abstractmethod
    def log_metrics(
        self, metrics: dict[str, float], step: int | None = None
    ) -> None:
        """Log multiple metrics at once."""

    @abstractmethod
    def log_artifact(self, local_path: Path, artifact_path: str | None = None) -> None:
        """Log a file artefact."""

    @abstractmethod
    def set_tag(self, key: str, value: str) -> None:
        """Set a run tag."""

    @property
    @abstractmethod
    def run_id(self) -> str | None:
        """Return the active run ID, or None if no run is active."""


# ---------------------------------------------------------------------------
# No-Op tracker (offline / CI)
# ---------------------------------------------------------------------------


class _RunRecord:
    """In-memory record of one run for the NoOpTracker."""

    def __init__(self, run_id: str, run_name: str, tags: dict[str, str]) -> None:
        self.run_id = run_id
        self.run_name = run_name
        self.tags: dict[str, str] = dict(tags)
        self.params: dict[str, Any] = {}
        self.metrics: dict[str, list[tuple[float, int | None]]] = {}
        self.artifacts: list[Path] = []
        self.started_at_utc = datetime.now(UTC)
        self.ended_at_utc: datetime | None = None


class NoOpTracker(ExperimentTracker):
    """In-memory experiment tracker for offline testing.

    All data is stored in memory.  No MLflow server is required.
    """

    def __init__(self) -> None:
        self._runs: dict[str, _RunRecord] = {}
        self._active_run_id: str | None = None
        self._run_counter = 0

    # ------------------------------------------------------------------
    # Interface implementation
    # ------------------------------------------------------------------

    def start_run(self, run_name: str, tags: dict[str, str] | None = None) -> str:
        """Start an in-memory run and return its ID."""
        self._run_counter += 1
        run_id = f"noop-run-{self._run_counter:04d}"
        self._runs[run_id] = _RunRecord(run_id, run_name, tags or {})
        self._active_run_id = run_id
        return run_id

    def end_run(self) -> None:
        """End the current run."""
        if self._active_run_id and self._active_run_id in self._runs:
            self._runs[self._active_run_id].ended_at_utc = datetime.now(UTC)
        self._active_run_id = None

    def log_param(self, key: str, value: Any) -> None:
        self._active_record().params[key] = value

    def log_params(self, params: dict[str, Any]) -> None:
        self._active_record().params.update(params)

    def log_metric(self, key: str, value: float, step: int | None = None) -> None:
        record = self._active_record()
        record.metrics.setdefault(key, []).append((value, step))

    def log_metrics(self, metrics: dict[str, float], step: int | None = None) -> None:
        for key, value in metrics.items():
            self.log_metric(key, value, step=step)

    def log_artifact(self, local_path: Path, artifact_path: str | None = None) -> None:
        self._active_record().artifacts.append(Path(local_path))

    def set_tag(self, key: str, value: str) -> None:
        self._active_record().tags[key] = value

    @property
    def run_id(self) -> str | None:
        return self._active_run_id

    # ------------------------------------------------------------------
    # Introspection helpers (testing use only)
    # ------------------------------------------------------------------

    def get_run(self, run_id: str) -> _RunRecord:
        """Return the named run record (testing use only)."""
        if run_id not in self._runs:
            raise KeyError(f"Run '{run_id}' not found")
        return self._runs[run_id]

    def all_run_ids(self) -> list[str]:
        """Return all recorded run IDs."""
        return list(self._runs)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _active_record(self) -> _RunRecord:
        if self._active_run_id is None:
            raise RuntimeError("No active experiment run.  Call start_run() first.")
        return self._runs[self._active_run_id]


# ---------------------------------------------------------------------------
# MLflow tracker (requires mlflow package and a running server)
# ---------------------------------------------------------------------------


class MLflowTracker(ExperimentTracker):
    """MLflow-backed experiment tracker.

    Wraps the ``mlflow`` Python client.  Requires ``mlflow`` to be
    installed and a tracking server accessible at ``tracking_uri``.

    Parameters
    ----------
    experiment_name:
        MLflow experiment name.  Created if it does not exist.
    tracking_uri:
        MLflow tracking server URI (e.g. ``'http://localhost:5000'``).
    """

    def __init__(self, experiment_name: str, tracking_uri: str) -> None:
        try:
            import mlflow  # type: ignore[import-untyped]
        except ModuleNotFoundError as exc:
            raise ModuleNotFoundError(
                "The 'mlflow' package is required for MLflowTracker.  "
                "Install it with: uv pip install mlflow"
            ) from exc

        self._mlflow = mlflow
        mlflow.set_tracking_uri(tracking_uri)
        mlflow.set_experiment(experiment_name)
        self._active_run: Any = None

    def start_run(self, run_name: str, tags: dict[str, str] | None = None) -> str:
        all_tags = {"started_at_utc": datetime.now(UTC).isoformat()}
        if tags:
            all_tags.update(tags)
        self._active_run = self._mlflow.start_run(run_name=run_name, tags=all_tags)
        return str(self._active_run.info.run_id)

    def end_run(self) -> None:
        if self._active_run is not None:
            self._mlflow.end_run()
            self._active_run = None

    def log_param(self, key: str, value: Any) -> None:
        self._mlflow.log_param(key, value)

    def log_params(self, params: dict[str, Any]) -> None:
        self._mlflow.log_params(params)

    def log_metric(self, key: str, value: float, step: int | None = None) -> None:
        self._mlflow.log_metric(key, value, step=step)

    def log_metrics(self, metrics: dict[str, float], step: int | None = None) -> None:
        self._mlflow.log_metrics(metrics, step=step)

    def log_artifact(self, local_path: Path, artifact_path: str | None = None) -> None:
        self._mlflow.log_artifact(str(local_path), artifact_path)

    def set_tag(self, key: str, value: str) -> None:
        self._mlflow.set_tag(key, value)

    @property
    def run_id(self) -> str | None:
        if self._active_run is None:
            return None
        return str(self._active_run.info.run_id)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def create_tracker(
    mode: str,
    *,
    experiment_name: str = "specproof",
    tracking_uri: str = "http://localhost:5000",
) -> ExperimentTracker:
    """Create a tracker from a mode string.

    Parameters
    ----------
    mode:
        ``'mlflow'`` — use the MLflow tracking server.
        ``'noop'`` — use the in-memory no-op tracker.
    experiment_name:
        Experiment name (MLflow only).
    tracking_uri:
        MLflow server URI (MLflow only).
    """
    if mode == "mlflow":
        return MLflowTracker(experiment_name=experiment_name, tracking_uri=tracking_uri)
    if mode == "noop":
        return NoOpTracker()
    raise ValueError(f"Unknown tracker mode '{mode}'.  Valid values: 'mlflow', 'noop'.")
