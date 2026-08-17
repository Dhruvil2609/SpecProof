"""ML pipeline integration tests.

Tests the end-to-end ML infrastructure stack:
- Dataset registry: register, get, list, integrity check (TASK-3.2.6.1)
- Experiment tracker: NoOpTracker run lifecycle (TASK-3.2.6.2)
- Model registry: register, promote, best_version (TASK-3.2.6.3)
- Drift detector: baseline comparison, alert generation (TASK-3.2.6.6)
- Training pipeline: synthetic data → ONNX → registry (TASK-3.2.6.4)

These tests use only the NoOpTracker and file-based registries;
no external services (MLflow, Docker) are required.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Ensure ml/ is importable from the project root
sys.path.insert(0, str(Path(__file__).parents[3]))


# ---------------------------------------------------------------------------
# Dataset registry integration (TASK-3.2.6.1)
# ---------------------------------------------------------------------------


class TestDatasetRegistryIntegration:
    @pytest.mark.integration
    def test_register_and_get_round_trip(self, tmp_path: Path) -> None:
        """Register a dataset version and retrieve it with correct metadata."""
        from ml.datasets.annotation_schema import generate_synthetic_tshirt_dataset
        from ml.datasets.dataset_registry import DatasetRegistry

        ann_dir = tmp_path / "annotations"
        paths = generate_synthetic_tshirt_dataset(ann_dir, count=6)

        registry = DatasetRegistry(tmp_path / "registry")
        registry.register(
            dataset_id="tshirt-seg",
            version="1.0.0",
            description="Synthetic T-shirt segmentation dataset",
            category="t_shirt",
            splits={"train": paths[:4], "val": paths[4:]},
        )

        retrieved = registry.get("tshirt-seg", "1.0.0")
        assert retrieved.dataset_id == "tshirt-seg"
        assert retrieved.version == "1.0.0"
        assert retrieved.total_annotations == 6
        assert len(retrieved.splits) == 2

    @pytest.mark.integration
    def test_register_duplicate_raises(self, tmp_path: Path) -> None:
        """Registering the same (dataset_id, version) twice raises FileExistsError."""
        from ml.datasets.annotation_schema import generate_synthetic_tshirt_dataset
        from ml.datasets.dataset_registry import DatasetRegistry

        paths = generate_synthetic_tshirt_dataset(tmp_path / "anns", count=4)
        registry = DatasetRegistry(tmp_path / "reg")
        registry.register(
            dataset_id="test-ds",
            version="1.0.0",
            description="First registration",
            category="t_shirt",
            splits={"train": paths},
        )
        with pytest.raises(FileExistsError):
            registry.register(
                dataset_id="test-ds",
                version="1.0.0",
                description="Duplicate",
                category="t_shirt",
                splits={"train": paths},
            )

    @pytest.mark.integration
    def test_integrity_check_passes_fresh_dataset(self, tmp_path: Path) -> None:
        """Integrity check passes immediately after registration."""
        from ml.datasets.annotation_schema import generate_synthetic_tshirt_dataset
        from ml.datasets.dataset_registry import DatasetRegistry

        paths = generate_synthetic_tshirt_dataset(tmp_path / "anns", count=4)
        registry = DatasetRegistry(tmp_path / "reg")
        registry.register(
            dataset_id="fresh-ds",
            version="1.0.0",
            description="Integrity test",
            category="t_shirt",
            splits={"train": paths},
        )
        assert registry.verify_integrity("fresh-ds", "1.0.0") is True

    @pytest.mark.integration
    def test_integrity_check_fails_after_file_modification(self, tmp_path: Path) -> None:
        """Integrity check fails if a dataset file is modified after registration."""
        from ml.datasets.annotation_schema import generate_synthetic_tshirt_dataset
        from ml.datasets.dataset_registry import DatasetRegistry

        paths = generate_synthetic_tshirt_dataset(tmp_path / "anns", count=2)
        registry = DatasetRegistry(tmp_path / "reg")
        registry.register(
            dataset_id="tamper-ds",
            version="1.0.0",
            description="Tamper test",
            category="t_shirt",
            splits={"train": paths},
        )
        # Corrupt one file
        paths[0].write_text("corrupted", encoding="utf-8")
        assert registry.verify_integrity("tamper-ds", "1.0.0") is False

    @pytest.mark.integration
    def test_list_versions_returns_all_versions(self, tmp_path: Path) -> None:
        """list_versions returns all registered versions sorted."""
        from ml.datasets.annotation_schema import generate_synthetic_tshirt_dataset
        from ml.datasets.dataset_registry import DatasetRegistry

        paths = generate_synthetic_tshirt_dataset(tmp_path / "anns", count=2)
        registry = DatasetRegistry(tmp_path / "reg")
        for v in ("1.0.0", "1.1.0", "2.0.0"):
            registry.register(
                dataset_id="multi-ds",
                version=v,
                description=f"Version {v}",
                category="t_shirt",
                splits={"train": paths},
            )
        versions = registry.list_versions("multi-ds")
        assert versions == ["1.0.0", "1.1.0", "2.0.0"]


# ---------------------------------------------------------------------------
# Experiment tracker integration (TASK-3.2.6.2)
# ---------------------------------------------------------------------------


class TestExperimentTrackerIntegration:
    @pytest.mark.integration
    def test_noop_tracker_run_lifecycle(self) -> None:
        """NoOpTracker: start_run → log → end_run stores all data."""
        from ml.training.experiment_tracker import NoOpTracker

        tracker = NoOpTracker()
        run_id = tracker.start_run("test-run", tags={"environment": "ci"})
        assert tracker.run_id == run_id

        tracker.log_params({"lr": 1e-3, "epochs": 5})
        tracker.log_metric("train_loss", 0.42, step=0)
        tracker.log_metric("train_loss", 0.31, step=1)
        tracker.log_metrics({"val_iou": 0.91}, step=1)
        tracker.set_tag("status", "running")
        tracker.end_run()

        assert tracker.run_id is None
        record = tracker.get_run(run_id)
        assert record.params["lr"] == pytest.approx(1e-3)
        assert record.params["epochs"] == 5
        assert record.metrics["train_loss"] == [(0.42, 0), (0.31, 1)]
        assert record.metrics["val_iou"] == [(0.91, 1)]
        assert record.tags["status"] == "running"

    @pytest.mark.integration
    def test_noop_tracker_multiple_runs(self) -> None:
        """NoOpTracker supports multiple sequential runs."""
        from ml.training.experiment_tracker import NoOpTracker

        tracker = NoOpTracker()
        id1 = tracker.start_run("run-1")
        tracker.log_metric("loss", 0.5)
        tracker.end_run()

        id2 = tracker.start_run("run-2")
        tracker.log_metric("loss", 0.3)
        tracker.end_run()

        assert id1 != id2
        assert set(tracker.all_run_ids()) == {id1, id2}

    @pytest.mark.integration
    def test_noop_tracker_log_without_run_raises(self) -> None:
        """Logging without an active run raises RuntimeError."""
        from ml.training.experiment_tracker import NoOpTracker

        tracker = NoOpTracker()
        with pytest.raises(RuntimeError, match="No active experiment run"):
            tracker.log_metric("loss", 0.5)

    @pytest.mark.integration
    def test_create_tracker_noop(self) -> None:
        """create_tracker('noop') returns a NoOpTracker."""
        from ml.training.experiment_tracker import NoOpTracker, create_tracker

        tracker = create_tracker("noop")
        assert isinstance(tracker, NoOpTracker)

    @pytest.mark.integration
    def test_create_tracker_invalid_mode_raises(self) -> None:
        """create_tracker with unknown mode raises ValueError."""
        from ml.training.experiment_tracker import create_tracker

        with pytest.raises(ValueError, match="Unknown tracker mode"):
            create_tracker("invalid_mode")


# ---------------------------------------------------------------------------
# Model registry integration (TASK-3.2.6.3)
# ---------------------------------------------------------------------------


class TestModelRegistryIntegration:
    @pytest.fixture()
    def dummy_onnx(self, tmp_path: Path) -> Path:
        """Create a dummy ONNX file (just bytes for registry tests)."""
        p = tmp_path / "model.onnx"
        p.write_bytes(b"dummy_onnx_content")
        return p

    @pytest.mark.integration
    def test_register_and_retrieve(self, tmp_path: Path, dummy_onnx: Path) -> None:
        """Register a model version and retrieve it."""
        from ml.training.model_registry import ModelRegistry, ModelStage

        registry = ModelRegistry(tmp_path / "model_registry")
        mv = registry.register(
            model_name="garment-segmentation",
            version="1.0.0",
            onnx_path=dummy_onnx,
            dataset_version="1.0.0",
            metrics={"val_iou": 0.88},
            description="Test registration",
        )
        assert mv.model_name == "garment-segmentation"
        assert mv.version == "1.0.0"
        assert mv.stage == ModelStage.CANDIDATE
        assert mv.metrics["val_iou"] == pytest.approx(0.88)

    @pytest.mark.integration
    def test_promote_candidate_to_staging(self, tmp_path: Path, dummy_onnx: Path) -> None:
        """Model can be promoted from Candidate to Staging."""
        from ml.training.model_registry import ModelRegistry, ModelStage

        registry = ModelRegistry(tmp_path / "reg")
        registry.register(
            model_name="seg",
            version="1.0.0",
            onnx_path=dummy_onnx,
            dataset_version="1.0.0",
        )
        updated = registry.promote("seg", "1.0.0", ModelStage.STAGING)
        assert updated.stage == ModelStage.STAGING

    @pytest.mark.integration
    def test_promote_staging_to_production(self, tmp_path: Path, dummy_onnx: Path) -> None:
        """Model can be promoted from Staging to Production."""
        from ml.training.model_registry import ModelRegistry, ModelStage

        registry = ModelRegistry(tmp_path / "reg")
        registry.register(
            model_name="seg",
            version="1.0.0",
            onnx_path=dummy_onnx,
            dataset_version="1.0.0",
        )
        registry.promote("seg", "1.0.0", ModelStage.STAGING)
        registry.promote("seg", "1.0.0", ModelStage.PRODUCTION)
        prod = registry.production_version("seg")
        assert prod is not None
        assert prod.version == "1.0.0"

    @pytest.mark.integration
    def test_best_version_by_metric(self, tmp_path: Path, dummy_onnx: Path) -> None:
        """best_version returns the version with highest metric value."""
        from ml.training.model_registry import ModelRegistry

        registry = ModelRegistry(tmp_path / "reg")
        for ver, iou in [("1.0.0", 0.82), ("1.1.0", 0.91), ("1.2.0", 0.78)]:
            registry.register(
                model_name="seg",
                version=ver,
                onnx_path=dummy_onnx,
                dataset_version="1.0.0",
                metrics={"val_iou": iou},
            )
        best = registry.best_version("seg", "val_iou")
        assert best is not None
        assert best.version == "1.1.0"

    @pytest.mark.integration
    def test_invalid_stage_transition_raises(self, tmp_path: Path, dummy_onnx: Path) -> None:
        """Promoting a production model to staging raises ValueError."""
        from ml.training.model_registry import ModelRegistry, ModelStage

        registry = ModelRegistry(tmp_path / "reg")
        registry.register(
            model_name="seg",
            version="1.0.0",
            onnx_path=dummy_onnx,
            dataset_version="1.0.0",
        )
        registry.promote("seg", "1.0.0", ModelStage.STAGING)
        registry.promote("seg", "1.0.0", ModelStage.PRODUCTION)
        with pytest.raises(ValueError, match="Invalid stage transition"):
            registry.promote("seg", "1.0.0", ModelStage.STAGING)


# ---------------------------------------------------------------------------
# Drift detector integration (TASK-3.2.6.6)
# ---------------------------------------------------------------------------


class TestDriftDetectorIntegration:
    def _make_report(self, tmp_path: Path, name: str, iou: float) -> Path:
        """Write a minimal evaluation report JSON."""
        report = {
            "model_name": "seg",
            "model_type": "segmentation",
            "onnx_path": "dummy.onnx",
            "evaluation_set_size": 10,
            "overall_metric": iou,
            "segmentation": {"mean_iou": iou, "iou_above_85": 1.0 if iou >= 0.85 else 0.0},
            "passed_exit_criteria": iou >= 0.85,
            "exit_criteria_description": "mean IoU ≥ 0.85",
        }
        p = tmp_path / f"{name}.json"
        p.write_text(json.dumps(report), encoding="utf-8")
        return p

    @pytest.mark.integration
    def test_no_drift_when_metrics_stable(self, tmp_path: Path) -> None:
        """No drift detected when current metric equals baseline."""
        from ml.evaluation.drift_detector import DriftDetector

        baseline = self._make_report(tmp_path, "baseline", 0.90)
        current = self._make_report(tmp_path, "current", 0.90)
        detector = DriftDetector(baseline, threshold_percent=5.0)
        report = detector.compare(current)
        assert report.any_drift_detected is False

    @pytest.mark.integration
    def test_drift_detected_on_regression(self, tmp_path: Path) -> None:
        """Drift is detected when metric drops by more than threshold."""
        from ml.evaluation.drift_detector import DriftDetector

        baseline = self._make_report(tmp_path, "baseline", 0.90)
        current = self._make_report(tmp_path, "current", 0.80)
        detector = DriftDetector(baseline, threshold_percent=5.0)
        report = detector.compare(current)
        assert report.any_drift_detected is True
        assert report.drift_count >= 1

    @pytest.mark.integration
    def test_no_drift_on_improvement(self, tmp_path: Path) -> None:
        """Improvement above threshold is not flagged as drift."""
        from ml.evaluation.drift_detector import DriftDetector

        baseline = self._make_report(tmp_path, "baseline", 0.85)
        current = self._make_report(tmp_path, "current", 0.93)
        detector = DriftDetector(baseline, threshold_percent=5.0)
        report = detector.compare(current)
        assert report.any_drift_detected is False

    @pytest.mark.integration
    def test_drift_report_summary_contains_regression_word(self, tmp_path: Path) -> None:
        """Drift report summary mentions 'DRIFT DETECTED' on regression."""
        from ml.evaluation.drift_detector import DriftDetector

        baseline = self._make_report(tmp_path, "baseline", 0.92)
        current = self._make_report(tmp_path, "current", 0.70)
        detector = DriftDetector(baseline, threshold_percent=5.0)
        report = detector.compare(current)
        assert "DRIFT DETECTED" in report.summary

    @pytest.mark.integration
    def test_save_as_baseline_promotes_file(self, tmp_path: Path) -> None:
        """save_as_baseline overwrites the baseline with the current report."""
        from ml.evaluation.drift_detector import DriftDetector

        baseline = self._make_report(tmp_path, "baseline", 0.85)
        current = self._make_report(tmp_path, "current", 0.91)
        detector = DriftDetector(baseline, threshold_percent=5.0)
        detector.save_as_baseline(current)

        # After promoting, comparing current to itself should show no drift
        report = detector.compare(current)
        assert report.any_drift_detected is False


# ---------------------------------------------------------------------------
# Training pipeline smoke test (TASK-3.2.6.4)
# ---------------------------------------------------------------------------


class TestTrainingPipelineIntegration:
    @pytest.mark.integration
    def test_segmentation_pipeline_smoke(self, tmp_path: Path) -> None:
        """End-to-end segmentation pipeline runs without error on synthetic data."""
        from ml.datasets.annotation_schema import generate_synthetic_tshirt_dataset
        from ml.training.experiment_tracker import NoOpTracker
        from ml.training.pipeline import PipelineConfig, TrainingPipeline

        ann_dir = tmp_path / "annotations"
        generate_synthetic_tshirt_dataset(ann_dir, count=8)

        config = PipelineConfig(
            model_type="segmentation",
            dataset_dir=ann_dir,
            output_dir=tmp_path / "exports",
            registry_dir=tmp_path / "registry",
            num_epochs=1,
            batch_size=2,
            image_height=64,
            image_width=64,
        )
        tracker = NoOpTracker()
        pipeline = TrainingPipeline(config, tracker=tracker)
        result = pipeline.run()

        assert "onnx_path" in result
        assert Path(result["onnx_path"]).exists()
        assert "metrics" in result
        assert len(tracker.all_run_ids()) == 1

    @pytest.mark.integration
    def test_landmark_pipeline_smoke(self, tmp_path: Path) -> None:
        """End-to-end landmark pipeline runs without error on synthetic data."""
        from ml.datasets.annotation_schema import generate_synthetic_tshirt_dataset
        from ml.training.experiment_tracker import NoOpTracker
        from ml.training.pipeline import PipelineConfig, TrainingPipeline

        ann_dir = tmp_path / "annotations"
        generate_synthetic_tshirt_dataset(ann_dir, count=8)

        config = PipelineConfig(
            model_type="landmark",
            dataset_dir=ann_dir,
            output_dir=tmp_path / "exports",
            registry_dir=tmp_path / "registry",
            num_epochs=1,
            batch_size=2,
            image_height=64,
            image_width=64,
        )
        tracker = NoOpTracker()
        pipeline = TrainingPipeline(config, tracker=tracker)
        result = pipeline.run()

        assert "onnx_path" in result
        assert Path(result["onnx_path"]).exists()
