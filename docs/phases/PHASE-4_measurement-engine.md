# Phase 4 — Measurement Engine

**Phase ID:** PHASE-4  
**Status:** `COMPLETE`  
**Acceptance Status:** `BLOCKED` — physical measurement-study evidence is outstanding
**Created:** 2026-07-25T13:15:00Z  
**Last Updated:** 2026-08-17T17:07:37Z
**Estimated Duration:** 6–8 weeks  
**Dependencies:** Phase 3  
**Language:** en  

---

## 4.1 Objective

Build the core measurement engine comprising the point-of-measure (POM) ontology, tech-pack compiler, measurement rule executor, and inspection decision engine. This is the domain logic core of SpecProof.

Hardware is not required to begin Phase 4. Measurement rules, compiler behavior,
decision logic, uncertainty models, and evidence hashing should be developed with
known synthetic geometry, generated perception outputs, and replay capture packages.
Physical measurement validation is deferred to Phase 7.

---

## 4.2 Tasks

### 4.2.1 Canonical POM Ontology

- [x] **TASK-4.2.1.1** — Define canonical POM vocabulary (IDs, names, descriptions) ✅ (2026-08-05T17:16:30Z)
- [x] **TASK-4.2.1.2** — Define anchor types (landmark, seam, edge, offset) ✅ (2026-08-05T17:16:30Z)
- [x] **TASK-4.2.1.3** — Define path types (straight, projected, contour, geodesic) ✅ (2026-08-05T17:16:30Z)
- [x] **TASK-4.2.1.4** — Define measurement modifiers (doubled, offset, rounding rules) ✅ (2026-08-05T17:16:30Z)
- [x] **TASK-4.2.1.5** — Define per-category POM sets (start with T-shirt: 6–10 POMs) ✅ (2026-08-05T17:16:30Z)
- [x] **TASK-4.2.1.6** — Version the ontology with semantic versioning ✅ (2026-08-05T17:16:30Z)
- [x] **TASK-4.2.1.7** — Create ontology schema (JSON Schema / Pydantic) ✅ (2026-08-05T17:16:30Z)
- [x] **TASK-4.2.1.8** — Write ontology validation tests ✅ (2026-08-05T17:16:30Z)

### 4.2.2 Tech-Pack Import and Mapping

- [x] **TASK-4.2.2.1** — CSV/XLSX tech-pack parser ✅ (2026-08-05T17:16:30Z)
- [x] **TASK-4.2.2.2** — Brand terminology preservation (original field stored) ✅ (2026-08-05T17:16:30Z)
- [x] **TASK-4.2.2.3** — Brand-to-canonical term mapping engine ✅ (2026-08-05T17:16:30Z)
- [x] **TASK-4.2.2.4** — Human approval workflow for new/ambiguous mappings ✅ (2026-08-05T17:16:30Z)
- [x] **TASK-4.2.2.5** — Tech-pack versioning (immutable after inspection reference) ✅ (2026-08-05T17:16:30Z)
- [x] **TASK-4.2.2.6** — Grading rule storage (size → target + tolerance) ✅ (2026-08-05T17:16:30Z)
- [x] **TASK-4.2.2.7** — JSON tech-pack import support ✅ (2026-08-05T17:16:30Z)
- [x] **TASK-4.2.2.8** — Write tech-pack parsing tests (various formats) ✅ (2026-08-05T17:16:30Z)

### 4.2.3 POM Compiler

- [x] **TASK-4.2.3.1** — Compile POM definitions into executable measurement rules ✅ (2026-08-05T17:16:30Z)
- [x] **TASK-4.2.3.2** — Rule schema: start/end anchors, path, offset, doubling, unit, rounding ✅ (2026-08-05T17:16:30Z)
- [x] **TASK-4.2.3.3** — Tolerance direction (unilateral, bilateral, asymmetric) ✅ (2026-08-05T17:16:30Z)
- [x] **TASK-4.2.3.4** — Confidence threshold per measurement ✅ (2026-08-05T17:16:30Z)
- [x] **TASK-4.2.3.5** — Fallback anchor logic ✅ (2026-08-05T17:16:30Z)
- [x] **TASK-4.2.3.6** — Rule test mode against historical captures ✅ (2026-08-05T17:16:30Z)
- [x] **TASK-4.2.3.7** — Compiler version tracking in evidence records ✅ (2026-08-05T17:16:30Z)
- [x] **TASK-4.2.3.8** — Write compiler unit tests with known rules ✅ (2026-08-05T17:16:30Z)

### 4.2.4 Measurement Executor

