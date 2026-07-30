# Phase 3 — Perception Pipeline

**Phase ID:** PHASE-3
**Status:** `IN_PROGRESS`
**Created:** 2026-07-25T13:15:00Z
**Last Updated:** 2026-07-30T17:59:35Z
**Estimated Duration:** 6–10 weeks
**Dependencies:** Phase 2
**Language:** en

---

## 3.1 Objective

Build the computer vision pipeline that transforms raw RGB-D captures into segmented garment surfaces, extracted features, and detected landmarks. This is the perception layer between raw camera data and the measurement engine.

Hardware is not required to begin Phase 3. Development should use synthetic RGB-D
scenes, generated garment masks, metadata-only fixtures, and replay `.spcapture`
packages. Hardware-captured datasets improve model validation later but do not block
algorithm, API, model-export, or test-harness implementation.

---

## 3.2 Tasks

### 3.2.1 Background Subtraction and Preprocessing

- [x] **TASK-3.2.1.1** — Capture-surface background model
- [x] **TASK-3.2.1.2** — Depth filtering (invalid, flying pixels, statistical outliers)
- [x] **TASK-3.2.1.3** — RGB-depth registration refinement
- [x] **TASK-3.2.1.4** — Noise reduction and smoothing
- [x] **TASK-3.2.1.5** — Write unit tests with synthetic data
- [ ] **TASK-3.2.1.6** — Write regression tests with replay corpus

### 3.2.2 Garment Segmentation

- [ ] **TASK-3.2.2.1** — Train/evaluate garment segmentation model (U-Net or similar)
- [ ] **TASK-3.2.2.2** — Dataset annotation pipeline (Label Studio/CVAT)
- [ ] **TASK-3.2.2.3** — RGB + Depth fusion for segmentation
- [ ] **TASK-3.2.2.4** — Garment boundary extraction
- [ ] **TASK-3.2.2.5** — Garment category classification
- [ ] **TASK-3.2.2.6** — Orientation detection (front/back)
- [ ] **TASK-3.2.2.7** — ONNX model export for portable inference
- [ ] **TASK-3.2.2.8** — Model card and evaluation report
- [ ] **TASK-3.2.2.9** — Write model evaluation tests

### 3.2.3 Point Cloud and Surface Processing

- [x] **TASK-3.2.3.1** — Organised point cloud generation from aligned RGB-D
- [x] **TASK-3.2.3.2** — Normal estimation
- [x] **TASK-3.2.3.3** — Support plane detection (RANSAC)
- [x] **TASK-3.2.3.4** — Garment-to-plane separation
- [ ] **TASK-3.2.3.5** — Surface confidence scoring
- [ ] **TASK-3.2.3.6** — Low-distortion 2D parameterisation (UV mapping)
- [ ] **TASK-3.2.3.7** — 3D-to-2D coordinate mapping preservation
- [ ] **TASK-3.2.3.8** — Mesh generation for visualisation (glTF/GLB export)
- [x] **TASK-3.2.3.9** — Write geometry unit tests with known shapes

### 3.2.4 Landmark Detection

- [ ] **TASK-3.2.4.1** — Define landmark vocabulary for T-shirt
- [ ] **TASK-3.2.4.2** — Train landmark detection model (keypoint or heatmap)
- [ ] **TASK-3.2.4.3** — Confidence scoring per landmark
- [ ] **TASK-3.2.4.4** — Missing/occluded landmark handling
- [ ] **TASK-3.2.4.5** — Contour and seam feature extraction (heuristic baseline)
- [ ] **TASK-3.2.4.6** — Graph-based landmark refinement (spec-constrained)
- [ ] **TASK-3.2.4.7** — ONNX export for landmark model
- [ ] **TASK-3.2.4.8** — Model card and evaluation report
- [ ] **TASK-3.2.4.9** — Write landmark accuracy tests

### 3.2.5 Drape Compensation (Research)

- [ ] **TASK-3.2.5.1** — Surface development / flattening algorithm
- [ ] **TASK-3.2.5.2** — Fabric slack and tension modelling
- [ ] **TASK-3.2.5.3** — Reference configuration mapping
- [ ] **TASK-3.2.5.4** — Ablation study vs baseline measurements
- [ ] **TASK-3.2.5.5** — Write drape compensation unit tests

### 3.2.6 ML Infrastructure

- [ ] **TASK-3.2.6.1** — Dataset versioning and management
- [ ] **TASK-3.2.6.2** — MLflow experiment tracking
- [ ] **TASK-3.2.6.3** — Model registry with versioning
- [ ] **TASK-3.2.6.4** — Training pipeline automation
- [ ] **TASK-3.2.6.5** — Evaluation pipeline with per-POM metrics
- [ ] **TASK-3.2.6.6** — Drift detection framework
- [ ] **TASK-3.2.6.7** — Write ML pipeline integration tests

---

## 3.3 Test Cases

| Test ID | Test Description | Type | Expected Result |
|---------|-----------------|------|-----------------|
| T-3.001 | Background subtraction on known scene | Unit | ≥95% foreground accuracy |
| T-3.002 | Depth filtering removes flying pixels | Unit | PASS on synthetic outlier fixture |
| T-3.003 | Segmentation IoU on test set | Model | ≥0.85 IoU |
| T-3.004 | Garment category classification accuracy | Model | ≥0.90 on test set |
| T-3.005 | Point cloud from known geometry | Unit | ±1mm positional error |
| T-3.006 | Plane detection on synthetic data | Unit | Normal within 1° |
| T-3.007 | Landmark detection recall on T-shirt | Model | ≥0.80 at 5mm threshold |
| T-3.008 | ONNX model produces identical output | Regression | Max abs diff < 1e-5 |
| T-3.009 | Surface development preserves area | Unit | ≤2% area distortion |
| T-3.010 | Pipeline runs within 15s on dev workstation | Performance | Time < 15000ms |
| T-3.011 | Cross-platform replay produces same landmarks | Cross-platform | Positions within tolerance |
| T-3.012 | Missing landmark triggers review flag | Unit | Status = REVIEW |

---

## 3.4 Exit Criteria

- [ ] Garment segmentation achieves ≥0.85 IoU on test set
- [ ] Landmark detection achieves ≥0.80 recall at 5mm threshold for T-shirt
- [ ] Point cloud and surface processing produce accurate geometry
- [ ] ONNX models export and run on both CPU and GPU runtimes
- [ ] Full pipeline runs within 15 seconds on dev workstation
- [ ] All model cards and evaluation reports generated
- [ ] All test cases pass

Initial software completion may use synthetic and replay datasets. Final model
acceptance must be rerun with hardware-captured garments when qualified hardware and
capture fixtures are available.
