# SpecProof Documentation

This folder contains the living product documentation for SpecProof.

## Files

- `USER-MANUAL.md` - End-user/operator manual for day-to-day garment inspection.
- `ADMIN-MANUAL.md` - Administrator manual for users, tenants, stations, policies, and support operations.
- `FEATURE-SOURCE-OF-TRUTH.md` - Developer-facing feature catalogue and expected behaviour source of truth.

## Update Rules

Update these files whenever a requirement, workflow, role, UI screen, API behaviour, data model, or operating procedure changes.

### Required Updates

- Update `FEATURE-SOURCE-OF-TRUTH.md` before or in the same change as any feature implementation.
- Update `USER-MANUAL.md` when an operator-facing workflow, label, status, error, or screen changes.
- Update `ADMIN-MANUAL.md` when a permission, tenant setting, station setup step, retention policy, diagnostics flow, or admin screen changes.
- Update examples, screenshots, commands, and credentials when development environment defaults change.
- Keep all timestamps in UTC ISO 8601 format.

### Review Checklist

- The documented feature exists in requirements, phase docs, or implemented code.
- The user/admin instructions describe observable behaviour, not internal guesses.
- The source-of-truth entry includes use cases, expected behaviour, states, evidence, and validation notes.
- Any blocked, future, or unimplemented capability is clearly marked as `Planned` or `Blocked`.
- Related progress files under `docs/tracking/` are updated for completed documentation work.

### Status Labels

- `Implemented` - Code and tests exist in the repository.
- `Partially Implemented` - A scaffold or partial flow exists, but the full requirement is not complete.
- `Planned` - Requirement is accepted but not implemented.
- `Blocked` - Work depends on hardware, credentials, tooling, admin setup, or external decisions.
