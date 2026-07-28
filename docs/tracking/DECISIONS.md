# SpecProof Architecture Decision Records

**Created:** 2026-07-25T13:15:00Z  
**Last Updated:** 2026-07-28T16:34:20Z
**Timezone:** UTC  
**Language:** en

## ADR Index

| ADR | Title | Status | Date (UTC) |
|-----|-------|--------|------------|
| ADR-001 | Use UTC for all timestamps | Accepted | 2026-07-25T13:15:00Z |
| ADR-002 | Use a monorepo workspace | Accepted | 2026-07-25T13:15:00Z |
| ADR-003 | Build i18n from day one | Accepted | 2026-07-25T13:15:00Z |
| ADR-004 | Require automated verification for agent changes | Accepted | 2026-07-25T13:15:00Z |
| ADR-005 | Use protobuf gRPC for station IPC | Accepted | 2026-07-28T16:34:20Z |
| ADR-006 | Use checksummed `.spcapture` packages | Accepted | 2026-07-28T16:34:20Z |

## ADR-001: Use UTC for All Timestamps

**Status:** Accepted
**Date:** 2026-07-25T13:15:00Z

### Decision

Use timezone-aware UTC in code, APIs, logs, evidence, documentation, and PostgreSQL `timestamptz` columns. Presentation layers may convert UTC for display.

## ADR-002: Use a Monorepo Workspace

**Status:** Accepted
**Date:** 2026-07-25T13:15:00Z

### Decision

Keep .NET, Python, TypeScript, infrastructure, contracts, and tests in one repository. Use pnpm workspaces, a .NET solution, and `pyproject.toml` dependency groups.

### Consequences

- Cross-component contract changes remain atomic.
- CI must validate every affected stack.
- Large capture assets use Git LFS.

## ADR-003: Build i18n from Day One

**Status:** Accepted
**Date:** 2026-07-25T13:15:00Z

### Decision

Use English as the base locale and translation keys for user-visible strings. Frontends use react-i18next and APIs honor locale negotiation where user-facing messages are returned.

## ADR-004: Require Automated Verification for Agent Changes

**Status:** Accepted
**Date:** 2026-07-25T13:15:00Z

### Decision

Code changes require relevant automated tests, static checks, progress updates, and honest recording of blocked external acceptance work.

## ADR-005: Use Protobuf gRPC for Station IPC

**Status:** Accepted  
**Date:** 2026-07-28T16:34:20Z

### Context

RealSense access and RGB-D processing require native Python dependencies, while the Windows station supervisor and platform integration use .NET.

### Decision

Use `packages/station-contracts/proto/v1/capture_station.proto` as the authoritative versioned IPC contract. Python hosts the camera service; .NET uses generated client types.

### Consequences

- RealSense SDK calls remain isolated behind Python adapters.
- Python and C# types derive from one contract.
- Missing devices map to `NOT_FOUND`, invalid calibration to `FAILED_PRECONDITION`, and unavailable hardware or SDKs to `UNAVAILABLE`.
- Contract compatibility tests are required before changing existing fields or methods.

## ADR-006: Use Checksummed `.spcapture` Packages

**Status:** Accepted
**Date:** 2026-07-28T16:34:20Z

### Context

RGB-D evidence must move between Windows stations, Linux services, offline queues, and S3-compatible object storage without losing fidelity or provenance.

### Decision

Use ZIP64 `.spcapture` packages containing canonical UTF-8 `manifest.json`, lossless RGB and unsigned 16-bit depth PNGs, intrinsics, extrinsics, per-frame metadata, and `checksums.sha256`. Publish packages atomically after validation.

### Consequences

- PostgreSQL stores metadata and object references, never image/depth binaries.
- Real package fixtures use Git LFS.
- Upload completion requires checksum verification and idempotency.
- Windows/Linux readers must produce identical manifests, dimensions, hashes, and depth values.
