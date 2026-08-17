"""Heatmap-based landmark detection model for SpecProof.

Implements a lightweight CNN that outputs one Gaussian heatmap per
T-shirt landmark.  The 10 output channels correspond to the canonical
T-shirt landmark vocabulary defined in ``specproof_measurement_service.landmarks``.

Input:  (B, 4, H, W)  — RGB (3 channels) + normalised depth (1 channel).
Output: (B, 10, H, W) — per-landmark Gaussian heatmaps in [0, 1].

Landmark coordinates are decoded by argmax over each heatmap channel.
"""

from __future__ import annotations

from dataclasses import dataclass

import torch
import torch.nn as nn
import torch.nn.functional as F

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Canonical T-shirt landmark names (must match ``LandmarkName`` enum order)
LANDMARK_NAMES: tuple[str, ...] = (
    "neck_left",
    "neck_right",
    "shoulder_left",
    "shoulder_right",
    "sleeve_hem_left",
    "sleeve_hem_right",
    "side_seam_left",
    "side_seam_right",
    "hem_left",
    "hem_right",
)
NUM_LANDMARKS: int = len(LANDMARK_NAMES)


# ---------------------------------------------------------------------------
# Model configuration
# ---------------------------------------------------------------------------


@dataclass
class LandmarkModelConfig:
    """Hyperparameters for the heatmap landmark model."""

    in_channels: int = 4       # RGB (3) + normalised depth (1)
    num_landmarks: int = NUM_LANDMARKS
    base_channels: int = 32    # Feature map width
    heatmap_sigma: float = 4.0  # Gaussian sigma used during training target generation


# ---------------------------------------------------------------------------
# Architecture
# ---------------------------------------------------------------------------


