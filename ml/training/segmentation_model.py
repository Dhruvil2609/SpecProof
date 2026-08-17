"""Segmentation U-Net model architecture for SpecProof.

Implements a lightweight U-Net encoder-decoder with skip connections.
Input: (B, C, H, W) where C = 4 (RGB + depth normalised to [0, 1]).
Output: (B, 1, H, W) sigmoid-activated garment probability map.

The model is designed to be ONNX-exportable from a deterministic
initialisation (no hardware-captured training required for export).
Real training requires an annotated dataset produced by the annotation
pipeline in ``ml/datasets/annotation_schema.py``.
"""

from __future__ import annotations

from dataclasses import dataclass

import torch
import torch.nn as nn
import torch.nn.functional as F

# ---------------------------------------------------------------------------
# Architecture blocks
# ---------------------------------------------------------------------------


class _ConvBlock(nn.Module):
    """Two 3×3 convolutions with BatchNorm and ReLU."""

    def __init__(self, in_channels: int, out_channels: int) -> None:
        super().__init__()
        self.block = nn.Sequential(
            nn.Conv2d(in_channels, out_channels, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_channels, out_channels, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.block(x)  # type: ignore[no-any-return]


class _Down(nn.Module):
    """MaxPool + ConvBlock (encoder step)."""

    def __init__(self, in_channels: int, out_channels: int) -> None:
        super().__init__()
        self.pool = nn.MaxPool2d(2)
        self.conv = _ConvBlock(in_channels, out_channels)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.conv(self.pool(x))  # type: ignore[no-any-return]


class _Up(nn.Module):
    """Bilinear upsample + concatenate skip + ConvBlock (decoder step)."""

    def __init__(self, in_channels: int, out_channels: int) -> None:
        super().__init__()
        self.up = nn.Upsample(scale_factor=2, mode="bilinear", align_corners=False)
        self.conv = _ConvBlock(in_channels, out_channels)

    def forward(self, x: torch.Tensor, skip: torch.Tensor) -> torch.Tensor:
        x = self.up(x)
        # Pad if spatial dims differ (odd input sizes)
        diff_h = skip.size(2) - x.size(2)
        diff_w = skip.size(3) - x.size(3)
        x = F.pad(x, [diff_w // 2, diff_w - diff_w // 2, diff_h // 2, diff_h - diff_h // 2])
        return self.conv(torch.cat([skip, x], dim=1))  # type: ignore[no-any-return]


# ---------------------------------------------------------------------------
# U-Net model
# ---------------------------------------------------------------------------


@dataclass
class SegmentationModelConfig:
    """Hyperparameters for the segmentation U-Net."""

    in_channels: int = 4       # RGB (3) + normalised depth (1)
    base_channels: int = 16    # Doubled at each encoder level
    depth: int = 4             # Number of encoder/decoder levels


class GarmentSegmentationModel(nn.Module):
    """Lightweight U-Net for garment segmentation.

    Parameters
    ----------
    config:
        Model hyperparameters.
    """

    def __init__(self, config: SegmentationModelConfig | None = None) -> None:
        super().__init__()
        cfg = config or SegmentationModelConfig()
        c = cfg.base_channels

        # Encoder
        self.enc1 = _ConvBlock(cfg.in_channels, c)
        self.enc2 = _Down(c, c * 2)
        self.enc3 = _Down(c * 2, c * 4)
        self.enc4 = _Down(c * 4, c * 8)

        # Bottleneck
        self.bottleneck = _Down(c * 8, c * 16)

        # Decoder
        self.dec4 = _Up(c * 16 + c * 8, c * 8)
        self.dec3 = _Up(c * 8 + c * 4, c * 4)
        self.dec2 = _Up(c * 4 + c * 2, c * 2)
        self.dec1 = _Up(c * 2 + c, c)

        # Output
        self.output_conv = nn.Conv2d(c, 1, kernel_size=1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass.

        Parameters
        ----------
        x:
            Input tensor of shape ``(B, 4, H, W)``.

        Returns
        -------
        torch.Tensor
            Segmentation probability map of shape ``(B, 1, H, W)``.
        """
        e1 = self.enc1(x)
        e2 = self.enc2(e1)
        e3 = self.enc3(e2)
        e4 = self.enc4(e3)
        b = self.bottleneck(e4)
        d4 = self.dec4(b, e4)
        d3 = self.dec3(d4, e3)
        d2 = self.dec2(d3, e2)
        d1 = self.dec1(d2, e1)
        return torch.sigmoid(self.output_conv(d1))  # type: ignore[no-any-return]

    def predict_mask(self, x: torch.Tensor, *, threshold: float = 0.5) -> torch.Tensor:
        """Run inference and threshold to a binary mask.

        Parameters
        ----------
        x:
            Input tensor ``(B, 4, H, W)``.
        threshold:
            Probability threshold for foreground classification.

        Returns
        -------
        torch.Tensor
            Boolean mask tensor ``(B, 1, H, W)``.
        """
        with torch.no_grad():
            probs = self.forward(x)
        return probs >= threshold


# ---------------------------------------------------------------------------
# Loss functions
# ---------------------------------------------------------------------------


def dice_loss(pred: torch.Tensor, target: torch.Tensor, eps: float = 1e-6) -> torch.Tensor:
    """Soft Dice loss for binary segmentation.

    Parameters
    ----------
    pred:
        Predicted probability map, shape ``(B, 1, H, W)``, values in ``[0, 1]``.
    target:
        Ground-truth binary mask, shape ``(B, 1, H, W)``, values in ``{0, 1}``.
    eps:
        Smoothing term to avoid division by zero.

    Returns
    -------
    torch.Tensor
        Scalar Dice loss.
    """
    pred_flat = pred.view(-1)
    target_flat = target.view(-1).float()
    intersection = (pred_flat * target_flat).sum()
    return 1.0 - (2.0 * intersection + eps) / (pred_flat.sum() + target_flat.sum() + eps)


def segmentation_loss(
    pred: torch.Tensor,
    target: torch.Tensor,
    *,
    bce_weight: float = 0.5,
    dice_weight: float = 0.5,
) -> torch.Tensor:
    """Combined BCE + Dice loss for training the segmentation model.

    Parameters
    ----------
    pred:
        Probability map ``(B, 1, H, W)`` in ``[0, 1]``.
    target:
        Binary ground-truth ``(B, 1, H, W)`` in ``{0, 1}``.
    bce_weight:
        Weight for the binary cross-entropy term.
    dice_weight:
        Weight for the Dice term.

    Returns
    -------
    torch.Tensor
        Scalar combined loss.
    """
    bce = F.binary_cross_entropy(pred, target.float())
    d_loss = dice_loss(pred, target)
    return bce_weight * bce + dice_weight * d_loss


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


def segmentation_iou(pred: torch.Tensor, target: torch.Tensor) -> float:
    """Compute IoU for binary segmentation tensors.

    Parameters
    ----------
    pred:
        Predicted binary mask tensor (bool or float thresholded).
    target:
        Ground-truth binary mask tensor.

    Returns
    -------
    float
        IoU in ``[0, 1]``.
    """
    pred_bool = pred.bool()
    target_bool = target.bool()
    intersection = int((pred_bool & target_bool).sum().item())
    union = int((pred_bool | target_bool).sum().item())
    if union == 0:
        return 1.0
    return intersection / union
