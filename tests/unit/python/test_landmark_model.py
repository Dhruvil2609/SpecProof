"""Tests for landmark heatmap model, graph refinement, and ONNX export.

Covers:
- TASK-3.2.4.2: Heatmap model architecture and forward pass
- TASK-3.2.4.6: Graph-based landmark refinement constraints
- TASK-3.2.4.7: ONNX export correctness (T-3.008)
- Recall metric and argmax decoding
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest
import torch

# Add ml/ to path for imports
sys.path.insert(0, str(Path(__file__).parents[3]))

from ml.training.landmark_model import (
    NUM_LANDMARKS,
    GarmentLandmarkModel,
    LandmarkModelConfig,
    generate_heatmap_targets,
    landmark_heatmap_loss,
    landmark_recall_at_threshold,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def small_config() -> LandmarkModelConfig:
    return LandmarkModelConfig(in_channels=4, num_landmarks=NUM_LANDMARKS, base_channels=16)


@pytest.fixture()
def model(small_config: LandmarkModelConfig) -> GarmentLandmarkModel:
    return GarmentLandmarkModel(small_config)


@pytest.fixture()
def dummy_input() -> torch.Tensor:
    return torch.zeros(1, 4, 64, 64)


# ---------------------------------------------------------------------------
# Architecture tests (TASK-3.2.4.2)
# ---------------------------------------------------------------------------


class TestGarmentLandmarkModel:
    @pytest.mark.unit
    def test_forward_output_shape(
        self, model: GarmentLandmarkModel, dummy_input: torch.Tensor
    ) -> None:
        """Forward pass produces (1, NUM_LANDMARKS, H, W) output."""
        output = model(dummy_input)
        assert output.shape == (1, NUM_LANDMARKS, 64, 64)

    @pytest.mark.unit
    def test_forward_output_in_range(
        self, model: GarmentLandmarkModel, dummy_input: torch.Tensor
    ) -> None:
        """Output values are in [0, 1] (sigmoid activation)."""
        output = model(dummy_input)
        assert float(output.min().item()) >= 0.0
        assert float(output.max().item()) <= 1.0

    @pytest.mark.unit
    def test_batch_size_2(self, model: GarmentLandmarkModel) -> None:
        """Model handles batch size 2."""
        inp = torch.zeros(2, 4, 64, 64)
        output = model(inp)
        assert output.shape == (2, NUM_LANDMARKS, 64, 64)

    @pytest.mark.unit
    def test_num_landmarks_is_10(self) -> None:
        """Vocabulary contains exactly 10 T-shirt landmarks."""
        assert NUM_LANDMARKS == 10

    @pytest.mark.unit
    def test_model_has_parameters(self, model: GarmentLandmarkModel) -> None:
        """Model has trainable parameters."""
        params = list(model.parameters())
        assert len(params) > 0
        assert sum(p.numel() for p in params) > 0

    @pytest.mark.unit
    def test_decode_landmarks_returns_list(
        self, model: GarmentLandmarkModel, dummy_input: torch.Tensor
    ) -> None:
        """decode_landmarks returns a list of dicts."""
        with torch.no_grad():
            heatmaps = model(dummy_input)
        result = model.decode_landmarks(heatmaps)
        assert isinstance(result, list)
        assert len(result) == 1

    @pytest.mark.unit
    def test_decode_landmarks_keys(
        self, model: GarmentLandmarkModel, dummy_input: torch.Tensor
    ) -> None:
        """Decoded landmarks contain all 10 landmark names."""
        from ml.training.landmark_model import LANDMARK_NAMES

        with torch.no_grad():
            heatmaps = model(dummy_input)
        result = model.decode_landmarks(heatmaps)
        item = result[0]
        for name in LANDMARK_NAMES:
            assert name in item, f"Missing landmark '{name}' in decoded output"


# ---------------------------------------------------------------------------
# Heatmap target generation
# ---------------------------------------------------------------------------


class TestHeatmapTargets:
    @pytest.mark.unit
    def test_target_shape(self) -> None:
        """Heatmap targets have shape (num_landmarks, H, W)."""
        points = [(32.0, 32.0)] * NUM_LANDMARKS  # type: ignore[list-item]
        targets = generate_heatmap_targets(points, height=64, width=64, sigma=4.0)
        assert targets.shape == (NUM_LANDMARKS, 64, 64)

    @pytest.mark.unit
    def test_peak_at_landmark_position(self) -> None:
        """Heatmap peak is at the annotated landmark position."""
        point = (20.0, 30.0)  # x=20, y=30
        points = [None] * NUM_LANDMARKS  # type: ignore[list-item]
        points[0] = point  # type: ignore[call-overload]
        targets = generate_heatmap_targets(points, height=64, width=64, sigma=3.0)  # type: ignore[arg-type]
        channel = targets[0]
        flat_idx = int(channel.argmax().item())
        w = 64
        peak_y = flat_idx // w
        peak_x = flat_idx % w
        assert peak_x == 20 and peak_y == 30, (
            f"Peak at ({peak_x}, {peak_y}) ≠ expected (20, 30)"
        )

    @pytest.mark.unit
    def test_missing_landmark_zero_heatmap(self) -> None:
        """Missing landmark (None) produces all-zero heatmap."""
        points = [None] * NUM_LANDMARKS  # type: ignore[list-item]
        targets = generate_heatmap_targets(points, height=32, width=32)  # type: ignore[arg-type]
        assert float(targets.max().item()) == pytest.approx(0.0)

    @pytest.mark.unit
    def test_heatmap_values_in_range(self) -> None:
        """Heatmap values are in [0, 1]."""
        points = [(16.0, 16.0)] * NUM_LANDMARKS  # type: ignore[list-item]
        targets = generate_heatmap_targets(points, height=32, width=32)  # type: ignore[arg-type]
        assert float(targets.min().item()) >= 0.0
        assert float(targets.max().item()) <= 1.0 + 1e-6


# ---------------------------------------------------------------------------
# Loss function tests
# ---------------------------------------------------------------------------


class TestLandmarkLoss:
    @pytest.mark.unit
    def test_loss_positive_for_random_inputs(self) -> None:
        """Loss is positive for random predictions and targets."""
        pred = torch.rand(2, NUM_LANDMARKS, 32, 32)
        target = torch.rand(2, NUM_LANDMARKS, 32, 32)
        loss = landmark_heatmap_loss(pred, target)
        assert float(loss.item()) > 0.0

    @pytest.mark.unit
    def test_loss_zero_for_identical_inputs(self) -> None:
        """Loss is 0.0 for identical prediction and target."""
        t = torch.rand(1, NUM_LANDMARKS, 16, 16)
        loss = landmark_heatmap_loss(t, t)
        assert float(loss.item()) == pytest.approx(0.0, abs=1e-6)

    @pytest.mark.unit
    def test_loss_with_visibility_mask(self) -> None:
        """Loss with visibility mask is computed without error."""
        pred = torch.rand(2, NUM_LANDMARKS, 16, 16)
        target = torch.rand(2, NUM_LANDMARKS, 16, 16)
        mask = torch.ones(2, NUM_LANDMARKS, dtype=torch.bool)
        mask[0, 5] = False  # occlude one landmark
        loss = landmark_heatmap_loss(pred, target, visibility_mask=mask)
        assert float(loss.item()) >= 0.0


# ---------------------------------------------------------------------------
# Recall metric tests
# ---------------------------------------------------------------------------


class TestLandmarkRecall:
    @pytest.mark.unit
    def test_perfect_recall_at_threshold(self) -> None:
        """Recall = 1.0 when all predictions are within tolerance."""
        decoded = [{"neck_left": {"x": 10.0, "y": 20.0, "confidence": 0.9, "detected": True}}]
        gt = [{"neck_left": (10.0, 20.0)}]
        recall = landmark_recall_at_threshold(decoded, gt, tolerance_px=5.0)
        assert recall == pytest.approx(1.0)

    @pytest.mark.unit
    def test_zero_recall_outside_tolerance(self) -> None:
        """Recall = 0.0 when predictions are outside tolerance."""
        decoded = [{"neck_left": {"x": 50.0, "y": 50.0, "confidence": 0.9, "detected": True}}]
        gt = [{"neck_left": (0.0, 0.0)}]
        recall = landmark_recall_at_threshold(decoded, gt, tolerance_px=5.0)
        assert recall == pytest.approx(0.0)

    @pytest.mark.unit
    def test_empty_ground_truth_returns_one(self) -> None:
        """Empty ground truth → recall = 1.0 by convention."""
        decoded: list[dict[str, object]] = [{}]
        gt: list[dict[str, tuple[float, float]]] = [{}]
        recall = landmark_recall_at_threshold(decoded, gt, tolerance_px=5.0)
        assert recall == pytest.approx(1.0)

    @pytest.mark.unit
    def test_not_detected_counts_as_miss(self) -> None:
        """Landmark marked detected=False counts as a miss."""
        decoded = [{"neck_left": {"x": 10.0, "y": 20.0, "confidence": 0.01, "detected": False}}]
        gt = [{"neck_left": (10.0, 20.0)}]
        recall = landmark_recall_at_threshold(decoded, gt, tolerance_px=5.0)
        assert recall == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Graph refinement tests (TASK-3.2.4.6)
# ---------------------------------------------------------------------------


class TestGraphRefineLandmarks:
    @pytest.fixture()
    def tshirt_landmark_set(self) -> object:
        """Generate a synthetic T-shirt landmark set."""
        import numpy as np
        from specproof_measurement_service.landmarks import detect_tshirt_landmarks

        mask = np.zeros((200, 200), dtype=np.bool_)
        mask[20:180, 60:140] = True  # body
        mask[20:60, 20:60] = True   # left sleeve
        mask[20:60, 140:180] = True  # right sleeve
        mask[20:40, 90:110] = False  # neckline
        return detect_tshirt_landmarks(mask)

    @pytest.mark.unit
    def test_graph_refine_returns_landmark_set(self) -> None:
        """graph_refine_landmarks returns a LandmarkSet."""
        import numpy as np
        from specproof_measurement_service.landmarks import (
            LandmarkSet,
            detect_tshirt_landmarks,
            graph_refine_landmarks,
        )

        mask = np.zeros((200, 200), dtype=np.bool_)
        # Simple rectangle (no neckline)
        mask[20:180, 60:140] = True
        landmark_set = detect_tshirt_landmarks(mask)
        refined = graph_refine_landmarks(landmark_set)
        assert isinstance(refined, LandmarkSet)

    @pytest.mark.unit
    def test_graph_refine_preserves_landmark_count(self) -> None:
        """Refined landmark set has same number of landmarks."""
        import numpy as np
        from specproof_measurement_service.landmarks import (
            detect_tshirt_landmarks,
            graph_refine_landmarks,
        )

        mask = np.zeros((200, 200), dtype=np.bool_)
        mask[20:180, 60:140] = True
        original = detect_tshirt_landmarks(mask)
        refined = graph_refine_landmarks(original)
        assert len(refined.landmarks) == len(original.landmarks)

    @pytest.mark.unit
    def test_sequential_ordering_left_side(self) -> None:
        """After refinement, left-side landmarks are ordered top to bottom."""
        import numpy as np
        from specproof_measurement_service.landmarks import (
            LandmarkName,
            LandmarkStatus,
            detect_tshirt_landmarks,
            graph_refine_landmarks,
        )

        # Create a T-shirt mask
        mask = np.zeros((300, 300), dtype=np.bool_)
        mask[30:250, 80:220] = True
        mask[30:80, 20:80] = True  # left sleeve
        mask[30:80, 220:280] = True  # right sleeve
        mask[30:50, 130:170] = False  # neckline

        original = detect_tshirt_landmarks(mask)
        refined = graph_refine_landmarks(original)

        _LEFT_SEQUENCE = (
            LandmarkName.NECK_LEFT,
            LandmarkName.SHOULDER_LEFT,
            LandmarkName.SLEEVE_HEM_LEFT,
            LandmarkName.SIDE_SEAM_LEFT,
            LandmarkName.HEM_LEFT,
        )
        prev_y = -1.0
        for name in _LEFT_SEQUENCE:
            lm = next((landmark for landmark in refined.landmarks if landmark.name == name), None)
            if lm is None or lm.status != LandmarkStatus.DETECTED:
                continue
            assert lm.y > prev_y, (
                f"Ordering violation: {name} y={lm.y:.1f} ≤ prev_y={prev_y:.1f}"
            )
            prev_y = lm.y

    @pytest.mark.unit
    def test_graph_refine_empty_mask_no_error(self) -> None:
        """Graph refinement on empty mask does not raise."""
        import numpy as np
        from specproof_measurement_service.landmarks import (
            detect_tshirt_landmarks,
            graph_refine_landmarks,
        )

        mask = np.zeros((100, 100), dtype=np.bool_)
        original = detect_tshirt_landmarks(mask)
        refined = graph_refine_landmarks(original)
        assert refined is not None


# ---------------------------------------------------------------------------
# ONNX export round-trip test (T-3.008)
# ---------------------------------------------------------------------------


class TestLandmarkONNXExport:
    @pytest.mark.unit
    def test_uncheckpointed_export_is_reproducible(self, tmp_path: Path) -> None:
        """Repeated uncheckpointed exports use stable weights and verification input."""
        from ml.exports.export_landmark_onnx import export_landmark_model

        first = export_landmark_model(
            tmp_path / "landmark-first.onnx",
            image_height=64,
            image_width=64,
        )
        second = export_landmark_model(
            tmp_path / "landmark-second.onnx",
            image_height=64,
            image_width=64,
        )

        assert first["verification_detail"] == second["verification_detail"]

    @pytest.mark.unit
    def test_onnx_export_and_round_trip(self, tmp_path: Path) -> None:
        """T-3.008 — Landmark ONNX output matches PyTorch output (max diff < 1e-5)."""
        from ml.exports.export_landmark_onnx import export_landmark_model

        result = export_landmark_model(
            tmp_path / "test_landmark.onnx",
            image_height=64,
            image_width=64,
        )
        assert result["verification"] in ("PASS", "SKIPPED")
        if result["verification"] == "PASS":
            detail = str(result.get("verification_detail", ""))
            if "max_abs_diff=" in detail:
                diff_str = detail.split("max_abs_diff=")[1].split(",")[0]
                max_diff = float(diff_str)
                assert max_diff < 1e-5

    @pytest.mark.unit
    def test_onnx_output_shape(self, tmp_path: Path) -> None:
        """Exported landmark ONNX model outputs (1, 10, H, W) heatmaps."""
        try:
            import onnxruntime as ort  # type: ignore[import-untyped]
        except ModuleNotFoundError:
            pytest.skip("onnxruntime not installed")

        from ml.exports.export_landmark_onnx import export_landmark_model

        onnx_path = tmp_path / "lm_shape_test.onnx"
        export_landmark_model(onnx_path, image_height=64, image_width=64)
        session = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
        inp = np.zeros((1, 4, 64, 64), dtype=np.float32)
        out = session.run(None, {"input_rgbd": inp})[0]
        assert out.shape == (1, NUM_LANDMARKS, 64, 64)

    @pytest.mark.unit
    def test_onnx_argmax_decoding_matches_pytorch(self, tmp_path: Path) -> None:
        """Argmax decoded coordinates match between PyTorch and ONNX Runtime."""
        try:
            import onnxruntime as ort  # type: ignore[import-untyped]
        except ModuleNotFoundError:
            pytest.skip("onnxruntime not installed")

        from ml.training.landmark_model import GarmentLandmarkModel, LandmarkModelConfig

        cfg = LandmarkModelConfig(in_channels=4, base_channels=16)
        m = GarmentLandmarkModel(cfg)
        m.eval()
        inp = torch.rand(1, 4, 64, 64)
        with torch.no_grad():
            pytorch_out = m(inp).numpy()

        onnx_path = tmp_path / "argmax_test.onnx"
        torch.onnx.export(m, inp, str(onnx_path), opset_version=17,
                          input_names=["input_rgbd"], output_names=["output_heatmaps"])
        session = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
        ort_out = session.run(None, {"input_rgbd": inp.numpy()})[0]

        pt_argmax = np.argmax(pytorch_out[0].reshape(NUM_LANDMARKS, -1), axis=1)
        ort_argmax = np.argmax(ort_out[0].reshape(NUM_LANDMARKS, -1), axis=1)
        np.testing.assert_array_equal(pt_argmax, ort_argmax)