class _ResBlock(nn.Module):
    """Residual 3×3 conv block with BatchNorm."""

    def __init__(self, channels: int) -> None:
        super().__init__()
        self.block = nn.Sequential(
            nn.Conv2d(channels, channels, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(channels),
            nn.ReLU(inplace=True),
            nn.Conv2d(channels, channels, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(channels),
        )
        self.relu = nn.ReLU(inplace=True)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.relu(self.block(x) + x)  # type: ignore[no-any-return]


class GarmentLandmarkModel(nn.Module):
    """Heatmap landmark detection model for T-shirts.

    Architecture
    ------------
    - Input stem: 4→base_channels (stride-2 downsample × 2).
    - Body: 4 residual blocks.
    - Head: 1×1 conv → ``num_landmarks`` channels → sigmoid heatmaps.
    - Decoder: bilinear upsample back to input resolution.

    Parameters
    ----------
    config:
        Model hyperparameters.
    """

    def __init__(self, config: LandmarkModelConfig | None = None) -> None:
        super().__init__()
        cfg = config or LandmarkModelConfig()
        c = cfg.base_channels

        # Encoder stem (stride 4 total)
        self.stem = nn.Sequential(
            nn.Conv2d(cfg.in_channels, c, kernel_size=3, stride=2, padding=1, bias=False),
            nn.BatchNorm2d(c),
            nn.ReLU(inplace=True),
            nn.Conv2d(c, c * 2, kernel_size=3, stride=2, padding=1, bias=False),
            nn.BatchNorm2d(c * 2),
            nn.ReLU(inplace=True),
        )

        # Body: residual blocks
        self.body = nn.Sequential(
            _ResBlock(c * 2),
            _ResBlock(c * 2),
            _ResBlock(c * 2),
            _ResBlock(c * 2),
        )

        # Heatmap head
        self.head = nn.Sequential(
            nn.Conv2d(c * 2, c, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(c),
            nn.ReLU(inplace=True),
            nn.Conv2d(c, cfg.num_landmarks, kernel_size=1),
        )

        self.num_landmarks = cfg.num_landmarks

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass.

        Parameters
        ----------
        x:
            Input tensor ``(B, 4, H, W)``.

        Returns
        -------
        torch.Tensor
            Heatmaps ``(B, num_landmarks, H, W)`` in ``[0, 1]``.
        """
        h, w = x.shape[2], x.shape[3]
        features = self.body(self.stem(x))
        heatmaps_small = self.head(features)
        # Upsample back to input resolution
        heatmaps = F.interpolate(heatmaps_small, size=(h, w), mode="bilinear", align_corners=False)
        return torch.sigmoid(heatmaps)  # type: ignore[no-any-return]

    def decode_landmarks(
        self, heatmaps: torch.Tensor, *, confidence_threshold: float = 0.1
    ) -> list[dict[str, object]]:
        """Decode heatmaps to landmark coordinates.

        Parameters
        ----------
        heatmaps:
            Batch of heatmaps, shape ``(B, num_landmarks, H, W)``.
        confidence_threshold:
            Minimum peak value to report a landmark as detected.

        Returns
        -------
        list[dict]
            One dict per batch item.  Each dict maps landmark name to
            ``{'x': float, 'y': float, 'confidence': float, 'detected': bool}``.
        """
        batch_results: list[dict[str, object]] = []
        b, n, h, w = heatmaps.shape
        for bi in range(b):
            item: dict[str, object] = {}
            for li in range(min(n, len(LANDMARK_NAMES))):
                channel = heatmaps[bi, li]  # (H, W)
                peak_val = float(channel.max().item())
                flat_idx = int(channel.argmax().item())
                y = flat_idx // w
                x = flat_idx % w
                detected = peak_val >= confidence_threshold
                item[LANDMARK_NAMES[li]] = {
                    "x": float(x),
                    "y": float(y),
                    "confidence": peak_val,
                    "detected": detected,
                }
            batch_results.append(item)
        return batch_results


# ---------------------------------------------------------------------------
# Heatmap target generation
# ---------------------------------------------------------------------------


def generate_heatmap_targets(
    landmark_points: list[tuple[float, float] | None],
    *,
    height: int,
    width: int,
    sigma: float = 4.0,
) -> torch.Tensor:
    """Generate Gaussian heatmap targets for training.

    Parameters
    ----------
    landmark_points:
        List of ``(x, y)`` image coordinates, one per landmark.
        ``None`` indicates a missing/occluded landmark (zero heatmap).
    height:
        Output heatmap height in pixels.
    width:
        Output heatmap width in pixels.
    sigma:
        Gaussian standard deviation in pixels.

    Returns
    -------
    torch.Tensor
        Heatmap tensor of shape ``(num_landmarks, H, W)``.
    """
    n = len(landmark_points)
    heatmaps = torch.zeros(n, height, width, dtype=torch.float32)
    ys = torch.arange(height, dtype=torch.float32).unsqueeze(1)  # (H, 1)
    xs = torch.arange(width, dtype=torch.float32).unsqueeze(0)   # (1, W)
    for i, point in enumerate(landmark_points):
        if point is None:
            continue
        px, py = float(point[0]), float(point[1])
        gauss = torch.exp(-((xs - px) ** 2 + (ys - py) ** 2) / (2.0 * sigma ** 2))
        heatmaps[i] = gauss
    return heatmaps


# ---------------------------------------------------------------------------
# Loss functions
# ---------------------------------------------------------------------------


def landmark_heatmap_loss(
    pred: torch.Tensor,
    target: torch.Tensor,
    *,
    visibility_mask: torch.Tensor | None = None,
) -> torch.Tensor:
    """MSE loss on heatmap predictions.

    Parameters
    ----------
    pred:
        Predicted heatmaps ``(B, N, H, W)``.
    target:
        Ground-truth heatmaps ``(B, N, H, W)``.
    visibility_mask:
        Boolean tensor ``(B, N)`` — True for visible/labelled landmarks.
        If None, all landmarks contribute equally.

    Returns
    -------
    torch.Tensor
        Scalar MSE loss.
    """
    if visibility_mask is None:
        return F.mse_loss(pred, target)

    # Expand mask to match spatial dims
    mask = visibility_mask.float().unsqueeze(-1).unsqueeze(-1)  # (B, N, 1, 1)
    masked_pred = pred * mask
    masked_target = target * mask
    num_visible = float(visibility_mask.float().sum().item()) * pred.shape[2] * pred.shape[3]
    if num_visible == 0.0:
        return torch.tensor(0.0, requires_grad=True)
    return ((masked_pred - masked_target) ** 2).sum() / num_visible


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


def landmark_recall_at_threshold(
    decoded: list[dict[str, object]],
    ground_truth: list[dict[str, tuple[float, float]]],
    *,
    tolerance_px: float,
) -> float:
    """Compute recall @ tolerance_px across a batch.

    Parameters
    ----------
    decoded:
        Output of ``GarmentLandmarkModel.decode_landmarks()``.
    ground_truth:
        List of dicts mapping landmark name to ``(x, y)`` ground-truth coordinate.
    tolerance_px:
        Distance threshold in pixels.

    Returns
    -------
    float
        Recall in ``[0, 1]``.
    """
    import math

    total = 0
    hits = 0
    for item_decoded, item_gt in zip(decoded, ground_truth, strict=True):
        for name, gt_point in item_gt.items():
            total += 1
            pred_info = item_decoded.get(name)
            if pred_info is None:
                continue
            pred_dict = pred_info  # type: ignore[assignment]
            if not pred_dict.get("detected", False):  # type: ignore[union-attr]
                continue
            dx = float(pred_dict["x"]) - gt_point[0]  # type: ignore[index]
            dy = float(pred_dict["y"]) - gt_point[1]  # type: ignore[index]
            if math.hypot(dx, dy) <= tolerance_px:
                hits += 1
    return hits / total if total > 0 else 1.0
