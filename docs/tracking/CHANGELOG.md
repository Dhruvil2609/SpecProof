# SpecProof Changelog

**Timezone:** UTC
**Format:** Keep a Changelog
**Versioning:** Semantic Versioning

## [Unreleased]

### Added

- 2026-08-05T17:16:30Z - Added Phase 4 deterministic measurement engine with POM ontology, tech-pack import, compiler, executor, decision routing, evidence hashing, .NET contracts/data persistence, and tests.
- 2026-08-01T08:20:52Z - Added Phase 3 replay regression and performance tests for canonical perception JSON stability, landmark consistency, mesh validity, and the 15-second runtime target.
- 2026-08-01T08:09:33Z - Added Phase 3 lightweight indexed visualisation mesh generation, canonical mesh JSON export, perception-result mesh metadata, and unit tests.
- 2026-07-31T17:05:12Z - Added Phase 3 low-distortion UV surface parameterisation, pixel-to-3D-to-2D mapping preservation, perception-result mapping export, and unit tests.
- 2026-07-31T16:47:39Z - Added the Phase 3 `.spcapture` perception orchestrator, versioned `PerceptionResult` JSON contract, canonical result writer, and pipeline tests.
- 2026-07-31T16:29:53Z - Added Phase 3 surface confidence scoring, T-shirt landmark vocabulary, contour-based landmark heuristics, review flags, recall scoring, and unit tests.
- 2026-07-31T16:16:10Z - Added deterministic Phase 3 RGB-depth garment segmentation, boundary extraction, T-shirt category/orientation heuristics, IoU scoring, and unit tests.
- 2026-07-30T17:59:35Z - Added synthetic calibration evaluators, capture-zone framing validation, replay package validation, Phase 3 RGB-D preprocessing, point-cloud utilities, and focused Python tests.
- 2026-07-30T17:19:06Z - Added `docs/phases/README.md` defining software-first development before hardware acceptance.
- 2026-07-28T18:14:56Z - Added `start-development.ps1 -InfrastructureOnly` to start Docker services while Python Application Control approval is pending.
- 2026-07-28T17:50:19Z - Added unified PowerShell start/stop scripts with Docker health waiting, application readiness checks, PID tracking, per-service logs, camera-provider modes, and configuration tests.
- 2026-07-28T16:53:43Z - Added the Phase 0-2 development runbook with ordered workstation setup, full-stack startup, verification, hardware, and completion steps.
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

- 2026-07-30T17:19:06Z - Updated Phase 0-8 roadmap language so coding proceeds with mock, replay, synthetic, Docker, and simulated API tests while hardware gates remain deferred acceptance items.
- 2026-07-29T17:22:46Z - Moved local Docker PostgreSQL from `localhost:5432` to `localhost:55432` to avoid conflict with an existing Windows PostgreSQL process.
- 2026-07-28T17:50:19Z - Installed and locked the Python 3.11 runtime, ML, station, and development dependency groups and updated Phase 0 evidence from host verification.
- 2026-07-28T16:34:20Z — Pinned Compose images and Python dependencies for reproducibility.
- 2026-07-28T16:34:20Z — Updated EF Core and Microsoft extensions to `10.0.10` and Npgsql EF provider to `10.0.3`.
- 2026-07-28T16:34:20Z — Strengthened doctor checks for Windows build, PostgreSQL `SELECT 1`, Redis `PING`, RabbitMQ authentication, CV imports, and optional camera enumeration.
- 2026-07-28T16:34:20Z — Updated development PostgreSQL credentials to local-only `Username=Admin;Password=Admin@123`.

### Fixed

- 2026-07-29T17:43:19Z - Resolved .NET Application Control test execution blocker and passed 7 real PostgreSQL migration/audit integration tests.
- 2026-07-29T17:22:46Z - Resolved the Python 3.11 native module blocker and verified `specproof-doctor` exits with zero required failures.
- 2026-07-28T18:14:56Z - Improved the launcher Python policy failure message with the Docker-only startup workaround.
- 2026-07-28T18:06:57Z - Fixed the distroless Loki healthcheck, registered the missing initial EF migration, corrected PostgreSQL audit-test fixture ordering, and added early launcher detection for blocked Python native modules.
- 2026-07-28T17:50:19Z - Fixed `specproof-doctor` Windows command-shim execution so pnpm is detected and validated correctly.
- 2026-07-28T16:34:20Z — Removed frontend non-null assertions that violated lint rules.
- 2026-07-28T16:34:20Z — Replaced corrupted Phase 0, Phase 1, Phase 2, progress, and changelog text with valid UTF-8.

### Blocked

- 2026-07-30T18:16:18Z - Verified local Docker MinIO synchronization integration test passes.
- Branch protection and remote Windows/Linux workflow status require GitHub administrative access.
- RealSense, physical calibration, disconnect/reconnect, hardware replay corpus, and stability acceptance are deferred until qualified hardware is available.
