# Phase 7 — Integration and Pilot

**Phase ID:** PHASE-7  
**Status:** `IN_PROGRESS`
**Created:** 2026-07-25T13:15:00Z  
**Last Updated:** 2026-08-15T07:40:34Z
**Estimated Duration:** 6–8 weeks  
**Dependencies:** Phase 6  
**Language:** en  

---

## 7.1 Objective

Integrate all components end-to-end, run comprehensive system tests, conduct the measurement validation study, and prepare for factory pilot deployment.

Before hardware is available, Phase 7 should run a software integration track using
mock capture services, replay packages, synthetic garments, seeded platform data, and
Docker infrastructure. The physical measurement validation study, camera crash tests,
operator study, and factory pilot remain deferred hardware acceptance activities.

---

## 7.2 Tasks

### 7.2.1 End-to-End Integration

- [x] **TASK-7.2.1.1** — Wire camera → perception → measurement → decision → evidence pipeline
- [x] **TASK-7.2.1.2** — Wire station agent → platform API → web UI data flow
- [x] **TASK-7.2.1.3** — Offline capture → sync → display workflow
- [x] **TASK-7.2.1.4** — Multi-station concurrent operation test
- [x] **TASK-7.2.1.5** — Write end-to-end integration tests

### 7.2.2 Measurement Validation Study

- [x] **TASK-7.2.2.1** — Define study protocol (≥30 garments, ≥3 operators, ≥3 placements)
- [ ] **TASK-7.2.2.2** — Collect manual reference measurements
- [ ] **TASK-7.2.2.3** — Run automated measurements
- [x] **TASK-7.2.2.4** — Compute repeatability (same placement std dev ≤2mm)
- [x] **TASK-7.2.2.5** — Compute reproducibility (diff operators ≤4mm 95%)
- [x] **TASK-7.2.2.6** — Compute agreement with manual (MAE ≤5mm)
- [x] **TASK-7.2.2.7** — Report per POM, not aggregated
- [x] **TASK-7.2.2.8** — Generate Gauge R&R report

Study protocol, data schemas, analysis scripts, report templates, and synthetic dry
runs can be completed before hardware arrives. Real data collection and acceptance
statistics require physical hardware and garments.

### 7.2.3 Performance Optimisation

- [ ] **TASK-7.2.3.1** — Profile full pipeline end-to-end
- [ ] **TASK-7.2.3.2** — Optimise to <5s per garment where feasible
- [ ] **TASK-7.2.3.3** — GPU inference optimisation
- [ ] **TASK-7.2.3.4** — Database query optimisation
- [ ] **TASK-7.2.3.5** — Write performance benchmark tests

### 7.2.4 Resilience Testing

- [ ] **TASK-7.2.4.1** — Power loss recovery test
- [ ] **TASK-7.2.4.2** — Network disconnection during sync
- [ ] **TASK-7.2.4.3** — Database unavailability handling
- [ ] **TASK-7.2.4.4** — Camera crash recovery
- [ ] **TASK-7.2.4.5** — Concurrent user stress test
- [ ] **TASK-7.2.4.6** — Write chaos/resilience tests

### 7.2.5 Cross-Platform Validation

- [ ] **TASK-7.2.5.1** — All replay tests pass on both Windows and Linux
- [ ] **TASK-7.2.5.2** — Measurement results within tolerance cross-platform
- [ ] **TASK-7.2.5.3** — Docker container deployment test
- [ ] **TASK-7.2.5.4** — Linux installer/package test
- [ ] **TASK-7.2.5.5** — Write cross-platform regression suite

### 7.2.6 Pilot Preparation

- [ ] **TASK-7.2.6.1** — Operator training materials
- [ ] **TASK-7.2.6.2** — Support runbooks
- [ ] **TASK-7.2.6.3** — Station deployment checklist
- [ ] **TASK-7.2.6.4** — Monitoring and alerting setup
- [ ] **TASK-7.2.6.5** — Backup and restore procedure
- [ ] **TASK-7.2.6.6** — Incident response plan

---

## 7.3 Test Cases

