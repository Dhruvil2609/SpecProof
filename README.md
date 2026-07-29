# SpecProof

SpecProof is a hardware and software system for automated garment measurement using RGB-D cameras, calibrated capture, 3D geometry, machine learning, and auditable decision records.

## Development Setup

Phases 0, 1, and 2 are in progress. Follow
`documentation/DEVELOPMENT-RUNBOOK.md` for the complete workstation setup, workspace
validation, full local startup order, and remaining manual acceptance steps. Detailed
Phase 0 host remediation is documented in `docs/setup/PHASE-0-WINDOWS.md`, and
reproducible local diagnostics are provided by `specproof-doctor`.

## Repository Layout

- `apps/` - station host, capture service, measurement service, APIs, and UIs.
- `packages/` - shared contracts, geometry, calibration, POM, measurement, decision, and evidence modules.
- `infra/` - local Docker, compose, monitoring, Windows, and Linux infrastructure assets.
- `ml/` - datasets, annotations, training, evaluation, exports, and model cards.
- `tools/` - developer and operator tools, including `specproof-doctor`.
- `tests/` - unit, integration, contract, regression, cross-platform, hardware, and acceptance tests.
- `docs/` - requirements, phase plans, standards, setup guides, and tracking.

## Local Services

After Docker Desktop is running, start the complete development environment:

```powershell
.\start-development.ps1
```

Stop all tracked applications and Compose services with `.\stop-development.ps1`.
Use `.\start-development.ps1 -ValidateOnly` to check prerequisites without starting
anything.

The compose credentials are local development defaults only. Do not reuse them outside local development.

## Diagnostics

After installing Python 3.11 and `uv`, run:

```powershell
uv sync --group dev
uv run specproof-doctor
uv run pytest tests/unit/tools/specproof_doctor -v
```

`specproof-doctor` reports PASS, FAIL, or SKIP for each Phase 0 workstation and service requirement.
