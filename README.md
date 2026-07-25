# SpecProof

SpecProof is a hardware and software system for automated garment measurement using RGB-D cameras, calibrated capture, 3D geometry, machine learning, and auditable decision records.

## Phase 0 Setup

This repository is currently in Phase 0: development environment setup. The host workstation setup is documented in `docs/setup/PHASE-0-WINDOWS.md`, and the reproducible local diagnostics are provided by `specproof-doctor`.

## Repository Layout

- `apps/` - station host, capture service, measurement service, APIs, and UIs.
- `packages/` - shared contracts, geometry, calibration, POM, measurement, decision, and evidence modules.
- `infra/` - local Docker, compose, monitoring, Windows, and Linux infrastructure assets.
- `ml/` - datasets, annotations, training, evaluation, exports, and model cards.
- `tools/` - developer and operator tools, including `specproof-doctor`.
- `tests/` - unit, integration, contract, regression, cross-platform, hardware, and acceptance tests.
- `docs/` - requirements, phase plans, standards, setup guides, and tracking.

## Local Services

Start local infrastructure after Docker Desktop is installed and running:

```powershell
docker compose up -d
docker compose ps
```

The compose credentials are local development defaults only. Do not reuse them outside local development.

## Diagnostics

After installing Python 3.11 and `uv`, run:

```powershell
uv sync --group dev
uv run specproof-doctor
uv run pytest tests/unit/tools/specproof_doctor -v
```

`specproof-doctor` reports PASS, FAIL, or SKIP for each Phase 0 workstation and service requirement.
