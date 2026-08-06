# Garment Segmentation Model Card

**Model ID:** `garment-segmentation`
**Version:** Phase 3 deterministic baseline + trainable U-Net
**Status:** Architecture complete; training pending hardware-captured dataset
**Language:** en
**Schema Version:** 1

---

## Model Details

| Field | Value |
|-------|-------|
| Architecture | U-Net encoder-decoder with skip connections |
| Input | (B, 4, H, W) — RGB (3 ch) + normalised depth (1 ch) |
| Output | (B, 1, H, W) — sigmoid garment probability map |
| Encoder depth | 4 levels, base channels = 16 |
| Parameters | ~120K (base_channels=16) |
| ONNX opset | 17 |
| Framework | PyTorch ≥ 2.7 |

## Intended Use

The model segments the garment silhouette from an aligned RGB-D capture
frame.  The output binary mask is consumed by:

- Point cloud and surface processing (`point_cloud.py`, `surface.py`)
- Surface parameterisation (`parameterization.py`)
- Landmark detection (`landmarks.py`)
- Measurement path construction (Phase 4)

The model must not be used for any purpose outside garment measurement on
SpecProof-calibrated capture stations.

## Training Data

| Split | Expected source |
|-------|----------------|
| Train | Hardware-captured T-shirt garments on SpecProof station |
| Val   | Hold-out hardware captures with human annotations |
| Test  | Separate hold-out set (never used during training) |

**Current baseline:** Deterministic RGB-D fusion (no learned weights).
Full training requires hardware-captured annotations produced by the
annotation pipeline (`ml/datasets/annotation_schema.py`).

## Evaluation Metrics

| Metric | Baseline (deterministic) | Exit criterion |
|--------|--------------------------|----------------|
| IoU (synthetic T-shirt) | 1.00 | ≥ 0.85 on test set |
| IoU (hardware captures) | Pending | ≥ 0.85 on test set |

> **Note:** The 1.00 IoU on the synthetic baseline uses deterministic
> fusion of a known mask; this does not represent real-world accuracy.
> Hardware-captured evaluation must be completed before the phase exits.

## Performance

- **Target latency:** < 15 s end-to-end pipeline on dev workstation (CPU)
- **Current baseline:** Within budget on synthetic captures (T-3.010 PASS)

## Limitations

1. Trained only on T-shirt silhouettes — other garment types not supported.
2. Requires calibrated capture zone; performance degrades outside spec.
3. Fails on heavily occluded garments or multi-garment scenes.
4. Hardware-captured performance not yet verified.

## Ethical Considerations

- No biometric data: images contain only garments, not people.
- All data collected via SpecProof-controlled stations.

## Contact

SpecProof development team — https://specproof.co.uk/
