# SpecProof Changelog

**Timezone:** UTC
**Format:** Keep a Changelog
**Versioning:** Semantic Versioning

## [Unreleased]

### Added

- 2026-07-28T16:34:20Z — Added the versioned capture-station protobuf contract and generated Python/C# types.
- 2026-07-28T16:34:20Z — Added mock, replay, and Windows RealSense camera adapters with aligned RGB-D capture, recording, retry, and reconnect behavior.
- 2026-07-28T16:34:20Z — Added immutable calibration records, daily/full validity, expiry enforcement, and persistence.
- 2026-07-28T16:34:20Z — Added atomic ZIP64 `.spcapture` packages with canonical manifests, PNG payloads, camera geometry, and SHA-256 validation.
- 2026-07-28T16:34:20Z — Added SQLite offline queueing, idempotent platform synchronization, MinIO/S3 storage, and capture-asset database records.
- 2026-07-28T16:34:20Z — Added station registration, health, capture initiation, and upload-completion API endpoints.
- 2026-07-28T16:34:20Z — Added Python, .NET, frontend, gRPC, package, calibration, queue, and migration tests with coverage reporting.
- 2026-07-28T16:34:20Z — Added generated ASP.NET Core OpenAPI and OpenTelemetry traces, metrics, logs, and OTLP configuration.
- 2026-07-26T13:16:49Z — Added end-user, administrator, and developer source-of-truth documentation.
- 2026-07-25T14:27:34Z — Added Phase 0 scaffolding, local infrastructure, Windows setup guidance, and `specproof-doctor`.

### Changed

- 2026-07-28T16:34:20Z — Pinned Compose images and Python dependencies for reproducibility.
- 2026-07-28T16:34:20Z — Updated EF Core and Microsoft extensions to `10.0.10` and Npgsql EF provider to `10.0.3`.
- 2026-07-28T16:34:20Z — Strengthened doctor checks for Windows build, PostgreSQL `SELECT 1`, Redis `PING`, RabbitMQ authentication, CV imports, and optional camera enumeration.
- 2026-07-28T16:34:20Z — Updated development PostgreSQL credentials to local-only `Username=Admin;Password=Admin@123`.

### Fixed

- 2026-07-28T16:34:20Z — Removed frontend non-null assertions that violated lint rules.
- 2026-07-28T16:34:20Z — Replaced corrupted Phase 0, Phase 1, Phase 2, progress, and changelog text with valid UTF-8.

### Blocked

- Python 3.11 execution is blocked by Windows Application Control on the managed interpreter.
- Docker service, PostgreSQL, MinIO, and migration runtime verification await a running Docker daemon.
- Branch protection and remote Windows/Linux workflow status require GitHub administrative access.
- RealSense, physical calibration, disconnect/reconnect, replay corpus, and stability acceptance require qualified hardware.
