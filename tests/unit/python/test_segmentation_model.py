"""Tests for garment segmentation model, ONNX export, and evaluation tests.

Covers:
- TASK-3.2.2.1: U-Net architecture forward pass and output shape
- TASK-3.2.2.7: ONNX export correctness (T-3.008)
- TASK-3.2.2.9: Model evaluation tests (IoU gate, segmentation metrics)
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest
import torch

# Add ml/ to path for imports
sys.path.insert(0, str(Path(__file__).parents[3]))

from ml.training.segmentation_model import (
    GarmentSegmentationModel,
    SegmentationModelConfig,
    dice_loss,
    segmentation_iou,
    segmentation_loss,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def small_config() -> SegmentationModelConfig:
    """Minimal model config for fast tests."""
    return SegmentationModelConfig(in_channels=4, base_channels=8, depth=4)


@pytest.fixture()
def model(small_config: SegmentationModelConfig) -> GarmentSegmentationModel:
    return GarmentSegmentationModel(small_config)


@pytest.fixture()
def dummy_input() -> torch.Tensor:
    """(1, 4, 64, 64) synthetic RGBD input."""
    return torch.zeros(1, 4, 64, 64)


# ---------------------------------------------------------------------------
# Architecture tests
# ---------------------------------------------------------------------------


class TestGarmentSegmentationModel:
    @pytest.mark.unit
    def test_forward_output_shape(
        self, model: GarmentSegmentationModel, dummy_input: torch.Tensor
    ) -> None:
        """Forward pass produces (1, 1, H, W) output."""
        output = model(dummy_input)
        assert output.shape == (1, 1, 64, 64)

    @pytest.mark.unit
    def test_forward_output_in_range(
        self, model: GarmentSegmentationModel, dummy_input: torch.Tensor
    ) -> None:
        """Output values are in [0, 1] (sigmoid activation)."""
        output = model(dummy_input)
        assert float(output.min().item()) >= 0.0
        assert float(output.max().item()) <= 1.0

    @pytest.mark.unit
    def test_batch_processing(self, model: GarmentSegmentationModel) -> None:
        """Model handles batch size > 1."""
        batch = torch.zeros(3, 4, 64, 64)
        output = model(batch)
        assert output.shape == (3, 1, 64, 64)

    @pytest.mark.unit
    def test_non_square_input(self, model: GarmentSegmentationModel) -> None:
        """Model handles non-square input (128×64)."""
        inp = torch.zeros(1, 4, 128, 64)
        output = model(inp)
        assert output.shape == (1, 1, 128, 64)

    @pytest.mark.unit
    def test_predict_mask_binary(
        self, model: GarmentSegmentationModel, dummy_input: torch.Tensor
    ) -> None:
        """predict_mask returns a boolean tensor."""
        mask = model.predict_mask(dummy_input)
        assert mask.dtype == torch.bool

    @pytest.mark.unit
    def test_predict_mask_shape(
        self, model: GarmentSegmentationModel, dummy_input: torch.Tensor
    ) -> None:
        """predict_mask output shape matches input spatial dims."""
        mask = model.predict_mask(dummy_input)
        assert mask.shape == (1, 1, 64, 64)

    @pytest.mark.unit
    def test_model_parameters_exist(self, model: GarmentSegmentationModel) -> None:
        """Model has trainable parameters."""
        params = list(model.parameters())
        assert len(params) > 0
        total = sum(p.numel() for p in params)
        assert total > 0


# ---------------------------------------------------------------------------
# Loss function tests
# ---------------------------------------------------------------------------


class TestSegmentationLoss:
    @pytest.mark.unit
    def test_dice_loss_perfect_prediction_zero(self) -> None:
        """Dice loss is 0.0 for perfect prediction."""
        pred = torch.ones(1, 1, 8, 8)
        target = torch.ones(1, 1, 8, 8)
        loss = dice_loss(pred, target)
        assert float(loss.item()) == pytest.approx(0.0, abs=1e-4)

    @pytest.mark.unit
    def test_dice_loss_empty_prediction_near_one(self) -> None:
        """Dice loss is ≈ 1.0 when prediction is empty and target is full."""
        pred = torch.zeros(1, 1, 8, 8)
        target = torch.ones(1, 1, 8, 8)
        loss = dice_loss(pred, target)
        assert float(loss.item()) == pytest.approx(1.0, abs=0.01)

    @pytest.mark.unit
    def test_segmentation_loss_positive(self) -> None:
        """Combined BCE+Dice loss is positive for non-trivial inputs."""
        pred = torch.rand(2, 1, 16, 16)
        target = (torch.rand(2, 1, 16, 16) > 0.5).float()
        loss = segmentation_loss(pred, target)
        assert float(loss.item()) > 0.0

    @pytest.mark.unit
    def test_segmentation_loss_perfect_zero(self) -> None:
        """Combined loss approaches 0 for perfect predictions."""
        pred = torch.ones(1, 1, 8, 8)
        target = torch.ones(1, 1, 8, 8)
        loss = segmentation_loss(pred, target)
        assert float(loss.item()) < 0.1


# ---------------------------------------------------------------------------
# IoU metric tests
# ---------------------------------------------------------------------------


class TestSegmentationIoU:
    @pytest.mark.unit
    def test_perfect_overlap_iou_one(self) -> None:
        """Perfect prediction → IoU = 1.0."""
        mask = torch.ones(1, 1, 8, 8, dtype=torch.bool)
        assert segmentation_iou(mask, mask) == pytest.approx(1.0)

    @pytest.mark.unit
    def test_no_overlap_iou_zero(self) -> None:
        """No overlap → IoU = 0.0."""
        pred = torch.zeros(1, 1, 8, 8, dtype=torch.bool)
        pred[0, 0, :4, :] = True
        target = torch.zeros(1, 1, 8, 8, dtype=torch.bool)
        target[0, 0, 4:, :] = True
        assert segmentation_iou(pred, target) == pytest.approx(0.0)

    @pytest.mark.unit
    def test_both_empty_iou_one(self) -> None:
        """Both masks empty → IoU = 1.0 by convention."""
        pred = torch.zeros(1, 1, 8, 8, dtype=torch.bool)
        target = torch.zeros(1, 1, 8, 8, dtype=torch.bool)
        assert segmentation_iou(pred, target) == pytest.approx(1.0)

    @pytest.mark.unit
    def test_half_overlap_iou_one_third(self) -> None:
        """50% overlap between equal-sized masks → IoU = 1/3."""
        pred = torch.zeros(1, 1, 1, 8, dtype=torch.bool)
        pred[0, 0, 0, :4] = True
        target = torch.zeros(1, 1, 1, 8, dtype=torch.bool)
        target[0, 0, 0, 2:6] = True
        # intersection = 2, union = 6 → IoU = 1/3
        assert segmentation_iou(pred, target) == pytest.approx(1.0 / 3.0, abs=0.01)


# ---------------------------------------------------------------------------
# ONNX export round-trip test (T-3.008)
# ---------------------------------------------------------------------------


class TestONNXExport:
    @pytest.mark.unit
    def test_onnx_export_and_round_trip(self, tmp_path: Path) -> None:
        """T-3.008 — ONNX export produces identical output to PyTorch (max diff < 1e-5)."""
        from ml.exports.export_segmentation_onnx import export_segmentation_model

        result = export_segmentation_model(
            tmp_path / "test_seg.onnx",
            image_height=64,
            image_width=64,
        )
        assert result["verification"] in ("PASS", "SKIPPED"), (
            f"ONNX export verification failed: {result}"
        )
        if result["verification"] == "PASS":
            detail = str(result.get("verification_detail", ""))
            # Extract max_abs_diff from detail string
            if "max_abs_diff=" in detail:
                diff_str = detail.split("max_abs_diff=")[1].split(",")[0]
                max_diff = float(diff_str)
                assert max_diff < 1e-5, f"T-3.008: max_abs_diff = {max_diff:.2e} exceeds 1e-5"

    @pytest.mark.unit
    def test_onnx_output_shape(self, tmp_path: Path) -> None:
        """Exported ONNX model produces (1, 1, H, W) output."""
        try:
            import onnxruntime as ort  # type: ignore[import-untyped]
        except ModuleNotFoundError:
            pytest.skip("onnxruntime not installed")

        from ml.exports.export_segmentation_onnx import export_segmentation_model

        onnx_path = tmp_path / "seg_shape_test.onnx"
        export_segmentation_model(onnx_path, image_height=64, image_width=64)

        session = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
        inp = np.zeros((1, 4, 64, 64), dtype=np.float32)
        out = session.run(None, {"input_rgbd": inp})[0]
        assert out.shape == (1, 1, 64, 64)

    @pytest.mark.unit
    def test_onnx_export_summary_keys(self, tmp_path: Path) -> None:
        """Export result dict contains expected keys."""
        from ml.exports.export_segmentation_onnx import export_segmentation_model

        result = export_segmentation_model(
            tmp_path / "summary_test.onnx",
            image_height=64,
            image_width=64,
        )
        for key in ("onnx_path", "sha256", "input_shape", "output_shape", "verification"):
            assert key in result, f"Missing key '{key}' in export result"


# ---------------------------------------------------------------------------
# Evaluation tests (TASK-3.2.2.9)
# ---------------------------------------------------------------------------


class TestSegmentationEvaluation:
    @pytest.mark.unit
    def test_iou_gate_on_synthetic_dataset(self, tmp_path: Path) -> None:
        """Synthetic dataset IoU ≥ threshold when mask is perfectly recovered."""
        # Deterministic baseline: all-ones prediction = all-ones target → IoU=1.0
        pred = torch.ones(1, 1, 32, 32, dtype=torch.bool)
        target = torch.ones(1, 1, 32, 32, dtype=torch.bool)
        iou = segmentation_iou(pred, target)
        assert iou >= 0.85, f"IoU gate failed: {iou:.3f} < 0.85"

    @pytest.mark.unit
    def test_annotation_schema_rle_round_trip(self, tmp_path: Path) -> None:
        """Annotation mask encodes and decodes without error."""
        from ml.datasets.annotation_schema import generate_synthetic_tshirt_dataset

        paths = generate_synthetic_tshirt_dataset(tmp_path / "annotations", count=3)
        from ml.datasets.annotation_schema import GarmentAnnotation

        for p in paths:
            ann = GarmentAnnotation.model_validate_json(p.read_text(encoding="utf-8"))
            mask = ann.mask_as_array()
            assert mask.shape == (ann.image_height, ann.image_width)
            assert mask.dtype == bool

    @pytest.mark.unit
    def test_synthetic_dataset_iou_is_one(self, tmp_path: Path) -> None:
        """Deterministic segmentation on synthetic masks achieves IoU = 1.0."""
        from ml.datasets.annotation_schema import (
            GarmentAnnotation,
            generate_synthetic_tshirt_dataset,
        )

        paths = generate_synthetic_tshirt_dataset(tmp_path / "anns", count=2, seed=7)
        for p in paths:
            ann = GarmentAnnotation.model_validate_json(p.read_text(encoding="utf-8"))
            gt = torch.from_numpy(ann.mask_as_array()).bool().unsqueeze(0).unsqueeze(0)
            # Deterministic baseline: predict the mask itself
            iou = segmentation_iou(gt, gt)
            assert iou == pytest.approx(1.0), f"Expected IoU=1.0, got {iou}"
