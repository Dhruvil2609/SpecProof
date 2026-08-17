"""Training loop implementation for the garment segmentation U-Net.

Provides a standalone trainer that wraps the full PyTorch training
lifecycle: data loading, optimisation, checkpointing, metric logging,
and early stopping.  Integrates with the ``ExperimentTracker`` abstraction.

Usage
-----
    from ml.training.segmentation_trainer import SegmentationTrainer, TrainerConfig
    from ml.training.experiment_tracker import NoOpTracker

    config = TrainerConfig(dataset_dir=Path("ml/datasets/annotations"))
    trainer = SegmentationTrainer(config, tracker=NoOpTracker())
    result = trainer.train()
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.optim as optim

from ml.datasets.annotation_schema import GarmentAnnotation, split_annotations
from ml.training.experiment_tracker import ExperimentTracker, NoOpTracker
from ml.training.segmentation_model import (
    GarmentSegmentationModel,
    SegmentationModelConfig,
    segmentation_iou,
    segmentation_loss,
)

# ---------------------------------------------------------------------------
# Trainer configuration
# ---------------------------------------------------------------------------


@dataclass
class TrainerConfig:
    """Configuration for the segmentation model trainer."""

    dataset_dir: Path
    output_dir: Path = field(default_factory=lambda: Path("ml/exports"))
    checkpoint_dir: Path = field(default_factory=lambda: Path("ml/checkpoints"))
    num_epochs: int = 50
    batch_size: int = 8
    learning_rate: float = 1e-3
    weight_decay: float = 1e-4
    lr_step_size: int = 10
    lr_gamma: float = 0.5
    early_stopping_patience: int = 10
    image_height: int = 256
    image_width: int = 256
    model_config: SegmentationModelConfig = field(
        default_factory=lambda: SegmentationModelConfig(
            in_channels=4, base_channels=16, depth=4
        )
    )
    split_seed: int = 42
    device: str = "cpu"


# ---------------------------------------------------------------------------
# Trainer
# ---------------------------------------------------------------------------


class SegmentationTrainer:
    """Training loop for the garment segmentation U-Net.

    Parameters
    ----------
    config:
        Trainer configuration.
    tracker:
        Experiment tracker (defaults to NoOpTracker).
    """

    def __init__(
        self,
        config: TrainerConfig,
        tracker: ExperimentTracker | None = None,
    ) -> None:
        self.config = config
        self.tracker = tracker or NoOpTracker()
        self.device = torch.device(config.device)
        self.model = GarmentSegmentationModel(config.model_config).to(self.device)
        self.optimiser = optim.AdamW(
            self.model.parameters(),
            lr=config.learning_rate,
            weight_decay=config.weight_decay,
        )
        self.scheduler = optim.lr_scheduler.StepLR(
            self.optimiser,
            step_size=config.lr_step_size,
            gamma=config.lr_gamma,
        )

    def train(self) -> dict[str, Any]:
        """Run the full training loop.

        Returns
        -------
        dict
            Training summary with best metric, checkpoint path, and run ID.
        """
        cfg = self.config
        annotation_paths = sorted(Path(cfg.dataset_dir).glob("*.json"))
        if not annotation_paths:
            raise FileNotFoundError(
                f"No annotation JSON files found in {cfg.dataset_dir}"
            )

        splits = split_annotations(annotation_paths, seed=cfg.split_seed)
        train_paths = splits["train"]
        val_paths = splits["val"]

        run_id = self.tracker.start_run(
            "segmentation-training",
            tags={
                "model": "garment-segmentation",
                "started_at_utc": datetime.now(UTC).isoformat(),
            },
        )
        self.tracker.log_params(
            {
                "num_epochs": cfg.num_epochs,
                "batch_size": cfg.batch_size,
                "learning_rate": cfg.learning_rate,
                "weight_decay": cfg.weight_decay,
                "image_height": cfg.image_height,
                "image_width": cfg.image_width,
                "base_channels": cfg.model_config.base_channels,
                "train_samples": len(train_paths),
                "val_samples": len(val_paths),
            }
        )

        best_val_iou = 0.0
        best_checkpoint_path: Path | None = None
        patience_counter = 0
        cfg.checkpoint_dir.mkdir(parents=True, exist_ok=True)

        for epoch in range(cfg.num_epochs):
            train_loss = self._train_epoch(train_paths, epoch)
            val_iou = self._validate(val_paths)
            lr = float(self.scheduler.get_last_lr()[0])
            self.scheduler.step()

            self.tracker.log_metrics(
                {"train_loss": train_loss, "val_iou": val_iou, "lr": lr},
                step=epoch,
            )

            if val_iou > best_val_iou:
                best_val_iou = val_iou
                patience_counter = 0
                ckpt_path = cfg.checkpoint_dir / f"seg_epoch{epoch:04d}_iou{val_iou:.4f}.pt"
                torch.save(self.model.state_dict(), str(ckpt_path))
                best_checkpoint_path = ckpt_path
            else:
                patience_counter += 1

            if patience_counter >= cfg.early_stopping_patience:
                break

        result: dict[str, Any] = {
            "run_id": run_id,
            "best_val_iou": best_val_iou,
            "best_checkpoint": str(best_checkpoint_path) if best_checkpoint_path else None,
            "completed_at_utc": datetime.now(UTC).isoformat(),
        }
        self.tracker.log_metrics({"best_val_iou": best_val_iou})
        self.tracker.set_tag("status", "completed")
        self.tracker.end_run()
        return result

    def _train_epoch(self, paths: list[Path], epoch: int) -> float:
        self.model.train()
        total_loss = 0.0
        count = 0
        for batch in _batch_iter(paths, self.config.batch_size):
            inputs, targets = _load_segmentation_batch(
                batch, self.config.image_height, self.config.image_width
            )
            inputs = inputs.to(self.device)
            targets = targets.to(self.device)
            self.optimiser.zero_grad()
            outputs = self.model(inputs)
            loss = segmentation_loss(outputs, targets)
            loss.backward()
            self.optimiser.step()
            total_loss += float(loss.item())
            count += 1
        return total_loss / max(count, 1)

    def _validate(self, paths: list[Path]) -> float:
        self.model.eval()
        scores: list[float] = []
        with torch.no_grad():
            for batch in _batch_iter(paths, self.config.batch_size):
                inputs, targets = _load_segmentation_batch(
                    batch, self.config.image_height, self.config.image_width
                )
                inputs = inputs.to(self.device)
                targets = targets.to(self.device)
                outputs = self.model(inputs)
                preds = outputs >= 0.5
                for b in range(inputs.shape[0]):
                    scores.append(segmentation_iou(preds[b], targets[b]))
        return float(np.mean(scores)) if scores else 0.0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_segmentation_batch(
    paths: list[Path], height: int, width: int
) -> tuple[torch.Tensor, torch.Tensor]:
    """Load a batch of segmentation annotation files as tensors."""
    import cv2 as cv

    inputs: list[torch.Tensor] = []
    targets: list[torch.Tensor] = []
    for path in paths:
        ann = GarmentAnnotation.model_validate_json(path.read_text(encoding="utf-8"))
        mask = ann.mask_as_array()
        mask_r = cv.resize(
            mask.astype(np.uint8), (width, height), interpolation=cv.INTER_NEAREST
        ).astype(bool)
        rgb = np.stack([mask_r.astype(np.float32)] * 3, axis=0)
        depth = mask_r.astype(np.float32)[np.newaxis]
        inp = torch.from_numpy(np.concatenate([rgb, depth], axis=0)).float()
        inputs.append(inp)
        targets.append(torch.from_numpy(mask_r.astype(np.float32)).unsqueeze(0))
    return torch.stack(inputs), torch.stack(targets)


def _batch_iter(paths: list[Path], size: int) -> list[list[Path]]:
    return [paths[i : i + size] for i in range(0, len(paths), size)]
