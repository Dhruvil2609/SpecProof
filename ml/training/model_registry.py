"""Model registry for SpecProof ML models.

Tracks versioned model artefacts, supports promotion workflow
(Candidate → Staging → Production), and selects the best model
by a named metric.  File-based; no external service required.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


class ModelStage(StrEnum):
    """Model lifecycle stages."""

    CANDIDATE = "candidate"
    STAGING = "staging"
    PRODUCTION = "production"
    ARCHIVED = "archived"


class ModelVersion(BaseModel):
    """One registered model version."""

    model_name: str
    version: str
    stage: ModelStage = ModelStage.CANDIDATE
    onnx_path: str = Field(description="Relative path to the ONNX export file")
    checkpoint_path: str | None = None
    dataset_version: str = Field(description="Dataset version used for training")
    metrics: dict[str, float] = Field(default_factory=dict)
    params: dict[str, Any] = Field(default_factory=dict)
    run_id: str | None = None
    registered_at_utc: datetime = Field(default_factory=lambda: datetime.now(UTC))
    promoted_at_utc: datetime | None = None
    description: str = ""
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
# Registry
# ---------------------------------------------------------------------------


class ModelRegistry:
    """File-based model version registry.

    Each model version is stored as a JSON file in ``registry_dir``.
    Promotion updates the stage field in-place.

    Parameters
    ----------
    registry_dir:
        Directory for version manifest files.
    """

    def __init__(self, registry_dir: Path) -> None:
        self._dir = Path(registry_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    def register(
        self,
        *,
        model_name: str,
        version: str,
        onnx_path: Path,
        dataset_version: str,
        metrics: dict[str, float] | None = None,
        params: dict[str, Any] | None = None,
        run_id: str | None = None,
        checkpoint_path: Path | None = None,
        description: str = "",
    ) -> ModelVersion:
        """Register a new model version.

        Parameters
        ----------
        model_name:
            Logical model name, e.g. ``'garment-segmentation'``.
        version:
            Semantic version string.
        onnx_path:
            Path to the ONNX model file.
        dataset_version:
            Dataset version string used for training.
        metrics:
            Evaluation metrics dict (e.g. ``{'iou': 0.92, 'recall': 0.88}``).
        params:
            Training hyperparameters.
        run_id:
            Experiment tracking run ID.
        checkpoint_path:
            Path to the PyTorch checkpoint (optional).
        description:
            Human-readable description.

        Returns
        -------
        ModelVersion

        Raises
        ------
        FileExistsError
            If this ``(model_name, version)`` is already registered.
        """
        manifest_path = self._manifest_path(model_name, version)
        if manifest_path.exists():
            raise FileExistsError(
                f"Model version '{model_name}@{version}' is already registered"
            )

        version_record = ModelVersion(
            model_name=model_name,
            version=version,
            onnx_path=str(onnx_path),
            dataset_version=dataset_version,
            metrics=metrics or {},
            params=params or {},
            run_id=run_id,
            checkpoint_path=str(checkpoint_path) if checkpoint_path else None,
            description=description,
            registered_at_utc=datetime.now(UTC),
        )
        manifest_path.write_text(
            version_record.to_canonical_json() + "\n", encoding="utf-8", newline="\n"
        )
        return version_record

    def get(self, model_name: str, version: str) -> ModelVersion:
        """Load a model version manifest.

        Raises
        ------
        KeyError
            If the version is not found.
        """
        manifest_path = self._manifest_path(model_name, version)
        if not manifest_path.exists():
            raise KeyError(f"Model version '{model_name}@{version}' not found")
        return ModelVersion.model_validate_json(manifest_path.read_text(encoding="utf-8"))

    def promote(
        self,
        model_name: str,
        version: str,
        target_stage: ModelStage,
    ) -> ModelVersion:
        """Promote a model to a higher lifecycle stage.

        The previous occupant of ``target_stage`` is automatically archived.

        Parameters
        ----------
        model_name:
            Logical model name.
        version:
            Version to promote.
        target_stage:
            Target lifecycle stage.

        Returns
        -------
        ModelVersion
            The updated version manifest.

        Raises
        ------
        ValueError
            If the promotion is not a valid forward transition.
        """
        record = self.get(model_name, version)
        _validate_transition(record.stage, target_stage)

        # Archive current occupant of target_stage
        for existing in self.list_versions(model_name):
            if existing == version:
                continue
            try:
                ev = self.get(model_name, existing)
            except KeyError:
                continue
            if ev.stage == target_stage:
                archived = ev.model_copy(update={"stage": ModelStage.ARCHIVED})
                self._manifest_path(model_name, existing).write_text(
                    archived.to_canonical_json() + "\n", encoding="utf-8", newline="\n"
                )

        updated = record.model_copy(
            update={"stage": target_stage, "promoted_at_utc": datetime.now(UTC)}
        )
        self._manifest_path(model_name, version).write_text(
            updated.to_canonical_json() + "\n", encoding="utf-8", newline="\n"
        )
        return updated

    def best_version(
        self, model_name: str, metric: str, *, higher_is_better: bool = True
    ) -> ModelVersion | None:
        """Return the version with the best value for ``metric``.

        Only non-archived versions are considered.

        Returns
        -------
        ModelVersion or None if no versions have the metric.
        """
        candidates: list[ModelVersion] = []
        for version_str in self.list_versions(model_name):
            try:
                mv = self.get(model_name, version_str)
            except KeyError:
                continue
            if mv.stage != ModelStage.ARCHIVED and metric in mv.metrics:
                candidates.append(mv)

        if not candidates:
            return None

        return max(candidates, key=lambda mv: mv.metrics[metric]) if higher_is_better else min(
            candidates, key=lambda mv: mv.metrics[metric]
        )

    def list_versions(self, model_name: str) -> list[str]:
        """Return all registered version strings for a model, sorted."""
        prefix = f"{model_name.replace('/', '_')}@"
        versions = []
        for p in self._dir.glob(f"{model_name.replace('/', '_')}@*.json"):
            versions.append(p.stem[len(prefix):])
        return sorted(versions)

    def production_version(self, model_name: str) -> ModelVersion | None:
        """Return the current production version, or None."""
        for version_str in self.list_versions(model_name):
            try:
                mv = self.get(model_name, version_str)
            except KeyError:
                continue
            if mv.stage == ModelStage.PRODUCTION:
                return mv
        return None

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _manifest_path(self, model_name: str, version: str) -> Path:
        safe_name = model_name.replace("/", "_")
        safe_ver = version.replace("/", "_")
        return self._dir / f"{safe_name}@{safe_ver}.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_TRANSITIONS: dict[ModelStage, set[ModelStage]] = {
    ModelStage.CANDIDATE: {ModelStage.STAGING, ModelStage.ARCHIVED},
    ModelStage.STAGING: {ModelStage.PRODUCTION, ModelStage.ARCHIVED},
    ModelStage.PRODUCTION: {ModelStage.ARCHIVED},
    ModelStage.ARCHIVED: set(),
}


def _validate_transition(current: ModelStage, target: ModelStage) -> None:
    allowed = _VALID_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise ValueError(
            f"Invalid stage transition: {current!r} → {target!r}.  "
            f"Allowed transitions from {current!r}: {sorted(str(s) for s in allowed)}"
        )
