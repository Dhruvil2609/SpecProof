"""Garment annotation schema and synthetic dataset generator.

This module defines the canonical JSON annotation format for garment
segmentation and landmark labelling, plus a synthetic data generator
that produces deterministic T-shirt fixtures for training and evaluation
without requiring hardware-captured images.

Annotation Format
-----------------
Each annotation file is a UTF-8 JSON document conforming to
``GarmentAnnotation``.  It may be produced by human annotators (e.g.
Label Studio / CVAT export) or by the synthetic generator in this module.

Synthetic Generator
-------------------
``generate_synthetic_tshirt_dataset()`` creates a set of PNG+JSON pairs
representing flat T-shirt silhouettes at varying scales and orientations.
All synthetic data is deterministic (seeded RNG) and self-contained.
"""

from __future__ import annotations

import hashlib
import json
import random
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Annotation schema
# ---------------------------------------------------------------------------


class AnnotationPoint(BaseModel):
    """Image-space coordinate in pixels (origin = top-left)."""

    x: float
    y: float


class MaskRLE(BaseModel):
    """Run-length encoded binary mask (COCO RLE format).

    The ``counts`` list alternates between background and foreground run
    lengths, starting with the background count, in column-major order.
    """

    width: int
    height: int
    counts: list[int]


class LandmarkAnnotation(BaseModel):
    """One annotated landmark keypoint."""

    name: str
    point: AnnotationPoint
    visibility: int = Field(
        ge=0,
        le=2,
        description="0=not labelled, 1=occluded, 2=visible",
    )
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)


class GarmentAnnotation(BaseModel):
    """Canonical annotation record for one garment capture frame.

    This is the schema written by annotators and consumed by the training
    pipeline.  Synthetic records use ``annotator_id='synthetic'``.
    """

    annotation_id: str
    capture_id: str
    station_id: str
    frame_index: int = 0
    image_width: int
    image_height: int
    category: str = Field(description="Garment category, e.g. 't_shirt'")
    orientation: str = Field(description="'front' or 'back'")
    mask: MaskRLE
    landmarks: list[LandmarkAnnotation] = Field(default_factory=list)
    annotator_id: str = "synthetic"
    schema_version: int = 1
    annotated_at_utc: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_canonical_json(self) -> str:
        """Return canonical UTF-8 JSON with sorted keys."""
        return json.dumps(
            self.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )

    def mask_as_array(self) -> np.ndarray:
        """Decode the RLE mask to a boolean HxW NumPy array."""
        return _rle_decode(self.mask)


# ---------------------------------------------------------------------------
# Synthetic dataset generator
# ---------------------------------------------------------------------------

_TSHIRT_LANDMARKS = [
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
]


