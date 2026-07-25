# Phase 2 — Capture Station Core

**Phase ID:** PHASE-2  
**Status:** `NOT_STARTED`  
**Created:** 2026-07-25T13:15:00Z  
**Last Updated:** 2026-07-25T13:15:00Z  
**Estimated Duration:** 4–6 weeks  
**Dependencies:** Phase 1  
**Language:** en  

---

## 2.1 Objective

Build the RGB-D camera integration, calibration system, capture workflow, and station agent that form the physical measurement foundation. The capture service runs natively on Windows, communicating with the platform via gRPC or local HTTP.

---

## 2.2 Tasks

### 2.2.1 Camera Provider Implementation

- [ ] **TASK-2.2.1.1** — Implement `ICameraProvider` for RealSense on Windows
- [ ] **TASK-2.2.1.2** — Device enumeration by serial number
- [ ] **TASK-2.2.1.3** — Stream profile configuration (RGB + Depth)
- [ ] **TASK-2.2.1.4** — Intrinsics and extrinsics retrieval
- [ ] **TASK-2.2.1.5** — Depth scale retrieval
- [ ] **TASK-2.2.1.6** — Aligned RGB-D capture
- [ ] **TASK-2.2.1.7** — Recording and replay (.bag files)
- [ ] **TASK-2.2.1.8** — Health check and error recovery
- [ ] **TASK-2.2.1.9** — USB disconnect/reconnect handling
- [ ] **TASK-2.2.1.10** — Write unit tests with mock camera
- [ ] **TASK-2.2.1.11** — Write integration tests with replay data

### 2.2.2 Calibration System

- [ ] **TASK-2.2.2.1** — Camera intrinsic verification module
- [ ] **TASK-2.2.2.2** — RGB-to-depth alignment verification
- [ ] **TASK-2.2.2.3** — Camera-to-capture-plane extrinsic calibration
- [ ] **TASK-2.2.2.4** — Scale verification using calibration artefact
- [ ] **TASK-2.2.2.5** — Flatness and orientation checks
- [ ] **TASK-2.2.2.6** — Lighting uniformity verification
- [ ] **TASK-2.2.2.7** — Calibration record storage (version, date, expiry, operator)
- [ ] **TASK-2.2.2.8** — Daily quick-check vs full calibration modes
- [ ] **TASK-2.2.2.9** — Calibration expiry enforcement
- [ ] **TASK-2.2.2.10** — Write calibration regression tests

### 2.2.3 Capture Workflow

- [ ] **TASK-2.2.3.1** — Live preview pipeline (15–30 FPS)
- [ ] **TASK-2.2.3.2** — Capture zone framing validation
- [ ] **TASK-2.2.3.3** — Multi-frame capture and fusion
- [ ] **TASK-2.2.3.4** — Platform-neutral capture package format
- [ ] **TASK-2.2.3.5** — Capture package checksums (SHA-256)
- [ ] **TASK-2.2.3.6** — Capture metadata (station, camera, timestamp UTC, environment)
- [ ] **TASK-2.2.3.7** — Capture storage to object store (MinIO)
- [ ] **TASK-2.2.3.8** — Write capture workflow E2E tests

### 2.2.4 Station Agent

- [ ] **TASK-2.2.4.1** — Python service with gRPC interface
- [ ] **TASK-2.2.4.2** — Station registration and identity
- [ ] **TASK-2.2.4.3** — Health reporting (camera, USB, storage, clock)
- [ ] **TASK-2.2.4.4** — Offline capture queue
- [ ] **TASK-2.2.4.5** — Synchronisation with platform API
- [ ] **TASK-2.2.4.6** — Structured JSON logging
- [ ] **TASK-2.2.4.7** — OpenTelemetry metrics export
- [ ] **TASK-2.2.4.8** — Write station agent tests

### 2.2.5 Capture Replay Corpus

- [ ] **TASK-2.2.5.1** — Create versioned replay corpus structure
- [ ] **TASK-2.2.5.2** — Record valid captures
- [ ] **TASK-2.2.5.3** — Record edge cases (low-light, reflective, black fabric, missing depth)
- [ ] **TASK-2.2.5.4** — Record calibration-expired scenarios
- [ ] **TASK-2.2.5.5** — Record corrupted/interrupted files
- [ ] **TASK-2.2.5.6** — Write corpus validation tests

---

## 2.3 Test Cases

| Test ID | Test Description | Type | Expected Result |
|---------|-----------------|------|-----------------|
| T-2.001 | Camera enumerates by serial number | Unit | Device info returned |
| T-2.002 | Aligned RGB-D frames captured | Integration | Both streams present |
| T-2.003 | Intrinsics match expected values | Regression | Within tolerance |
| T-2.004 | Depth scale is physically correct | Calibration | ±0.1% of spec |
| T-2.005 | Capture package format is platform-neutral | Unit | Loads on Win+Linux |
| T-2.006 | SHA-256 checksum validates | Unit | Hash matches |
| T-2.007 | Capture survives USB disconnect | Integration | Graceful recovery |
| T-2.008 | Calibration expiry blocks capture | Integration | Capture refused |
| T-2.009 | Offline captures queue and sync later | E2E | All captures delivered |
| T-2.010 | 30-minute stability run | Stress | Zero dropped frames |
| T-2.011 | Replay corpus loads on both platforms | Cross-platform | Identical outputs |
| T-2.012 | Station health endpoint returns valid JSON | Unit | Schema validates |

---

## 2.4 Exit Criteria

- [ ] Camera captures aligned RGB-D frames reliably
- [ ] Calibration system stores versioned records
- [ ] Capture packages are platform-neutral and checksummed
- [ ] Station agent runs, reports health, and syncs offline captures
- [ ] 30-minute stability test passes
- [ ] All test cases pass on Windows; replay tests pass on Linux
