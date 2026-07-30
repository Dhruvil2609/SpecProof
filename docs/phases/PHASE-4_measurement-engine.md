# Phase 4 — Measurement Engine

**Phase ID:** PHASE-4  
**Status:** `NOT_STARTED`  
**Created:** 2026-07-25T13:15:00Z  
**Last Updated:** 2026-07-30T17:19:06Z
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

- [ ] **TASK-4.2.1.1** — Define canonical POM vocabulary (IDs, names, descriptions)
- [ ] **TASK-4.2.1.2** — Define anchor types (landmark, seam, edge, offset)
- [ ] **TASK-4.2.1.3** — Define path types (straight, projected, contour, geodesic)
- [ ] **TASK-4.2.1.4** — Define measurement modifiers (doubled, offset, rounding rules)
- [ ] **TASK-4.2.1.5** — Define per-category POM sets (start with T-shirt: 6–10 POMs)
- [ ] **TASK-4.2.1.6** — Version the ontology with semantic versioning
- [ ] **TASK-4.2.1.7** — Create ontology schema (JSON Schema / Pydantic)
- [ ] **TASK-4.2.1.8** — Write ontology validation tests

### 4.2.2 Tech-Pack Import and Mapping

- [ ] **TASK-4.2.2.1** — CSV/XLSX tech-pack parser
- [ ] **TASK-4.2.2.2** — Brand terminology preservation (original field stored)
- [ ] **TASK-4.2.2.3** — Brand-to-canonical term mapping engine
- [ ] **TASK-4.2.2.4** — Human approval workflow for new/ambiguous mappings
- [ ] **TASK-4.2.2.5** — Tech-pack versioning (immutable after inspection reference)
- [ ] **TASK-4.2.2.6** — Grading rule storage (size → target + tolerance)
- [ ] **TASK-4.2.2.7** — JSON tech-pack import support
- [ ] **TASK-4.2.2.8** — Write tech-pack parsing tests (various formats)

### 4.2.3 POM Compiler

- [ ] **TASK-4.2.3.1** — Compile POM definitions into executable measurement rules
- [ ] **TASK-4.2.3.2** — Rule schema: start/end anchors, path, offset, doubling, unit, rounding
- [ ] **TASK-4.2.3.3** — Tolerance direction (unilateral, bilateral, asymmetric)
- [ ] **TASK-4.2.3.4** — Confidence threshold per measurement
- [ ] **TASK-4.2.3.5** — Fallback anchor logic
- [ ] **TASK-4.2.3.6** — Rule test mode against historical captures
- [ ] **TASK-4.2.3.7** — Compiler version tracking in evidence records
- [ ] **TASK-4.2.3.8** — Write compiler unit tests with known rules

### 4.2.4 Measurement Executor

- [ ] **TASK-4.2.4.1** — Execute compiled rules against perception output
- [ ] **TASK-4.2.4.2** — Geodesic distance computation on developed surface
- [ ] **TASK-4.2.4.3** — Projected distance computation
- [ ] **TASK-4.2.4.4** — Straight-line distance with offset
- [ ] **TASK-4.2.4.5** — Uncertainty estimation per measurement
- [ ] **TASK-4.2.4.6** — Confidence scoring per measurement
- [ ] **TASK-4.2.4.7** — Evidence overlay generation (image + measurements)
- [ ] **TASK-4.2.4.8** — Write measurement accuracy tests with known geometry

### 4.2.5 Decision Engine

- [ ] **TASK-4.2.5.1** — Implement PASS / FAIL / REVIEW / INVALID status logic
- [ ] **TASK-4.2.5.2** — Per-POM tolerance comparison
- [ ] **TASK-4.2.5.3** — Aggregate inspection decision
- [ ] **TASK-4.2.5.4** — Low-confidence → REVIEW routing
- [ ] **TASK-4.2.5.5** — Failed POM → detailed deviation report
- [ ] **TASK-4.2.5.6** — Configurable false-pass threshold
- [ ] **TASK-4.2.5.7** — Write decision engine tests for all status paths

### 4.2.6 Evidence Record

- [ ] **TASK-4.2.6.1** — Evidence package schema (capture hash, versions, measurements, decision)
- [ ] **TASK-4.2.6.2** — Bind calibration record, model version, ontology version, compiler version
- [ ] **TASK-4.2.6.3** — SHA-256 hash chain
- [ ] **TASK-4.2.6.4** — Append-only audit event stream
- [ ] **TASK-4.2.6.5** — Evidence record serialisation (JSON + binary assets)
- [ ] **TASK-4.2.6.6** — Write evidence integrity tests

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

- [ ] T-shirt POM set (6–10 POMs) defined and compiled
- [ ] Tech-pack import from CSV/XLSX/JSON works
- [ ] Measurements within ±2mm on known geometry
- [ ] Decision engine routes PASS/FAIL/REVIEW/INVALID correctly
- [ ] Evidence records are tamper-detectable via hashes
- [ ] All test cases pass

Software completion is based on deterministic synthetic geometry, fixture tech packs,
and replay packages. Hardware measurement studies are acceptance evidence, not a
blocker for implementing the engine.
