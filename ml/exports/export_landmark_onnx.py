"""ONNX export script for the garment landmark heatmap model.

Exports the GarmentLandmarkModel to ONNX format with a fixed
4-channel input (RGB + normalised depth) and verifies:
  - Output shape is (1, 10, H, W)
  - Max absolute difference between PyTorch and ONNX Runtime outputs < 1e-5
  - Argmax landmark decoding is equivalent between PyTorch and ONNX outputs

Usage
-----
    python -m ml.exports.export_landmark_onnx \\
        --output ml/exports/garment-landmark-v1.onnx \\
        --height 256 --width 256

To export from a saved checkpoint::

    python -m ml.exports.export_landmark_onnx \\
        --checkpoint ml/checkpoints/landmark_best.pt \\
        --output ml/exports/garment-landmark-v1.onnx
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

import numpy as np
import torch

_DEFAULT_EXPORT_SEED = 20260817


def export_landmark_model(
    output_path: Path,
    *,
    checkpoint_path: Path | None = None,
    image_height: int = 256,
    image_width: int = 256,
    opset_version: int = 18,
) -> dict[str, object]:
    """Export the landmark model to ONNX and verify correctness.

    Parameters
    ----------
    output_path:
        Destination ONNX file path.
    checkpoint_path:
        Optional PyTorch checkpoint (.pt) to load weights from.
    image_height:
        Fixed input height for the export.
    image_width:
        Fixed input width for the export.
    opset_version:
        ONNX opset version (default 18).

    Returns
    -------
    dict
        Export summary including path, SHA-256, and verification result.

    Raises
    ------
    AssertionError
        If ONNX output does not match PyTorch output within 1e-5.
    """
    from ml.training.landmark_model import (
        NUM_LANDMARKS,
        GarmentLandmarkModel,
        LandmarkModelConfig,
    )

    config = LandmarkModelConfig(in_channels=4, num_landmarks=NUM_LANDMARKS, base_channels=32)
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(_DEFAULT_EXPORT_SEED)
        model = GarmentLandmarkModel(config)

    if checkpoint_path is not None:
        state = torch.load(str(checkpoint_path), map_location="cpu", weights_only=True)
        model.load_state_dict(state)

    model.eval()
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # A local generator keeps verification reproducible without changing application RNG state.
    # Non-uniform input avoids ambiguous argmax locations caused by tied zero-input heatmaps.
    generator = torch.Generator(device="cpu").manual_seed(_DEFAULT_EXPORT_SEED)
    dummy_input = torch.rand(
        1,
        4,
        image_height,
        image_width,
        generator=generator,
    )

    # Reference PyTorch output
    with torch.no_grad():
        pytorch_output = model(dummy_input).numpy()

    # Export
    torch.onnx.export(
        model,
        dummy_input,
        str(output_path),
        opset_version=opset_version,
        input_names=["input_rgbd"],
        output_names=["output_heatmaps"],
        dynamic_axes={
            "input_rgbd": {0: "batch_size"},
            "output_heatmaps": {0: "batch_size"},
        },
    )

    # Verify with ONNX Runtime
    try:
        import onnxruntime as ort  # type: ignore[import-untyped]

        session = ort.InferenceSession(str(output_path), providers=["CPUExecutionProvider"])
        ort_output = session.run(None, {"input_rgbd": dummy_input.numpy()})[0]

        # Shape check
        expected_shape = (1, NUM_LANDMARKS, image_height, image_width)
        assert ort_output.shape == expected_shape, (
            f"ONNX output shape {ort_output.shape} != expected {expected_shape}"
        )

        # Numerical check: T-3.008
        max_diff = float(np.max(np.abs(ort_output - pytorch_output)))
        assert max_diff < 1e-5, (
            f"T-3.008 FAILED: max abs diff = {max_diff:.2e} (threshold 1e-5)"
        )

        # Argmax equivalence: decoded coordinates must match
        pytorch_argmax = np.argmax(pytorch_output[0].reshape(NUM_LANDMARKS, -1), axis=1)
        ort_argmax = np.argmax(ort_output[0].reshape(NUM_LANDMARKS, -1), axis=1)
        assert np.all(pytorch_argmax == ort_argmax), (
            "Argmax landmark coordinates differ between PyTorch and ONNX Runtime"
        )

        verification = "PASS"
        verification_detail = f"max_abs_diff={max_diff:.2e}, argmax_match=True"

    except ModuleNotFoundError:
        verification = "SKIPPED"
        verification_detail = "onnxruntime not installed"
        max_diff = float("nan")

    sha256 = hashlib.sha256(output_path.read_bytes()).hexdigest()

    return {
        "onnx_path": str(output_path),
        "sha256": sha256,
        "input_shape": [1, 4, image_height, image_width],
        "output_shape": [1, NUM_LANDMARKS, image_height, image_width],
        "num_landmarks": NUM_LANDMARKS,
        "opset_version": opset_version,
        "verification": verification,
        "verification_detail": verification_detail,
        "checkpoint_path": str(checkpoint_path) if checkpoint_path else None,
    }


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Export garment landmark model to ONNX")
    parser.add_argument("--output", type=Path, default=Path("ml/exports/garment-landmark.onnx"))
    parser.add_argument("--checkpoint", type=Path, default=None)
    parser.add_argument("--height", type=int, default=256)
    parser.add_argument("--width", type=int, default=256)
    parser.add_argument("--opset", type=int, default=18)
    args = parser.parse_args()

    import json

    result = export_landmark_model(
        args.output,
        checkpoint_path=args.checkpoint,
        image_height=args.height,
        image_width=args.width,
        opset_version=args.opset,
    )
    print(json.dumps(result, indent=2, default=str))

    if result.get("verification") == "PASS":
        print("\n✅ ONNX export verified (T-3.008 PASS)")
    elif result.get("verification") == "SKIPPED":
        print("\n⚠️  ONNX verification skipped (onnxruntime not installed)")
    else:
        print("\n❌ ONNX export verification FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
