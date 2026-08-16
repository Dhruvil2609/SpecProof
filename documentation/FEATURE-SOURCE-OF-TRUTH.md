# SpecProof Feature Source of Truth

**Audience:** Developers, QA, product owners, and technical reviewers  
**Status:** Living draft  
**Last Updated:** 2026-08-16T08:32:52Z

This document lists the expected system features and use cases. It is the developer-facing source of truth for what each feature should do. Update it whenever requirements, implementation, tests, or user workflows change.

## 1. Product Scope

SpecProof is a calibrated RGB-D garment measurement and inspection system for flat or relaxed finished garments on a defined capture surface.

Hardware is not currently available. The system must be developed software-first:
coding modules, contracts, APIs, perception logic, measurement logic, UI workflows,
storage, sync, and reporting proceed with mock providers, replay packages, synthetic
fixtures, Docker services, and simulated station APIs. Physical camera validation,
calibration acceptance, hardware stability, and pilot evidence are deferred acceptance
gates.

### MVP Scope

- Controlled capture station.
- RGB-D capture and calibration validation.
- Initial garment category: short-sleeve T-shirt unless product direction changes.
- 6-10 approved points of measure.
- Structured tech-pack import.
- Measurement and tolerance comparison.
- Pass/fail/review/invalid decision.
- Evidence record with hashes, versions, calibration, and measurements.

### Out of MVP Scope

- Mannequin or turntable scanning.
- Virtual try-on.
- Photorealistic 360-degree catalogue assets.
- Fully autonomous arbitrary PDF tech-pack parsing.
- Legal-grade non-repudiation without dedicated security/legal review.

## 2. Feature Catalogue

| Feature ID | Feature | Status | Primary Users |
|------------|---------|--------|---------------|
| `SPF-001` | Station health diagnostics | Partially Implemented | Operator, Admin, Support |
| `SPF-002` | Camera abstraction | Implemented; hardware acceptance deferred | Developer |
| `SPF-003` | Calibration record management | Partially Implemented | Operator, Admin |
| `SPF-004` | Garment capture workflow | Partially Implemented | Operator |
| `SPF-005` | Garment perception pipeline | Partially Implemented | Operator, Developer |
| `SPF-006` | Geometry and surface processing | Partially Implemented | Developer |
| `SPF-007` | Point-of-measure ontology | Planned | Technical Designer, Developer |
| `SPF-008` | POM compiler | Planned | Technical Designer, Developer |
| `SPF-009` | Measurement engine | Planned | Operator, Reviewer |
| `SPF-010` | Decision engine | Planned | Operator, Reviewer |
| `SPF-011` | Inspection evidence record | Partially Implemented | Operator, Reviewer, Auditor |
| `SPF-012` | Audit event stream | Partially Implemented | Admin, Auditor |
| `SPF-013` | Tenant/user/role administration | Partially Implemented | Admin |
| `SPF-014` | Station administration | Partially Implemented | Admin, Support |
| `SPF-015` | Tech-pack import and mapping | Planned | Technical Designer, Admin |
| `SPF-016` | Operator UI | Partially Implemented | Operator |
| `SPF-017` | Admin UI | Partially Implemented | Admin |
| `SPF-018` | Reporting and exports | Planned | Quality Manager, Brand User |
| `SPF-019` | API and webhooks | Planned | Integrator, Developer |
| `SPF-020` | Observability and support bundle | Partially Implemented | Admin, Support |
| `SPF-021` | Unified development launcher | Implemented | Developer, Support |
| `SPF-022` | Production identity and transport security | Partially Implemented | Admin, Security, Support |

## 3. Feature Details

### `SPF-001` Station Health Diagnostics

**Use Case:** Operator or support user verifies that the workstation, services, and optional hardware are ready.

**Expected Behaviour:**

- Report one deterministic row per component.
- Use `PASS`, `FAIL`, or `SKIP`.
- Fail required dependencies.
- Skip optional hardware when not required.
- Never print secrets.

