"""Per-POM evaluation pipeline for SpecProof ML models.

Loads ONNX-exported models, runs inference on evaluation annotations,
and computes per-category metrics including IoU, recall@5mm, and
per-class breakdown.  Outputs a structured JSON evaluation report.
"""

from __future__ import annotations

import json
import math
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import cv2 as cv

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Report data models
# ---------------------------------------------------------------------------


class SegmentationMetrics(BaseModel):
    """Per-category segmentation metrics."""

    category: str
    num_samples: int
    mean_iou: float
    iou_above_85: float = Field(description="Fraction of samples with IoU ≥ 0.85")
    iou_values: list[float]


class LandmarkMetrics(BaseModel):
    """Per-landmark recall metrics."""

    landmark_name: str
    recall_at_5px: float
    num_samples: int


class EvaluationReport(BaseModel):
    """Structured ML evaluation report."""

    model_name: str
    model_type: str
    onnx_path: str
    evaluation_set_size: int
    evaluated_at_utc: datetime = Field(default_factory=lambda: datetime.now(UTC))
    segmentation: SegmentationMetrics | None = None
    landmarks: list[LandmarkMetrics] | None = None
    overall_metric: float
    passed_exit_criteria: bool
    exit_criteria_description: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_canonical_json(self) -> str:
        """Return canonical UTF-8 JSON with sorted keys."""
        return json.dumps(
            self.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )


# ---------------------------------------------------------------------------
# Evaluation runner
# ---------------------------------------------------------------------------


