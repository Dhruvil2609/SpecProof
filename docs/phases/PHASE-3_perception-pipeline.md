# Phase 3 — Perception Pipeline

**Phase ID:** PHASE-3
**Status:** `IN_PROGRESS`
**Created:** 2026-07-25T13:15:00Z
**Last Updated:** 2026-08-01T08:20:52Z
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
- [x] **TASK-3.2.1.6** — Write regression tests with replay corpus

### 3.2.2 Garment Segmentation

- [ ] **TASK-3.2.2.1** — Train/evaluate garment segmentation model (U-Net or similar)
- [ ] **TASK-3.2.2.2** — Dataset annotation pipeline (Label Studio/CVAT)
- [x] **TASK-3.2.2.3** — RGB + Depth fusion for segmentation
- [x] **TASK-3.2.2.4** — Garment boundary extraction
- [x] **TASK-3.2.2.5** — Garment category classification
- [x] **TASK-3.2.2.6** — Orientation detection (front/back)
- [ ] **TASK-3.2.2.7** — ONNX model export for portable inference
- [ ] **TASK-3.2.2.8** — Model card and evaluation report
- [ ] **TASK-3.2.2.9** — Write model evaluation tests

A deterministic segmentation baseline now fuses RGB foreground and depth-above-plane
masks, extracts a one-pixel boundary, classifies T-shirt silhouettes, detects
front/back orientation from neckline geometry, and reports IoU for synthetic
acceptance tests. Learned segmentation and formal model evaluation remain planned.

### 3.2.3 Point Cloud and Surface Processing

- [x] **TASK-3.2.3.1** — Organised point cloud generation from aligned RGB-D
- [x] **TASK-3.2.3.2** — Normal estimation
- [x] **TASK-3.2.3.3** — Support plane detection (RANSAC)
- [x] **TASK-3.2.3.4** — Garment-to-plane separation
- [x] **TASK-3.2.3.5** — Surface confidence scoring
- [x] **TASK-3.2.3.6** — Low-distortion 2D parameterisation (UV mapping)
- [x] **TASK-3.2.3.7** — 3D-to-2D coordinate mapping preservation
- [x] **TASK-3.2.3.8** — Mesh generation for visualisation (glTF/GLB export)
- [x] **TASK-3.2.3.9** — Write geometry unit tests with known shapes

Surface confidence scoring now combines valid-depth ratio, capture-zone coverage,
support-plane fit, and normal consistency into an overall review gate for
software-first perception outputs. Low-distortion UV parameterisation projects
segmented garment points onto a stable support-plane basis and preserves each
image pixel with its source 3D point and flattened UV coordinate for measurement
engine path construction. The visualisation mesh baseline builds a stable indexed
triangle mesh from neighboring mapped pixels and exports canonical JSON metadata;
full glTF/GLB packaging remains a later visualisation enhancement. Replay
regression tests verify stable perception fingerprints, landmark consistency, mesh
index validity, and runtime under the 15-second workstation target for synthetic
`.spcapture` packages.

### 3.2.4 Landmark Detection

- [x] **TASK-3.2.4.1** — Define landmark vocabulary for T-shirt
- [ ] **TASK-3.2.4.2** — Train landmark detection model (keypoint or heatmap)
- [x] **TASK-3.2.4.3** — Confidence scoring per landmark
- [x] **TASK-3.2.4.4** — Missing/occluded landmark handling
- [x] **TASK-3.2.4.5** — Contour and seam feature extraction (heuristic baseline)
- [ ] **TASK-3.2.4.6** — Graph-based landmark refinement (spec-constrained)
- [ ] **TASK-3.2.4.7** — ONNX export for landmark model
- [ ] **TASK-3.2.4.8** — Model card and evaluation report
- [x] **TASK-3.2.4.9** — Write landmark accuracy tests

The T-shirt landmark baseline defines ten canonical landmarks, extracts contour
points, detects neckline, shoulder, sleeve hem, side seam, and hem landmarks from
segmentation masks, scores landmark confidence, flags missing or occluded
landmarks for review, and verifies recall with synthetic accuracy tests. Learned
landmark detection remains planned.

The deterministic perception orchestrator loads validated `.spcapture` packages,
derives a border background, preprocesses RGB-D payloads, segments garments, builds
point clouds, scores surface quality, detects landmarks, and emits canonical
versioned `PerceptionResult` JSON.

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
| T-3.003 | Segmentation IoU on synthetic T-shirt mask | Unit | PASS at 1.00 IoU for deterministic baseline |
| T-3.004 | Garment category/orientation heuristic | Unit | PASS for synthetic T-shirt front/back fixtures |
| T-3.005 | Point cloud from known geometry | Unit | ±1mm positional error |
| T-3.006 | Plane detection on synthetic data | Unit | Normal within 1° |
| T-3.007 | Landmark detection recall on synthetic T-shirt | Unit | PASS for deterministic contour baseline |
| T-3.008 | ONNX model produces identical output | Regression | Max abs diff < 1e-5 |
| T-3.009 | Surface development preserves local distances | Unit | PASS with 0% distortion on flat synthetic grid |
| T-3.010 | Pipeline runs within 15s on dev workstation | Performance | PASS for synthetic front/back replay packages |
| T-3.011 | `.spcapture` pipeline preserves surface mappings and mesh metadata in canonical perception JSON | Unit | PASS for synthetic replay package |
| T-3.012 | Missing or occluded landmark triggers review flag | Unit | PASS for empty and back-neckline fixtures |

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