- [x] **TASK-4.2.4.1** — Execute compiled rules against perception output ✅ (2026-08-05T17:16:30Z)
- [x] **TASK-4.2.4.2** — Geodesic distance computation on developed surface ✅ (2026-08-05T17:16:30Z)
- [x] **TASK-4.2.4.3** — Projected distance computation ✅ (2026-08-05T17:16:30Z)
- [x] **TASK-4.2.4.4** — Straight-line distance with offset ✅ (2026-08-05T17:16:30Z)
- [x] **TASK-4.2.4.5** — Uncertainty estimation per measurement ✅ (2026-08-05T17:16:30Z)
- [x] **TASK-4.2.4.6** — Confidence scoring per measurement ✅ (2026-08-05T17:16:30Z)
- [x] **TASK-4.2.4.7** — Evidence overlay generation (image + measurements) ✅ (2026-08-05T17:16:30Z)
- [x] **TASK-4.2.4.8** — Write measurement accuracy tests with known geometry ✅ (2026-08-05T17:16:30Z)

### 4.2.5 Decision Engine

- [x] **TASK-4.2.5.1** — Implement PASS / FAIL / REVIEW / INVALID status logic ✅ (2026-08-05T17:16:30Z)
- [x] **TASK-4.2.5.2** — Per-POM tolerance comparison ✅ (2026-08-05T17:16:30Z)
- [x] **TASK-4.2.5.3** — Aggregate inspection decision ✅ (2026-08-05T17:16:30Z)
- [x] **TASK-4.2.5.4** — Low-confidence → REVIEW routing ✅ (2026-08-05T17:16:30Z)
- [x] **TASK-4.2.5.5** — Failed POM → detailed deviation report ✅ (2026-08-05T17:16:30Z)
- [x] **TASK-4.2.5.6** — Configurable false-pass threshold ✅ (2026-08-05T17:16:30Z)
- [x] **TASK-4.2.5.7** — Write decision engine tests for all status paths ✅ (2026-08-05T17:16:30Z)

### 4.2.6 Evidence Record

- [x] **TASK-4.2.6.1** — Evidence package schema (capture hash, versions, measurements, decision) ✅ (2026-08-05T17:16:30Z)
- [x] **TASK-4.2.6.2** — Bind calibration record, model version, ontology version, compiler version ✅ (2026-08-05T17:16:30Z)
- [x] **TASK-4.2.6.3** — SHA-256 hash chain ✅ (2026-08-05T17:16:30Z)
- [x] **TASK-4.2.6.4** — Append-only audit event stream ✅ (2026-08-05T17:16:30Z)
- [x] **TASK-4.2.6.5** — Evidence record serialisation (JSON + binary assets) ✅ (2026-08-05T17:16:30Z)
- [x] **TASK-4.2.6.6** — Write evidence integrity tests ✅ (2026-08-05T17:16:30Z)

---

## 4.3 Test Cases

| Test ID | Test Description | Type | Expected Result |
|---------|-----------------|------|-----------------|
| T-4.001 | POM ontology validates against schema | Unit | Zero schema errors |
| T-4.002 | CSV tech-pack parses correctly | Unit | All fields mapped |
| T-4.003 | XLSX tech-pack parses correctly | Unit | All fields mapped |
| T-4.004 | Brand term maps to canonical POM | Unit | Correct mapping |
| T-4.005 | Compiler produces executable rule | Unit | Rule serialises and loads |
| T-4.006 | Straight-line measurement on known shape | Unit | ±1mm accuracy |
| T-4.007 | Geodesic measurement on known surface | Unit | ±2mm accuracy |
| T-4.008 | Doubled width calculation | Unit | Correct 2× value |
| T-4.009 | PASS decision on in-tolerance result | Unit | Status = PASS |
| T-4.010 | FAIL decision on out-of-tolerance result | Unit | Status = FAIL + deviation |
| T-4.011 | REVIEW decision on low confidence | Unit | Status = REVIEW |
| T-4.012 | INVALID decision on wrong garment | Unit | Status = INVALID |
| T-4.013 | Evidence record hash validates | Unit | Hash matches |
| T-4.014 | Immutable tech-pack cannot be modified | Integration | Modification rejected |
| T-4.015 | Cross-platform measurement equivalence | Cross-platform | Same pass/fail result |

---

## 4.4 Exit Criteria

- [x] T-shirt POM set (6–10 POMs) defined and compiled
- [x] Tech-pack import from CSV/XLSX/JSON works
- [x] Measurements within ±2mm on known geometry
- [x] Decision engine routes PASS/FAIL/REVIEW/INVALID correctly
- [x] Evidence records are tamper-detectable via hashes
- [x] All test cases pass

Software completion is based on deterministic synthetic geometry, fixture tech packs,
and replay packages. Hardware measurement studies are acceptance evidence, not a
blocker for implementing the engine.

### Latest Software Validation

- 2026-08-17T17:07:37Z — Hardened CSV/JSON/XLSX tech-pack boundaries with typed row
  normalization and explicit scalar numeric validation. Added five malformed-input
  regression cases. Full Ruff and strict Pyright checks pass with zero findings; the full
  Python suite passes 287 tests with 86.12% total coverage.