| Test ID | Test Description | Type | Expected Result |
|---------|-----------------|------|-----------------|
| T-7.001 | Full E2E: capture → result in <15s | E2E | Time < 15000ms |
| T-7.002 | Measurement repeatability ≤2mm std dev | Validation | Per POM passes |
| T-7.003 | Measurement reproducibility ≤4mm 95% | Validation | Per POM passes |
| T-7.004 | Manual agreement MAE ≤5mm | Validation | Per POM passes |
| T-7.005 | Power loss recovery preserves data | Resilience | Zero lost inspections |
| T-7.006 | Network loss queues and syncs | Resilience | All records delivered |
| T-7.007 | 3 stations run concurrently | Stress | No data corruption |
| T-7.008 | Cross-platform same pass/fail result | Cross-platform | Results match |
| T-7.009 | Docker deployment starts cleanly | Deployment | Health check passes |
| T-7.010 | Backup and restore produces valid state | Resilience | Data integrity verified |

---

## 7.4 Exit Criteria

- [ ] Full pipeline runs end-to-end without manual intervention
- [ ] Software E2E pipeline runs with mock/replay capture data
- [ ] Measurement validation study meets POC targets on hardware-captured data
- [ ] <15s processing on dev workstation
- [ ] Resilience tests pass (power, network, crash recovery)
- [ ] Cross-platform replay produces equivalent results
- [ ] Pilot documentation complete
- [ ] All test cases pass

Software integration can be completed before hardware. Pilot readiness and measurement
validation remain deferred until qualified capture hardware and garments are available.

---

## 7.5 Implementation Evidence

- 2026-08-15T06:43:40Z — Added the typed local `InspectionPipeline` contract and
  orchestrator for validated `.spcapture` context, perception, compiled rules,
  measurement execution, decision routing, sealed evidence, canonical platform payloads,
  and monotonic per-stage timings. Appended backward-compatible inspection context,
  inspection ID, and processing status fields to the station gRPC contract. Focused
  integration and gRPC validation: 13 tests passed. TASK-7.2.1.1 remains open until the
  capture service invokes this pipeline automatically.
- 2026-08-15T06:52:18Z — Added a separate durable SQLite inspection-result queue
  with immutable canonical payload hashes, capture/inspection idempotency, pending,
  submitting, retryable-failure, dead-letter, and completed states, bounded exponential
  retry, process-restart recovery, manual dead-letter requeue, capture-upload gating, and
  authenticated HTTP result submission. Focused queue and capture validation: 20 tests
  passed. TASK-7.2.1.3 remains open until the operator-visible display flow is connected.
- 2026-08-15T07:08:10Z — Expanded platform inspection submission with canonical
  evidence and tech-pack version bindings. Added consistent tenant, station, capture,
  inspection, status, measurement, and hash validation; evidence signing; one-transaction
  inspection, evidence, audit, and report-job persistence; identical replay; and conflicting
  replay detection. Release build passed with zero warnings, 24 platform tests and 16 data
  tests passed, and 7 integrated Python tests passed. The real PostgreSQL test is checked in
  and gated by `SPEC_PROOF_RUN_DATABASE_INTEGRATION=1`; runtime execution remains pending
  because Docker is stopped.
- 2026-08-15T07:27:58Z — Connected operator order/style/size/batch and immutable
  tech-pack context through Station Host and gRPC, executed the local pipeline after capture,
  durably persisted results before acknowledgement, added optional background capture/result
  delivery, returned real inspection IDs/status, and replaced the UI timer with translated
  polling, retry, offline, and timeout states. Added a versioned offline tech-pack fixture,
  integrated gRPC acknowledgement test, and concurrent three-station identity/isolation test.
  Validation passed: 19 Python tests, zero-warning .NET release build, and 11 operator tests
  with lint/typecheck. Runtime Docker acceptance remains open.
- 2026-08-15T07:40:34Z — Added `specproof-validation-study` with versioned garment,
  POM, operator, placement, repeat, manual, and automated schemas; controlled CSV input;
  normalized Zstandard Parquet output; and JSON/HTML per-POM reports. Statistics include
  same-placement standard deviation, operator P95 reproducibility, bias, MAE,
  Bland–Altman limits, false-pass/fail rates, and crossed Gauge R&R variance components.
  Added deterministic passing/failing fixtures, three tests, a ≥30 garment/≥3 operator/≥3
  placement protocol, and collection template. Physical collection tasks remain deferred.