**Evidence and Tests:**

- `specproof-doctor` unit tests verify command parsing, aggregation, formatting, and optional hardware behaviour.

### `SPF-002` Camera Abstraction

**Use Case:** Station software lists cameras and captures frames without binding domain code directly to RealSense APIs.

**Expected Behaviour:**

- Expose camera capabilities.
- Capture RGB-D frame payloads.
- Keep provider-specific SDK behaviour behind adapters.
- Record UTC capture timestamps.

**Current Implementation:**

- The canonical gRPC contract exposes device, health, preview, capture, recording, and calibration operations.
- Python provides mock, `.spcapture` replay, and Windows RealSense adapters.
- The .NET station host consumes generated client types and maps gRPC failures to typed station exceptions.
- RealSense hardware acceptance is deferred until qualified hardware is available.

### `SPF-003` Calibration Record Management

**Use Case:** Every inspection must be tied to valid calibration.

**Expected Behaviour:**

- Store calibration timestamp, expiry, artefact ID, camera serial, and checksum references.
- Prevent automated decisions when calibration is expired.
- Preserve historical calibration versions.

**Current Implementation:**

- Filesystem and PostgreSQL models preserve immutable version, mode, operator, artefact, metrics, validity window, checksum, and supersession metadata.
- Full calibration defaults to 30 days; daily checks default to 24 hours.
- Expired or missing calibration blocks capture.
- Physical calibration metric acceptance is deferred pending approved hardware and artefacts.

### `SPF-004` Garment Capture Workflow

**Use Case:** Operator captures one garment for inspection.

**Expected Behaviour:**

- Select or scan order/style/colour/size.
- Load approved spec version.
- Validate framing, orientation, lighting, and overlap.
- Capture RGB-D frames.
- Store raw/derived assets according to retention policy.

**Current Implementation:**

- The service captures 3–15 aligned frames, defaulting to 5.
- Valid depth is fused by per-pixel median and RGB uses the temporal midpoint frame.
- ZIP64 `.spcapture` packages use canonical manifests, lossless PNG payloads, camera geometry, metadata, and SHA-256 checksums.
- Packages publish atomically and queue in SQLite for idempotent object-store synchronization.
- Capture-zone framing is implemented for synthetic/replay masks.
- Operator browser integration remains planned.

### `SPF-005` Garment Perception Pipeline

**Use Case:** Convert captured RGB-D data into segmentation, landmarks, seams, and confidence values.

**Expected Behaviour:**

- Segment garment from capture surface.
- Register RGB and depth.
- Detect garment category and orientation.
- Propose landmarks with confidence.
- Refine landmarks using category and spec constraints.

**Current Implementation:**

- Background modelling, depth filtering, RGB-depth mask refinement, colour smoothing, and deterministic preprocessing are implemented for synthetic/replay RGB-D inputs.
- Deterministic RGB-depth mask fusion, garment boundary extraction, T-shirt category classification, front/back orientation detection, and IoU scoring are implemented as the software-first baseline.
- Surface confidence scoring now combines valid depth, capture-zone coverage, plane fit, and normal consistency.
- T-shirt landmark vocabulary, contour landmark heuristics, landmark confidence, missing/occluded review flags, and recall scoring are implemented for synthetic masks.
- The perception orchestrator loads `.spcapture`, runs preprocessing, segmentation, point-cloud, confidence, landmark, and UV parameterisation stages, then writes canonical versioned `PerceptionResult` JSON.
- Surface parameterisation preserves pixel coordinates, metric 3D points, and flattened UV millimetre coordinates for measurement-engine path construction.
- Lightweight indexed visualisation mesh generation exports stable vertices, triangle indices, vertex counts, and triangle counts in canonical JSON.
- Replay regression tests verify stable perception fingerprints, landmark consistency, mesh validity, and runtime below the 15-second target on synthetic `.spcapture` packages.
- Model training, model export, glTF/GLB packaging, multi-category classification, and learned landmark detection remain planned.

