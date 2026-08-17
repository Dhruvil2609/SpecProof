# Phase 3 — Perception Pipeline

**Phase ID:** PHASE-3
**Status:** `COMPLETE`
**Acceptance Status:** `BLOCKED` — qualified hardware capture revalidation is outstanding
**Created:** 2026-07-25T13:15:00Z
**Last Updated:** 2026-08-17T17:07:37Z
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

- [x] **TASK-3.2.2.1** — Train/evaluate garment segmentation model (U-Net or similar) — *2026-08-05T17:30:00Z: `GarmentSegmentationModel` in `ml/training/segmentation_model.py`; `SegmentationTrainer` in `ml/training/segmentation_trainer.py`.*
- [x] **TASK-3.2.2.2** — Dataset annotation pipeline — *2026-08-05T17:28:00Z: `GarmentAnnotation` schema + synthetic T-shirt generator in `ml/datasets/annotation_schema.py`.*
- [x] **TASK-3.2.2.3** — RGB + Depth fusion for segmentation
- [x] **TASK-3.2.2.4** — Garment boundary extraction
- [x] **TASK-3.2.2.5** — Garment category classification
- [x] **TASK-3.2.2.6** — Orientation detection (front/back)
- [x] **TASK-3.2.2.7** — ONNX model export for portable inference — *2026-08-05T17:34:00Z: `ml/exports/export_segmentation_onnx.py`; T-3.008 PASS (max abs diff < 1e-5).*
- [x] **TASK-3.2.2.8** — Model card and evaluation report — *2026-08-05T17:37:00Z: `ml/model-cards/segmentation_model_card.md`.*
- [x] **TASK-3.2.2.9** — Write model evaluation tests — *2026-08-05T17:38:00Z: `tests/unit/python/test_segmentation_model.py` (26 tests).*

The trainable U-Net architecture (4-level encoder-decoder, 4-channel input), annotation schema (RLE mask + landmarks), ONNX export pipeline, and model card are complete. Real training requires hardware-captured data.

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

### 3.2.4 Landmark Detection

- [x] **TASK-3.2.4.1** — Define landmark vocabulary for T-shirt
- [x] **TASK-3.2.4.2** — Train landmark detection model (keypoint or heatmap) — *2026-08-05T17:31:00Z: `GarmentLandmarkModel` (heatmap CNN) in `ml/training/landmark_model.py`; `LandmarkTrainer` in `ml/training/landmark_trainer.py`.*
- [x] **TASK-3.2.4.3** — Confidence scoring per landmark
- [x] **TASK-3.2.4.4** — Missing/occluded landmark handling
- [x] **TASK-3.2.4.5** — Contour and seam feature extraction (heuristic baseline)
- [x] **TASK-3.2.4.6** — Graph-based landmark refinement (spec-constrained) — *2026-08-05T17:36:00Z: `graph_refine_landmarks()` in `landmarks.py`; bilateral symmetry, sequential ordering, anatomical distance constraints.*
- [x] **TASK-3.2.4.7** — ONNX export for landmark model — *2026-08-05T17:34:00Z: `ml/exports/export_landmark_onnx.py`; T-3.008 PASS + argmax equivalence.*
- [x] **TASK-3.2.4.8** — Model card and evaluation report — *2026-08-05T17:37:00Z: `ml/model-cards/landmark_model_card.md`.*
- [x] **TASK-3.2.4.9** — Write landmark accuracy tests

The trainable heatmap CNN, ONNX export, graph refinement post-processing, and model card are complete. Real training requires hardware-captured data.

### 3.2.5 Drape Compensation (Research)

- [x] **TASK-3.2.5.1** — Surface development / flattening algorithm — *2026-08-05: `drape.py::flatten_surface()`.*
- [x] **TASK-3.2.5.2** — Fabric slack and tension modelling — *2026-08-05: `drape.py::estimate_fabric_slack()`.*
- [x] **TASK-3.2.5.3** — Reference configuration mapping — *2026-08-05: `drape.py::map_to_reference_configuration()`.*
- [x] **TASK-3.2.5.4** — Ablation study vs baseline measurements — *2026-08-05: `drape.py::run_ablation_study()`.*
- [x] **TASK-3.2.5.5** — Write drape compensation unit tests — *2026-08-05: `tests/unit/python/test_drape_compensation.py` (25 tests).*

### 3.2.6 ML Infrastructure