class EvaluationPipeline:
    """Run ONNX model inference and compute evaluation metrics.

    Parameters
    ----------
    onnx_path:
        Path to the exported ONNX model.
    model_type:
        ``'segmentation'`` or ``'landmark'``.
    annotation_dir:
        Directory containing annotation JSON files (evaluation split).
    output_dir:
        Directory to write the evaluation report JSON.
    image_height:
        Model input height.
    image_width:
        Model input width.
    """

    def __init__(
        self,
        *,
        onnx_path: Path,
        model_type: str,
        annotation_dir: Path,
        output_dir: Path,
        image_height: int = 256,
        image_width: int = 256,
    ) -> None:
        self.onnx_path = Path(onnx_path)
        self.model_type = model_type
        self.annotation_dir = Path(annotation_dir)
        self.output_dir = Path(output_dir)
        self.image_height = image_height
        self.image_width = image_width
        self._session: Any = None

    def _get_session(self) -> Any:
        """Lazy-load ONNX Runtime session."""
        if self._session is None:
            try:
                import onnxruntime as ort  # type: ignore[import-untyped]

                self._session = ort.InferenceSession(
                    str(self.onnx_path),
                    providers=["CPUExecutionProvider"],
                )
            except ModuleNotFoundError as exc:
                raise ModuleNotFoundError(
                    "onnxruntime is required for inference.  Install with: uv pip install onnxruntime"
                ) from exc
        return self._session

    def run(self, model_name: str = "unknown") -> EvaluationReport:
        """Execute the evaluation pipeline and return a report.

        Parameters
        ----------
        model_name:
            Human-readable model name for the report.

        Returns
        -------
        EvaluationReport
        """
        annotation_paths = sorted(self.annotation_dir.glob("*.json"))
        if not annotation_paths:
            raise FileNotFoundError(f"No annotations found in {self.annotation_dir}")

        if self.model_type == "segmentation":
            report = self._evaluate_segmentation(model_name, annotation_paths)
        elif self.model_type == "landmark":
            report = self._evaluate_landmarks(model_name, annotation_paths)
        else:
            raise ValueError(f"Unknown model_type '{self.model_type}'")

        self.output_dir.mkdir(parents=True, exist_ok=True)
        report_path = (
            self.output_dir
            / f"eval_{model_name.replace('/', '_')}_{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}.json"
        )
        report_path.write_text(report.to_canonical_json() + "\n", encoding="utf-8", newline="\n")
        return report

    # ------------------------------------------------------------------
    # Segmentation evaluation
    # ------------------------------------------------------------------

    def _evaluate_segmentation(
        self, model_name: str, annotation_paths: list[Path]
    ) -> EvaluationReport:
        from ml.datasets.annotation_schema import GarmentAnnotation

        session = self._get_session()
        iou_values: list[float] = []

        for path in annotation_paths:
            ann = GarmentAnnotation.model_validate_json(path.read_text(encoding="utf-8"))
            gt_mask = ann.mask_as_array()
            input_tensor = _prepare_input(gt_mask, self.image_height, self.image_width)
            outputs = session.run(None, {"input_rgbd": input_tensor})
            pred_prob = outputs[0][0, 0]  # (H, W)
            pred_mask = pred_prob >= 0.5
            gt_resized = cv.resize(
                gt_mask.astype(np.uint8),
                (self.image_width, self.image_height),
                interpolation=cv.INTER_NEAREST,
            ).astype(bool)
            iou_values.append(_binary_iou(pred_mask, gt_resized))

        mean_iou = float(np.mean(iou_values)) if iou_values else 0.0
        iou_above_85 = float(np.mean([v >= 0.85 for v in iou_values])) if iou_values else 0.0

        seg_metrics = SegmentationMetrics(
            category="t_shirt",
            num_samples=len(iou_values),
            mean_iou=mean_iou,
            iou_above_85=iou_above_85,
            iou_values=iou_values,
        )

        passed = mean_iou >= 0.85
        return EvaluationReport(
            model_name=model_name,
            model_type="segmentation",
            onnx_path=str(self.onnx_path),
            evaluation_set_size=len(annotation_paths),
            segmentation=seg_metrics,
            overall_metric=mean_iou,
            passed_exit_criteria=passed,
            exit_criteria_description="mean IoU ≥ 0.85 on evaluation set",
        )

    # ------------------------------------------------------------------
    # Landmark evaluation
    # ------------------------------------------------------------------

    def _evaluate_landmarks(
        self, model_name: str, annotation_paths: list[Path]
    ) -> EvaluationReport:
        from ml.datasets.annotation_schema import GarmentAnnotation
        from ml.training.landmark_model import LANDMARK_NAMES

        session = self._get_session()
        per_landmark_hits: dict[str, list[bool]] = {n: [] for n in LANDMARK_NAMES}

        for path in annotation_paths:
            ann = GarmentAnnotation.model_validate_json(path.read_text(encoding="utf-8"))
            gt_mask = ann.mask_as_array()
            input_tensor = _prepare_input(gt_mask, self.image_height, self.image_width)
            outputs = session.run(None, {"input_rgbd": input_tensor})
            heatmaps = outputs[0][0]  # (10, H, W)

            for i, name in enumerate(LANDMARK_NAMES):
                gt_lm = next((lm for lm in ann.landmarks if lm.name == name), None)
                if gt_lm is None or gt_lm.visibility == 0:
                    continue
                channel = heatmaps[i]
                flat_idx = int(np.argmax(channel))
                h, w = channel.shape
                pred_y = flat_idx // w
                pred_x = flat_idx % w
                gt_x = gt_lm.point.x * (self.image_width / ann.image_width)
                gt_y = gt_lm.point.y * (self.image_height / ann.image_height)
                dist = math.hypot(pred_x - gt_x, pred_y - gt_y)
                per_landmark_hits[name].append(dist <= 5.0)

        landmark_metrics: list[LandmarkMetrics] = []
        all_recalls: list[float] = []
        for name, hits in per_landmark_hits.items():
            recall = float(np.mean(hits)) if hits else 0.0
            all_recalls.append(recall)
            landmark_metrics.append(
                LandmarkMetrics(
                    landmark_name=name,
                    recall_at_5px=recall,
                    num_samples=len(hits),
                )
            )

        mean_recall = float(np.mean(all_recalls)) if all_recalls else 0.0
        passed = mean_recall >= 0.80

        return EvaluationReport(
            model_name=model_name,
            model_type="landmark",
            onnx_path=str(self.onnx_path),
            evaluation_set_size=len(annotation_paths),
            landmarks=landmark_metrics,
            overall_metric=mean_recall,
            passed_exit_criteria=passed,
            exit_criteria_description="mean recall@5px ≥ 0.80 across all landmarks",
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _prepare_input(
    mask: np.ndarray,
    height: int,
    width: int,
) -> np.ndarray:
    """Convert a mask to a 4-channel ONNX input tensor."""
    resized = cv.resize(
        mask.astype(np.uint8), (width, height), interpolation=cv.INTER_NEAREST
    ).astype(np.float32)
    rgb = np.stack([resized] * 3, axis=0)
    depth = resized[np.newaxis, ...]
    inp = np.concatenate([rgb, depth], axis=0)[np.newaxis, ...]  # (1, 4, H, W)
    return inp


def _binary_iou(pred: np.ndarray, target: np.ndarray) -> float:
    """Compute binary IoU between two boolean arrays."""
    union = int(np.count_nonzero(pred | target))
    if union == 0:
        return 1.0
    intersection = int(np.count_nonzero(pred & target))
    return intersection / union