def generate_synthetic_tshirt_dataset(
    output_dir: Path,
    *,
    count: int = 20,
    seed: int = 42,
    image_width: int = 640,
    image_height: int = 480,
) -> list[Path]:
    """Generate a set of synthetic T-shirt annotation JSON files.

    Each record describes a procedurally generated flat T-shirt silhouette
    at a random scale and position within the frame.  All data is
    deterministic given the same ``seed`` and ``count``.

    Parameters
    ----------
    output_dir:
        Directory to write annotation JSON files.  Created if absent.
    count:
        Number of annotation records to generate.
    seed:
        Random seed for reproducibility.
    image_width:
        Synthetic image width in pixels.
    image_height:
        Synthetic image height in pixels.

    Returns
    -------
    list[Path]
        Paths to the generated annotation JSON files.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    np_rng = np.random.default_rng(seed)
    paths: list[Path] = []

    for i in range(count):
        annotation_id = f"synthetic-tshirt-{i:04d}"
        orientation = "front" if i % 2 == 0 else "back"
        mask_array = _generate_tshirt_mask(
            np_rng, image_width, image_height, orientation=orientation
        )
        rle = _rle_encode(mask_array)
        landmarks = _generate_landmarks(mask_array, orientation)
        ann = GarmentAnnotation(
            annotation_id=annotation_id,
            capture_id=f"cap-{i:04d}",
            station_id="synthetic",
            image_width=image_width,
            image_height=image_height,
            category="t_shirt",
            orientation=orientation,
            mask=rle,
            landmarks=landmarks,
            annotator_id="synthetic",
            annotated_at_utc=datetime(2026, 1, 1, tzinfo=UTC),
            metadata={"generator": "specproof-synthetic-v1", "index": str(i)},
        )
        out_path = output_dir / f"{annotation_id}.json"
        out_path.write_text(ann.to_canonical_json(), encoding="utf-8", newline="\n")
        paths.append(out_path)

    return paths


# ---------------------------------------------------------------------------
# Dataset split utilities
# ---------------------------------------------------------------------------


def split_annotations(
    annotation_paths: list[Path],
    *,
    train_ratio: float = 0.7,
    val_ratio: float = 0.15,
    seed: int = 42,
) -> dict[str, list[Path]]:
    """Split annotation paths into train/val/test subsets.

    Parameters
    ----------
    annotation_paths:
        Full list of annotation file paths.
    train_ratio:
        Fraction assigned to training (default 0.7).
    val_ratio:
        Fraction assigned to validation (default 0.15).
    seed:
        Shuffle seed for reproducibility.

    Returns
    -------
    dict with keys ``'train'``, ``'val'``, ``'test'``.
    """
    if train_ratio + val_ratio >= 1.0:
        raise ValueError("train_ratio + val_ratio must be < 1.0")
    paths = sorted(annotation_paths)
    rng = random.Random(seed)
    rng.shuffle(paths)
    n = len(paths)
    n_train = int(n * train_ratio)
    n_val = int(n * val_ratio)
    return {
        "train": paths[:n_train],
        "val": paths[n_train : n_train + n_val],
        "test": paths[n_train + n_val :],
    }


def compute_annotation_checksum(annotation_path: Path) -> str:
    """Return the SHA-256 hex digest of an annotation file."""
    return hashlib.sha256(annotation_path.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _generate_tshirt_mask(
    rng: np.random.Generator,
    width: int,
    height: int,
    *,
    orientation: str,
) -> np.ndarray:
    """Generate a synthetic T-shirt binary mask (HxW bool array)."""
    mask = np.zeros((height, width), dtype=np.bool_)

    # Body rectangle
    bw = int(width * rng.uniform(0.35, 0.55))
    bh = int(height * rng.uniform(0.55, 0.75))
    bx = (width - bw) // 2 + int(rng.uniform(-width * 0.05, width * 0.05))
    by = int(height * 0.15)
    mask[by : by + bh, bx : bx + bw] = True

    # Sleeves (horizontal bars at the top)
    sw = int(width * rng.uniform(0.12, 0.20))
    sh = int(bh * rng.uniform(0.18, 0.26))
    # Left sleeve
    lx = max(0, bx - sw)
    mask[by : by + sh, lx : bx] = True
    # Right sleeve
    rx = bx + bw
    mask[by : by + sh, rx : rx + sw] = True

    # Neckline cutout (front = deeper, back = shallower)
    neck_depth = int(bh * (0.12 if orientation == "front" else 0.05))
    neck_width = int(bw * 0.35)
    nx = bx + (bw - neck_width) // 2
    mask[by : by + neck_depth, nx : nx + neck_width] = False

    return mask


def _rle_encode(mask: np.ndarray) -> MaskRLE:
    """Encode a boolean HxW mask as column-major RLE."""
    height, width = mask.shape
    flat = mask.flatten(order="F").astype(np.uint8)
    counts: list[int] = []
    current = 0
    run = 0
    for pixel in flat:
        if pixel == current:
            run += 1
        else:
            counts.append(run)
            run = 1
            current = pixel
    counts.append(run)
    # RLE must start with background count
    if flat[0] == 1:
        counts.insert(0, 0)
    return MaskRLE(width=width, height=height, counts=counts)


def _rle_decode(rle: MaskRLE) -> np.ndarray:
    """Decode a MaskRLE to a boolean HxW NumPy array."""
    flat = np.zeros(rle.width * rle.height, dtype=np.bool_)
    pos = 0
    current = False
    for run in rle.counts:
        flat[pos : pos + run] = current
        pos += run
        current = not current
    return flat.reshape(rle.height, rle.width, order="F")


def _generate_landmarks(mask: np.ndarray, orientation: str) -> list[LandmarkAnnotation]:
    """Generate plausible landmark annotations from a mask."""
    from specproof_measurement_service.landmarks import detect_tshirt_landmarks

    landmark_set = detect_tshirt_landmarks(mask)
    annotations: list[LandmarkAnnotation] = []
    for lm in landmark_set.landmarks:
        from specproof_measurement_service.landmarks import LandmarkStatus

        visibility = 2 if lm.status == LandmarkStatus.DETECTED else 0
        annotations.append(
            LandmarkAnnotation(
                name=lm.name.value,
                point=AnnotationPoint(x=lm.x, y=lm.y),
                visibility=visibility,
                confidence=lm.confidence,
            )
        )
    return annotations
