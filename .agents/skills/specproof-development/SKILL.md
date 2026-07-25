---
name: specproof-development
description: Master skill for SpecProof AI Codex development. ALWAYS ACTIVE for every SpecProof task — code, test, fix, refactor, document, review, deploy, database, frontend, backend, Python, .NET, TypeScript, camera, measurement, perception, calibration, infrastructure. Defines mandatory rules, conventions, and workflow for all development phases.
---

# SpecProof AI Codex Development Skill

You are an AI Codex agent developing the SpecProof garment measurement system. Follow these rules for ALL development work.

## Project Context

SpecProof is a hardware+software system for automated garment measurement using RGB-D cameras. It combines calibrated capture, 3D geometry, machine learning, and a trust/audit layer. Read the full requirements in:
- `SpecProof_Project_Requirements_and_Analysis.md`
- `SpecProof_Development_Environment_Requirements.md`

## Mandatory Rules

### 1. Production-Grade Code
- Write production-quality code — no placeholders, no TODOs, no shortcuts
- All code must be type-safe, well-documented, and follow project coding standards
- See `docs/standards/CODING-STANDARDS.md` for language-specific rules

### 2. Automatic Test Cases
- **Every feature, function, or fix MUST include automated tests**
- Unit tests for all business logic (≥80% coverage for domain logic)
- Integration tests for service boundaries
- Regression tests for measurement accuracy
- Follow test strategy in `docs/testing/TEST-STRATEGY.md`

### 3. UTC Timestamps
- All timestamps MUST be UTC
- Python: `datetime.now(timezone.utc)` — never naive datetimes
- .NET: `DateTime.UtcNow` or `DateTimeOffset.UtcNow` — never `DateTime.Now`
- TypeScript: `new Date().toISOString()`
- Database: `timestamptz` columns
- Logs: UTC only

### 4. Multi-Language Support (i18n)
- All user-facing strings MUST use i18n translation keys
- Never hardcode display text
- Default language: English (`en`)
- Follow `docs/i18n/I18N-STRATEGY.md`

### 5. Progress Tracking
- After completing work, update `docs/tracking/PROGRESS.md`
- Mark completed tasks with `[x]` in the relevant phase document
- Add entries to `docs/tracking/CHANGELOG.md`
- Record the UTC timestamp of completion

### 6. Cross-Platform
- Use `Path.Combine` (.NET), `pathlib.Path` (Python)
- No hardcoded drive letters, no OS-specific paths in domain code
- Platform-specific code behind interfaces (see Section 4 of dev env doc)
- Test on both Windows and Linux runners

### 7. Architecture
- Follow abstraction boundaries: `ICameraProvider`, `ICalibrationProvider`, `IMeasurementEngine`, etc.
- Domain logic is platform-independent
- Platform-dependent code is isolated
- Use dependency injection

### 8. Data Formats
- JSON/MessagePack for contracts
- PNG/TIFF for lossless images
- PLY/PCD for point clouds
- glTF/GLB for meshes
- Parquet for analytical data
- UTF-8 without BOM for text

## Workflow for Each Task

1. **Read the phase document** — find your task in `docs/phases/PHASE-N_*.md`
2. **Read relevant references** — check requirements docs and existing code
3. **Implement** — write production-grade code following standards
4. **Write tests** — create automated tests covering the implementation
5. **Verify** — run tests and ensure they pass
6. **Update tracking** — mark task complete, update progress, add changelog entry
7. **Document** — add/update API docs, docstrings, and comments

## Phase Documents

- `docs/phases/PHASE-0_development-environment-setup.md`
- `docs/phases/PHASE-1_project-foundation.md`
- `docs/phases/PHASE-2_capture-station-core.md`
- `docs/phases/PHASE-3_perception-pipeline.md`
- `docs/phases/PHASE-4_measurement-engine.md`
- `docs/phases/PHASE-5_platform-and-trust-layer.md`
- `docs/phases/PHASE-6_web-application.md`
- `docs/phases/PHASE-7_integration-and-pilot.md`
- `docs/phases/PHASE-8_production-hardening.md`

## Key Reference Documents

- `docs/standards/CODING-STANDARDS.md`
- `docs/testing/TEST-STRATEGY.md`
- `docs/i18n/I18N-STRATEGY.md`
- `docs/tracking/PROGRESS.md`
- `docs/tracking/CHANGELOG.md`
- `docs/tracking/DECISIONS.md`
