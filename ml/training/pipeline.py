"""Training pipeline automation for SpecProof ML models.

Orchestrates: data loading → augmentation → training → evaluation →
ONNX export → model registry registration.

Usage
-----
Run from the project root::

    python -m ml.training.pipeline \\
        --model segmentation \\
        --dataset-dir ml/datasets/annotations \\
        --output-dir ml/exports \\
        --tracker noop

For real training with MLflow::

    python -m ml.training.pipeline \\
        --model segmentation \\
        --tracker mlflow \\
        --mlflow-uri http://localhost:5000
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim

from ml.datasets.annotation_schema import GarmentAnnotation, split_annotations
from ml.datasets.dataset_registry import DatasetRegistry
from ml.training.experiment_tracker import ExperimentTracker, NoOpTracker, create_tracker
from ml.training.landmark_model import (
    GarmentLandmarkModel,
    LandmarkModelConfig,
    landmark_heatmap_loss,
    landmark_recall_at_threshold,
)
from ml.training.model_registry import ModelRegistry, ModelStage
from ml.training.segmentation_model import (
    GarmentSegmentationModel,
    SegmentationModelConfig,
    segmentation_iou,
    segmentation_loss,
)


# ---------------------------------------------------------------------------
# Pipeline configuration
# ---------------------------------------------------------------------------


class PipelineConfig:
    """Training pipeline configuration."""

    def __init__(
        self,
        *,
        model_type: str,
        dataset_dir: Path,
        output_dir: Path,
        registry_dir: Path,
        dataset_version: str = "1.0.0",
        dataset_id: str = "tshirt-segmentation",
        num_epochs: int = 1,
        batch_size: int = 4,
        learning_rate: float = 1e-3,
        image_height: int = 256,
        image_width: int = 256,
        tracker_mode: str = "noop",
        mlflow_uri: str = "http://localhost:5000",
        model_version: str | None = None,
    ) -> None:
        self.model_type = model_type
        self.dataset_dir = Path(dataset_dir)
        self.output_dir = Path(output_dir)
        self.registry_dir = Path(registry_dir)
        self.dataset_version = dataset_version
        self.dataset_id = dataset_id
        self.num_epochs = num_epochs
        self.batch_size = batch_size
        self.learning_rate = learning_rate
        self.image_height = image_height
        self.image_width = image_width
        self.tracker_mode = tracker_mode
        self.mlflow_uri = mlflow_uri
        self.model_version = model_version or datetime.now(UTC).strftime("%Y%m%d-%H%M%S")


# ---------------------------------------------------------------------------
# Pipeline runner
# ---------------------------------------------------------------------------


class TrainingPipeline:
    """End-to-end training pipeline.

    Parameters
    ----------
    config:
        Pipeline configuration.
    tracker:
        Experiment tracker (defaults to NoOpTracker).
    """

    def __init__(
        self,
        config: PipelineConfig,
        tracker: ExperimentTracker | None = None,
    ) -> None:
        self.config = config
        self.tracker = tracker or NoOpTracker()
        self.device = torch.device("cpu")  # CPU-only for software-first phase

    def run(self) -> dict[str, Any]:
        """Execute the full training pipeline.

        Returns
        -------
        dict
            Result summary with model path, metrics, and run ID.
        """
        cfg = self.config
        run_id = self.tracker.start_run(
            run_name=f"{cfg.model_type}-{cfg.model_version}",
            tags={
                "model_type": cfg.model_type,
                "pipeline": "specproof-ml-v1",
                "started_at_utc": datetime.now(UTC).isoformat(),
            },
        )

        try:
            self.tracker.log_params(
                {
                    "model_type": cfg.model_type,
                    "num_epochs": cfg.num_epochs,
                    "batch_size": cfg.batch_size,
                    "learning_rate": cfg.learning_rate,
                    "image_height": cfg.image_height,
                    "image_width": cfg.image_width,
                    "dataset_version": cfg.dataset_version,
                }
            )

            # Load annotations
            annotation_paths = sorted(cfg.dataset_dir.glob("*.json"))
            if not annotation_paths:
                raise FileNotFoundError(
                    f"No annotation JSON files found in {cfg.dataset_dir}. "
                    "Run ml/datasets/annotation_schema.py to generate synthetic data."
                )

            splits = split_annotations(annotation_paths, seed=42)
            train_paths = splits["train"]
            val_paths = splits["val"]

            # Build model
            model, model_name = self._build_model()
            model = model.to(self.device)
            optimiser = optim.Adam(model.parameters(), lr=cfg.learning_rate)

            # Training loop
            best_val_metric = 0.0
            for epoch in range(cfg.num_epochs):
                train_loss = self._train_epoch(model, optimiser, train_paths, epoch)
                val_metric = self._evaluate(model, val_paths)
                self.tracker.log_metrics(
                    {"train_loss": train_loss, "val_metric": val_metric}, step=epoch
                )
                if val_metric > best_val_metric:
                    best_val_metric = val_metric

            # Export to ONNX
            cfg.output_dir.mkdir(parents=True, exist_ok=True)
            onnx_path = cfg.output_dir / f"{model_name}-{cfg.model_version}.onnx"
            _export_to_onnx(model, onnx_path, cfg.model_type, cfg.image_height, cfg.image_width)
            self.tracker.log_artifact(onnx_path)

            # Register model
            registry = ModelRegistry(cfg.registry_dir)
            metrics = {
                "val_iou" if cfg.model_type == "segmentation" else "val_recall": best_val_metric
            }
            try:
                registered = registry.register(
                    model_name=model_name,
                    version=cfg.model_version,
                    onnx_path=onnx_path,
                    dataset_version=cfg.dataset_version,
                    metrics=metrics,
                    params={
                        "num_epochs": cfg.num_epochs,
                        "learning_rate": cfg.learning_rate,
                    },
                    run_id=run_id,
                    description=f"Auto-registered by training pipeline at {datetime.now(UTC).isoformat()}",
                )
            except FileExistsError:
                registered = registry.get(model_name, cfg.model_version)

            result = {
                "run_id": run_id,
                "model_name": model_name,
                "model_version": cfg.model_version,
                "onnx_path": str(onnx_path),
                "metrics": metrics,
                "registry_stage": registered.stage,
                "completed_at_utc": datetime.now(UTC).isoformat(),
            }

            self.tracker.set_tag("status", "completed")
            self.tracker.log_metrics(metrics)

        except Exception:
            self.tracker.set_tag("status", "failed")
            raise
        finally:
            self.tracker.end_run()

        return result

    def _build_model(self) -> tuple[nn.Module, str]:
        if self.config.model_type == "segmentation":
            return GarmentSegmentationModel(SegmentationModelConfig()), "garment-segmentation"
        if self.config.model_type == "landmark":
            return GarmentLandmarkModel(LandmarkModelConfig()), "garment-landmark"
        raise ValueError(f"Unknown model_type '{self.config.model_type}'")

    def _train_epoch(
        self,
        model: nn.Module,
        optimiser: optim.Optimizer,
        annotation_paths: list[Path],
        epoch: int,
    ) -> float:
        model.train()
        total_loss = 0.0
        count = 0
        for batch_paths in _batch(annotation_paths, self.config.batch_size):
            inputs, targets = _load_batch(
                batch_paths, self.config.image_height, self.config.image_width, self.config.model_type
            )
            inputs = inputs.to(self.device)
            targets = targets.to(self.device)
            optimiser.zero_grad()
            outputs = model(inputs)
            if self.config.model_type == "segmentation":
                loss = segmentation_loss(outputs, targets)
            else:
                loss = landmark_heatmap_loss(outputs, targets)
            loss.backward()
            optimiser.step()
            total_loss += float(loss.item())
            count += 1
        return total_loss / max(count, 1)

    def _evaluate(self, model: nn.Module, annotation_paths: list[Path]) -> float:
        model.eval()
        scores: list[float] = []
        with torch.no_grad():
            for batch_paths in _batch(annotation_paths, self.config.batch_size):
                inputs, targets = _load_batch(
                    batch_paths, self.config.image_height, self.config.image_width, self.config.model_type
                )
                inputs = inputs.to(self.device)
                targets = targets.to(self.device)
                outputs = model(inputs)
                if self.config.model_type == "segmentation":
                    pred_mask = outputs >= 0.5
                    for b in range(inputs.shape[0]):
                        scores.append(segmentation_iou(pred_mask[b], targets[b]))
                else:
                    # Use mean peak confidence as a proxy metric
                    scores.append(float(outputs.max().item()))
        return float(np.mean(scores)) if scores else 0.0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _export_to_onnx(
    model: nn.Module,
    output_path: Path,
    model_type: str,
    height: int,
    width: int,
) -> None:
    """Export a model to ONNX format."""
    model.eval()
    dummy_input = torch.zeros(1, 4, height, width)
    out_channels = 1 if model_type == "segmentation" else 10
    torch.onnx.export(
        model,
        dummy_input,
        str(output_path),
        opset_version=18,

        input_names=["input_rgbd"],
        output_names=["output_mask" if model_type == "segmentation" else "output_heatmaps"],
        dynamic_axes={
            "input_rgbd": {0: "batch_size"},
            ("output_mask" if model_type == "segmentation" else "output_heatmaps"): {0: "batch_size"},
        },
    )


def _load_batch(
    paths: list[Path],
    height: int,
    width: int,
    model_type: str,
) -> tuple[torch.Tensor, torch.Tensor]:
    """Load a batch of annotations as input/target tensors."""
    input_list: list[torch.Tensor] = []
    target_list: list[torch.Tensor] = []

    for path in paths:
        ann = GarmentAnnotation.model_validate_json(path.read_text(encoding="utf-8"))
        mask_array = ann.mask_as_array()

        # Resize mask to target height×width
        import cv2 as cv

        mask_resized = cv.resize(
            mask_array.astype(np.uint8), (width, height), interpolation=cv.INTER_NEAREST
        ).astype(bool)

        # Build 4-channel input (3 synthetic RGB from mask + depth channel)
        rgb = np.stack([mask_resized.astype(np.float32)] * 3, axis=0)
        depth = mask_resized.astype(np.float32)[np.newaxis, ...]
        inp = torch.from_numpy(np.concatenate([rgb, depth], axis=0)).float()
        input_list.append(inp)

        if model_type == "segmentation":
            target = torch.from_numpy(mask_resized.astype(np.float32)).unsqueeze(0)
            target_list.append(target)
        else:
            # Dummy zero heatmap targets (real targets need landmark annotations)
            target_list.append(torch.zeros(10, height, width))

    return torch.stack(input_list), torch.stack(target_list)


def _batch(items: list[Path], size: int) -> list[list[Path]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="SpecProof ML training pipeline")
    parser.add_argument("--model", choices=["segmentation", "landmark"], required=True)
    parser.add_argument("--dataset-dir", type=Path, default=Path("ml/datasets/annotations"))
    parser.add_argument("--output-dir", type=Path, default=Path("ml/exports"))
    parser.add_argument("--registry-dir", type=Path, default=Path("ml/registry"))
    parser.add_argument("--tracker", choices=["noop", "mlflow"], default="noop")
    parser.add_argument("--mlflow-uri", default="http://localhost:5000")
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--lr", type=float, default=1e-3)
    return parser


def main() -> None:
    """CLI entry point."""
    args = _build_arg_parser().parse_args()
    tracker = create_tracker(args.tracker, tracking_uri=args.mlflow_uri)
    config = PipelineConfig(
        model_type=args.model,
        dataset_dir=args.dataset_dir,
        output_dir=args.output_dir,
        registry_dir=args.registry_dir,
        num_epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.lr,
        tracker_mode=args.tracker,
        mlflow_uri=args.mlflow_uri,
    )
    pipeline = TrainingPipeline(config, tracker=tracker)
    result = pipeline.run()
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
