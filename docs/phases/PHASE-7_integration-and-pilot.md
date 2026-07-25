# Phase 7 — Integration and Pilot

**Phase ID:** PHASE-7  
**Status:** `NOT_STARTED`  
**Created:** 2026-07-25T13:15:00Z  
**Last Updated:** 2026-07-25T13:15:00Z  
**Estimated Duration:** 6–8 weeks  
**Dependencies:** Phase 6  
**Language:** en  

---

## 7.1 Objective

Integrate all components end-to-end, run comprehensive system tests, conduct the measurement validation study, and prepare for factory pilot deployment.

---

## 7.2 Tasks

### 7.2.1 End-to-End Integration

- [ ] **TASK-7.2.1.1** — Wire camera → perception → measurement → decision → evidence pipeline
- [ ] **TASK-7.2.1.2** — Wire station agent → platform API → web UI data flow
- [ ] **TASK-7.2.1.3** — Offline capture → sync → display workflow
- [ ] **TASK-7.2.1.4** — Multi-station concurrent operation test
- [ ] **TASK-7.2.1.5** — Write end-to-end integration tests

### 7.2.2 Measurement Validation Study

- [ ] **TASK-7.2.2.1** — Define study protocol (≥30 garments, ≥3 operators, ≥3 placements)
- [ ] **TASK-7.2.2.2** — Collect manual reference measurements
- [ ] **TASK-7.2.2.3** — Run automated measurements
- [ ] **TASK-7.2.2.4** — Compute repeatability (same placement std dev ≤2mm)
- [ ] **TASK-7.2.2.5** — Compute reproducibility (diff operators ≤4mm 95%)
- [ ] **TASK-7.2.2.6** — Compute agreement with manual (MAE ≤5mm)
- [ ] **TASK-7.2.2.7** — Report per POM, not aggregated
- [ ] **TASK-7.2.2.8** — Generate Gauge R&R report

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
- [ ] Measurement validation study meets POC targets
- [ ] <15s processing on dev workstation
- [ ] Resilience tests pass (power, network, crash recovery)
- [ ] Cross-platform replay produces equivalent results
- [ ] Pilot documentation complete
- [ ] All test cases pass