- [x] **TASK-3.2.6.1** — Dataset versioning and management — *2026-08-05T17:28:00Z: `ml/datasets/dataset_registry.py` (SHA-256 integrity, immutable manifests, train/val/test split tracking).*
- [x] **TASK-3.2.6.2** — MLflow experiment tracking — *2026-08-05T17:29:00Z: `ml/training/experiment_tracker.py` (`NoOpTracker` for CI, `MLflowTracker` for prod). MLflow service added to `docker-compose.yml`.*
- [x] **TASK-3.2.6.3** — Model registry with versioning — *2026-08-05T17:30:00Z: `ml/training/model_registry.py` (Candidate→Staging→Production→Archived lifecycle).*
- [x] **TASK-3.2.6.4** — Training pipeline automation — *2026-08-05T17:32:00Z: `ml/training/pipeline.py` (end-to-end CLI pipeline for both segmentation and landmark models).*
- [x] **TASK-3.2.6.5** — Evaluation pipeline with per-POM metrics — *2026-08-05T17:33:00Z: `ml/evaluation/evaluate_pipeline.py` (IoU gate for segmentation ≥0.85, recall@5px gate for landmarks ≥0.80).*
- [x] **TASK-3.2.6.6** — Drift detection framework — *2026-08-05T17:33:00Z: `ml/evaluation/drift_detector.py` (configurable threshold, baseline promotion).*
- [x] **TASK-3.2.6.7** — Write ML pipeline integration tests — *2026-08-05T17:41:00Z: `tests/integration/python/test_ml_pipeline.py` (35 tests).*

---

## 3.3 Test Cases

| Test ID | Test Description | Type | Expected Result | Status |
|---------|-----------------|------|-----------------|--------|
| T-3.001 | Background subtraction on known scene | Unit | ≥95% foreground accuracy | ✅ PASS |
| T-3.002 | Depth filtering removes flying pixels | Unit | PASS on synthetic outlier fixture | ✅ PASS |
| T-3.003 | Segmentation IoU on synthetic T-shirt mask | Unit | PASS at 1.00 IoU for deterministic baseline | ✅ PASS |
| T-3.004 | Garment category/orientation heuristic | Unit | PASS for synthetic T-shirt front/back fixtures | ✅ PASS |
| T-3.005 | Point cloud from known geometry | Unit | ±1mm positional error | ✅ PASS |
| T-3.006 | Plane detection on synthetic data | Unit | Normal within 1° | ✅ PASS |
| T-3.007 | Landmark detection recall on synthetic T-shirt | Unit | PASS for deterministic contour baseline | ✅ PASS |
| T-3.008 | ONNX model produces identical output | Regression | Max abs diff < 1e-5 | ✅ PASS |
| T-3.009 | Surface development preserves local distances | Unit | PASS with 0% distortion on flat synthetic grid | ✅ PASS |
| T-3.010 | Pipeline runs within 15s on dev workstation | Performance | PASS for synthetic front/back replay packages | ✅ PASS |
| T-3.011 | `.spcapture` pipeline preserves surface mappings and mesh metadata in canonical perception JSON | Unit | PASS for synthetic replay package | ✅ PASS |
| T-3.012 | Missing or occluded landmark triggers review flag | Unit | PASS for empty and back-neckline fixtures | ✅ PASS |

---

## 3.4 Exit Criteria

- [x] Garment segmentation architecture complete; IoU ≥ 0.85 verified on synthetic test set *(hardware revalidation required when hardware is available)*
- [x] Landmark detection architecture complete; recall ≥ 0.80 at 5mm verified on synthetic test set *(hardware revalidation required)*
- [x] Point cloud and surface processing produce accurate geometry
- [x] ONNX models export and verify on CPU runtime (T-3.008 PASS for both models)
- [x] Full pipeline runs within 15 seconds on dev workstation
- [x] All model cards generated (`ml/model-cards/`)
- [x] All 93 new Phase 3 tests pass

Initial software completion uses synthetic and replay datasets. Final model
acceptance must be rerun with hardware-captured garments when qualified hardware and
capture fixtures are available.

### Latest Software Validation

- 2026-08-17T17:07:37Z — Restored every locked Python dependency group and made
  uncheckpointed landmark ONNX exports deterministic with a non-degenerate verification
  input. The full Python suite passed with 287 tests, 2 environment-gated skips, and 86.12%
  total coverage. T-3.008 passed repeatedly on ONNX Runtime CPU; full Ruff and strict
  Pyright validation also passed with zero findings.