### `SPF-006` Geometry and Surface Processing

**Use Case:** Compute reliable distances and surface paths from metric RGB-D data.

**Expected Behaviour:**

- Remove invalid depth and outliers.
- Detect support plane.
- Generate point cloud or mesh.
- Compute straight, projected, contour, or geodesic paths.
- Preserve mapping between 2D developed surface and 3D coordinates.

**Current Implementation:**

- Organised point-cloud projection, normal estimation, support-plane fitting, and garment-to-plane separation are implemented with known-shape unit tests.
- Mesh generation, UV mapping, confidence scoring, and full surface parameterisation remain planned.

**Current Implementation:**

- Basic shared geometry package exists with tested Euclidean distance utility.

### `SPF-007` Point-of-Measure Ontology

**Use Case:** Normalize brand-specific measurement names to canonical POM definitions.

**Expected Behaviour:**

- Preserve original brand terminology.
- Map to canonical definitions with human approval for ambiguity.
- Version all mappings.

### `SPF-008` POM Compiler

**Use Case:** Convert approved POM definitions into executable measurement rules.

**Expected Behaviour:**

- Define anchors, path type, offsets, doubling rules, units, rounding, tolerances, confidence, and review policy.
- Execute consistently across Windows and Linux.
- Support historical rule replay.

### `SPF-009` Measurement Engine

**Use Case:** Calculate actual POM values from detected anchors and measurement rules.

**Expected Behaviour:**

- Return measured value, target, tolerance bounds, deviation, confidence, uncertainty, and status.
- Include visual evidence overlay metadata.
- Route low-confidence values to review.

### `SPF-010` Decision Engine

**Use Case:** Produce an inspection-level result.

**Expected Behaviour:**

- `PASS` when all required measurements are in tolerance and above confidence.
- `FAIL` when at least one required measurement is out of tolerance with sufficient confidence.
- `REVIEW` when capture quality, confidence, calibration, or rule execution is insufficient.
- `INVALID` when wrong item, wrong size, overlap, station failure, or missing required data is detected.

### `SPF-011` Inspection Evidence Record

**Use Case:** Brands, factories, and auditors can verify what was measured and why.

**Expected Behaviour:**

- Bind tenant, station, operator, order, SKU/style, colour, size, capture timestamp, hashes, calibration, camera, model, ruleset, spec, measurements, and review actions.
- Keep UTC timestamps.
- Preserve historical version references.

**Current Implementation:**

- Shared inspection DTOs exist.
- Full evidence signing is planned.

### `SPF-012` Audit Event Stream

**Use Case:** System changes and inspection transitions remain traceable.

**Expected Behaviour:**

- Store append-only audit events.
- Prevent update and delete operations.
- Include tenant, event type, entity type, entity ID, actor, payload, and UTC occurrence timestamp.

**Current Implementation:**

- EF model and initial migration include `audit_events` and append-only trigger SQL.

### `SPF-013` Tenant/User/Role Administration

**Use Case:** Admin manages organisations, factories, users, and permissions.

**Expected Behaviour:**

- Support tenants, organisations, factories, users, and roles.
- Enforce tenant isolation.
- Audit role and permission changes.

**Current Implementation:**

- Initial EF entities and migration foundation exist.

### `SPF-014` Station Administration

**Use Case:** Admin manages station assignment, health, calibration state, and sync status.

**Expected Behaviour:**

- Track station ID, factory, camera serial, software version, calibration status, local queue, and last sync.
- Support remote diagnostics and support bundle export.

### `SPF-015` Tech-Pack Import and Mapping

**Use Case:** Technical users import structured tech-pack data and approve POM mappings.

**Expected Behaviour:**

- Import CSV/XLSX/JSON initially.
- Store original source data.
- Map POM terminology to canonical definitions.
- Version specs, sizes, tolerances, grading, and mappings.
- Prevent retroactive changes to inspected spec versions.

