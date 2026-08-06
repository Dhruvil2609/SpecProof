# Garment Landmark Detection Model Card

**Model ID:** `garment-landmark`
**Version:** Phase 3 deterministic baseline + trainable heatmap CNN
**Status:** Architecture complete; training pending hardware-captured dataset
**Language:** en
**Schema Version:** 1

---

## Model Details

| Field | Value |
|-------|-------|
| Architecture | Heatmap CNN with residual encoder + bilinear decoder |
| Input | (B, 4, H, W) — RGB (3 ch) + normalised depth (1 ch) |
| Output | (B, 10, H, W) — per-landmark Gaussian heatmaps in [0, 1] |
| Landmarks | 10 (canonical T-shirt vocabulary) |
| Body depth | 4 residual blocks, base channels = 32 |
| ONNX opset | 17 |
| Framework | PyTorch ≥ 2.7 |

## Landmark Vocabulary

| Index | Name | Description |
|-------|------|-------------|
| 0 | `neck_left` | Left edge of neckline opening |
| 1 | `neck_right` | Right edge of neckline opening |
| 2 | `shoulder_left` | Outermost left shoulder point |
| 3 | `shoulder_right` | Outermost right shoulder point |
| 4 | `sleeve_hem_left` | Left sleeve cuff edge |
| 5 | `sleeve_hem_right` | Right sleeve cuff edge |
| 6 | `side_seam_left` | Left side seam at widest body point |
| 7 | `side_seam_right` | Right side seam at widest body point |
| 8 | `hem_left` | Bottom-left hem corner |
| 9 | `hem_right` | Bottom-right hem corner |

## Landmark Decoding

Predictions are decoded by computing `argmax` over each heatmap channel
and converting the flat index to `(x, y)` image coordinates.  A peak
value below `confidence_threshold` (default 0.1) is reported as
`not detected`.

## Graph Refinement

The post-processing step `graph_refine_landmarks()` enforces:
1. Bilateral symmetry between paired landmarks.
2. Monotonic top-to-bottom ordering along each side seam.
3. Anatomical distance constraints (11 pairs, with min/max in mm).

## Intended Use

Landmark coordinates feed the measurement path construction stage in the
Phase 4 measurement engine.  Do not use for garment styles other than
T-shirts without retraining and re-evaluation.

## Training Data

| Split | Expected source |
|-------|----------------|
| Train | Hardware-captured T-shirts with landmark annotations |
| Val   | Hold-out annotated captures |
| Test  | Separate hold-out set |

**Current baseline:** Deterministic contour heuristics (no learned weights).

## Evaluation Metrics

| Metric | Baseline | Exit criterion |
|--------|----------|----------------|
| Recall@5mm (synthetic) | PASS (deterministic baseline) | ≥ 0.80 on test set |
| Recall@5mm (hardware) | Pending | ≥ 0.80 on test set |

## Performance

- **Target:** < 15 s end-to-end pipeline (shared with full perception pipeline)

## Limitations

1. Designed for flat T-shirt garments only.
2. Heatmap resolution is constrained by stride-2 downsampling.
3. Occluded landmarks are reported as `not detected`.
4. Hardware performance not yet verified.

## Contact

SpecProof development team — https://specproof.co.uk/
