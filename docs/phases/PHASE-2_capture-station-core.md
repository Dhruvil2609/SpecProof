# Phase 2 — Capture Station Core

**Phase ID:** PHASE-2  
**Status:** `IN_PROGRESS`
**Created:** 2026-07-25T13:15:00Z  
**Last Updated:** 2026-07-28T16:34:20Z
**Estimated Duration:** 4–6 weeks  
**Dependencies:** Phase 1 foundation; hardware acceptance depends on Phase 0 workstation remediation
**Language:** en

## 2.1 Objective

Build the versioned RGB-D capture boundary, camera adapters, calibration records, capture packages, offline station queue, and platform synchronization foundation. Native RealSense access remains in Python; the .NET station host supervises it through gRPC.

## 2.2 Tasks

### 2.2.1 Camera Provider Implementation

- [x] **TASK-2.2.1.1** — Implement RealSense camera provider for Windows
- [x] **TASK-2.2.1.2** — Device enumeration by serial number
- [x] **TASK-2.2.1.3** — Stream profile configuration for RGB and depth
- [x] **TASK-2.2.1.4** — Intrinsics and extrinsics retrieval
- [x] **TASK-2.2.1.5** — Depth scale retrieval
- [x] **TASK-2.2.1.6** — Aligned RGB-D capture
- [x] **TASK-2.2.1.7** — Recording and replay adapters
- [x] **TASK-2.2.1.8** — Health checks, bounded retry, and error mapping
- [x] **TASK-2.2.1.9** — Disconnect and reconnect state handling
- [x] **TASK-2.2.1.10** — Unit tests with mock camera
- [ ] **TASK-2.2.1.11** — Integration tests with physical `.bag` replay data

Implementation is complete for the adapter boundary. RealSense hardware behavior remains blocked pending a D435-class camera, qualified SDK, USB 3 connection, and hardware-in-loop execution.

### 2.2.2 Calibration System

- [ ] **TASK-2.2.2.1** — Camera intrinsic verification module
- [ ] **TASK-2.2.2.2** — RGB-to-depth alignment verification
- [ ] **TASK-2.2.2.3** — Camera-to-capture-plane extrinsic calibration
- [ ] **TASK-2.2.2.4** — Scale verification using calibration artefact
- [ ] **TASK-2.2.2.5** — Flatness and orientation checks
- [ ] **TASK-2.2.2.6** — Lighting uniformity verification
- [x] **TASK-2.2.2.7** — Immutable calibration record storage
- [x] **TASK-2.2.2.8** — Daily quick-check and full calibration modes
- [x] **TASK-2.2.2.9** — Calibration expiry enforcement
- [x] **TASK-2.2.2.10** — Calibration record and threshold regression tests

The service exposes calibration workflows and enforces validity. Physical metric evaluators are intentionally unavailable until artefact geometry and hardware fixtures can be validated.

### 2.2.3 Capture Workflow

- [x] **TASK-2.2.3.1** — Latest-frame bounded preview stream
- [ ] **TASK-2.2.3.2** — Capture zone framing validation
- [x] **TASK-2.2.3.3** — Configurable multi-frame capture and median depth fusion
- [x] **TASK-2.2.3.4** — ZIP64 `.spcapture` package format
- [x] **TASK-2.2.3.5** — Payload and package SHA-256 checksums
- [x] **TASK-2.2.3.6** — Canonical UTC capture metadata
- [x] **TASK-2.2.3.7** — MinIO/S3 object-storage abstraction and asset records
- [ ] **TASK-2.2.3.8** — Full capture workflow E2E test against running services

### 2.2.4 Station Agent

- [x] **TASK-2.2.4.1** — Versioned Python gRPC service and generated C# client
- [x] **TASK-2.2.4.2** — Station identity and credential-store abstractions
- [x] **TASK-2.2.4.3** — Camera, storage, clock, and queue health reporting
- [x] **TASK-2.2.4.4** — Durable SQLite offline capture queue
- [x] **TASK-2.2.4.5** — Idempotent platform and object-store synchronization
- [x] **TASK-2.2.4.6** — Structured JSON logging
- [x] **TASK-2.2.4.7** — OpenTelemetry metrics and OTLP export configuration
- [x] **TASK-2.2.4.8** — Station agent unit and service tests

### 2.2.5 Capture Replay Corpus

- [x] **TASK-2.2.5.1** — Versioned replay corpus structure and scenario manifest
- [ ] **TASK-2.2.5.2** — Record valid hardware captures
- [ ] **TASK-2.2.5.3** — Record low-light, reflective, black-fabric, and missing-depth cases
- [ ] **TASK-2.2.5.4** — Record calibration-expired scenarios
- [ ] **TASK-2.2.5.5** — Record corrupted and interrupted packages
- [ ] **TASK-2.2.5.6** — Cross-platform corpus validation tests

Real recordings and `.spcapture` packages must use Git LFS. Synthetic metadata fixtures remain normal Git files.

## 2.3 Contract and Data Rules

- `packages/station-contracts/proto/v1/capture_station.proto` is the authoritative IPC contract.
- Missing cameras map to `NOT_FOUND`; invalid calibration maps to `FAILED_PRECONDITION`; unavailable SDKs, disconnects, and I/O failures map to `UNAVAILABLE`.
- Default streams are RGB `1280×720@30` and depth `848×480@30`, aligned depth-to-colour.
- Captures use 5 frames by default and accept 3–15 frames.
- `.spcapture` files contain canonical UTF-8 metadata, lossless RGB/depth payloads, camera geometry, per-frame metadata, and checksums.
- Package publication is atomic after checksum verification.
- PostgreSQL stores capture metadata only; binary payloads belong in object storage.
- Development PostgreSQL credentials are local-only: `Username=Admin;Password=Admin@123`.

## 2.4 Verification Evidence

| Test | Status | Evidence |
|------|--------|----------|
| Mock enumeration and aligned frames | PASS | Python unit tests |
| Calibration threshold and expiry enforcement | PASS | Python unit and gRPC service tests |
| Capture fusion and package checksums | PASS | Python package round-trip tests |
| Queue idempotency, retry, and restart recovery | PASS | SQLite unit tests |
| gRPC list, health, preview, capture, calibration, recording | PASS | Direct service tests |
| Python quality gate | PASS | Ruff, Pyright, 58 tests, 80.15% total coverage |
| .NET station client and platform API build | PASS | Release build, zero warnings |
| PostgreSQL forward/rollback/audit behavior | BLOCKED | Docker daemon unavailable locally; CI test is configured |
| MinIO upload integration | BLOCKED | Docker daemon unavailable locally |
| Windows RealSense hardware tests | BLOCKED | Camera and qualified SDK unavailable |
| Linux replay compatibility | BLOCKED | Linux runner not executed locally |
| 30-minute stability run | BLOCKED | Physical hardware unavailable |

## 2.5 Exit Criteria

- [ ] RealSense captures aligned RGB-D frames reliably on qualified Windows hardware
- [x] Calibration records are immutable, versioned, and expiry-enforced
- [x] Capture packages are platform-neutral, atomic, and checksummed
- [x] Station agent reports health and recovers durable queue state
- [ ] PostgreSQL and MinIO integration tests pass against running services
- [ ] Physical calibration evaluators pass known-artefact acceptance thresholds
- [ ] USB disconnect/reconnect hardware test passes
- [ ] 30-minute zero-failure stability test passes
- [ ] Replay tests pass on Linux and Windows

Phase 2 remains `IN_PROGRESS` until all blocked integration, cross-platform, and hardware acceptance gates pass.