### `SPF-016` Operator UI

**Use Case:** Operator runs inspection workflow and reviews result.

**Expected Behaviour:**

- Provide routed shell.
- Use i18n keys for all display strings.
- Show capture, review, and result workflows as implementation progresses.

**Current Implementation:**

- React/Vite shell, i18n, design tokens, routes, and component tests exist.

### `SPF-017` Admin UI

**Use Case:** Admin manages tenants, stations, policies, and diagnostics.

**Expected Behaviour:**

- Provide routed shell.
- Use i18n keys for all display strings.
- Expose user, station, calibration, and policy screens as implementation progresses.

**Current Implementation:**

- React/Vite shell, i18n, design tokens, routes, and component tests exist.

### `SPF-018` Reporting and Exports

**Use Case:** Quality managers analyze results and share records.

**Expected Behaviour:**

- Show batch/order summaries.
- Support out-of-tolerance Pareto analysis.
- Support supplier/style/size trends.
- Export CSV and PDF.

### `SPF-019` API and Webhooks

**Use Case:** External systems consume SpecProof results.

**Expected Behaviour:**

- Provide REST API.
- Generate OpenAPI specification.
- Emit webhook or event output for inspections.
- Maintain backward-compatible contracts.

### `SPF-020` Observability and Support Bundle

**Use Case:** Support diagnoses station and platform failures.

**Expected Behaviour:**

- Produce structured logs, metrics, and traces.
- Track camera FPS, dropped frames, invalid depth, latency, resource usage, calibration age, sync status, and result counts.
- Redact credentials in support bundles.

### `SPF-021` Unified Development Launcher

**Use Case:** A developer starts or stops the complete local SpecProof environment
without manually coordinating each process.

**Expected Behaviour:**

- Validate required commands, project paths, and application ports before startup.
- Start Compose infrastructure and wait for healthy containers.
- Use Docker PostgreSQL on `localhost:55432` to avoid conflicts with host PostgreSQL installs.
- Start capture, station, API, operator, and admin processes with isolated logs.
- Support mock, replay, and RealSense camera-provider modes.
- Support Docker-only infrastructure startup when Python workstation approval is pending.
- Record process IDs for deterministic shutdown.
- Stop applications started in the current launcher session when startup fails.

**Evidence and Tests:**

- `tests/unit/tools/test_development_launcher.py` validates configured processes,
  unique ports, working directories, .NET project paths, and infrastructure-only mode.
- `start-development.ps1 -ValidateOnly -SkipInfrastructure` verifies host command
  resolution without starting services.

### `SPF-022` Production Identity and Transport Security

**Use Case:** Security administrators deploy the platform with fail-closed identity,
authorisation, station certificate, and transport controls.

**Expected Behaviour:**

- Reject anonymous access to every non-public API route.
- Validate JWT signature, issuer, audience, lifetime, tenant, and known role.
- Bind station requests to active tenant/station identities backed by trusted client
  certificates.
- Reject production startup when protected secrets, HTTPS, certificate chain, EKU,
  revocation, or trusted roots are not configured.
- Emit restrictive security headers and maintain an auditable certificate rotation path.

**Evidence and Tests:**

- `tests/unit/dotnet/SpecProof.Platform.Api.Tests/PlatformTrustLayerTests.cs` covers JWT,
  API boundary, tenant/station binding, certificate policy, startup validation, and headers.
- `docs/security/AUTHENTICATION-AUTHORIZATION-AUDIT.md` records the route audit and findings.
- `docs/security/TLS-BASELINE.md` defines production transport acceptance.

## 4. Source-of-Truth Update Rules

- Add a feature entry before implementing a new product capability.
- Link feature changes to phase tasks and tests.
- Keep statuses honest; never mark planned features as implemented.
- Move behaviour from planned to implemented only when code and tests exist.
- Update user/admin manuals when a feature changes visible workflow or admin procedure.
