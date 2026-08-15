# SpecProof Development Runbook

**Audience:** Developers, workstation administrators, and technical testers  
**Scope:** Phases 0, 1, and 2  
**Status:** Living runbook  
**Last Updated:** 2026-08-01T08:20:52Z
**Platform:** Windows 11 x64  
**Shell:** PowerShell 7

This guide explains how to prepare the workstation, validate the repository, run the
current SpecProof applications, and close the remaining acceptance gates for Phases 0,
1, and 2.

The repository code for these phases is partially complete. A manual action is not
evidence that a task passed: run the stated verification command and update the phase
and tracking documents only after the result is successful.

## 1. Current Phase Status

| Phase   | Status        | Main Remaining Gates                                                                                             |
| ------- | ------------- | ---------------------------------------------------------------------------------------------------------------- |
| Phase 0 | `IN_PROGRESS` | Host tooling, RealSense, and optional GPU acceptance remain manual/deferred                                      |
| Phase 1 | `IN_PROGRESS` | Remote CI, branch protection, and required checks                                                               |
| Phase 2 | `IN_PROGRESS` | Linux replay and deferred hardware acceptance remain; local MinIO sync is verified                            |
| Phase 3 | `IN_PROGRESS` | `.spcapture` perception pipeline has replay regression, mesh validity, and runtime tests                       |

Hardware is not currently available. Continue software development for Phases 2-8
with mock providers, replay packages, synthetic fixtures, Docker services, and API
simulators. Do not mark physical camera, calibration, disconnect/reconnect, stability,
pilot, or measurement-validation gates complete until hardware evidence exists.

Review the authoritative task lists before changing a phase status:

- `docs/phases/PHASE-0_development-environment-setup.md`
- `docs/phases/PHASE-1_project-foundation.md`
- `docs/phases/PHASE-2_capture-station-core.md`
- `docs/tracking/PROGRESS.md`

## 2. Important Development Credentials

These credentials are for local development only.

| Service          | Endpoint                 | Username    | Password                 |
| ---------------- | ------------------------ | ----------- | ------------------------ |
| PostgreSQL       | `localhost:55432`        | `Admin`     | `Admin@123`              |
| MinIO            | `http://localhost:9000`  | `specproof` | `specproof_dev_password` |
| MinIO Console    | `http://localhost:9001`  | `specproof` | `specproof_dev_password` |
| RabbitMQ         | `localhost:5672`         | `specproof` | `specproof_dev_password` |
| RabbitMQ Console | `http://localhost:15672` | `specproof` | `specproof_dev_password` |
| Grafana          | `http://localhost:3000`  | `specproof` | `specproof_dev_password` |

Never reuse these values in a shared, staging, pilot, or production environment.

## 3. Phase 0: Complete the Development Environment

Perform these steps in order.

### Step 0.1: Verify Windows and Security

1. Install all approved Windows updates and restart.
2. Confirm Windows 11 x64:

   ```powershell
   Get-ComputerInfo |
     Select-Object WindowsProductName, WindowsVersion, OsBuildNumber, OsArchitecture
   ```

3. Enable Developer Mode in **Settings > System > Advanced > For developers**.
4. Confirm time synchronization:

   ```powershell
   w32tm /query /status
   ```

5. If the clock is not synchronized, run from an elevated terminal:

   ```powershell
   w32tm /config /manualpeerlist:"time.windows.com,0x8" /syncfromflags:manual /update
   Restart-Service W32Time
   w32tm /resync /rediscover
   w32tm /query /status
   ```

   On a domain-joined workstation, use the organisation-approved NTP policy instead.

6. Confirm BitLocker status and enable it when required by workstation policy:

   ```powershell
   manage-bde -status
   ```

7. Install approved chipset, GPU, and USB-controller drivers from Windows Update or
   the workstation vendor.

### Step 0.2: Install WSL2

1. Open an elevated PowerShell terminal.
2. Install WSL2:

   ```powershell
   wsl --install
   ```

3. Restart Windows when requested.
4. Verify WSL:

   ```powershell
   wsl --status
   wsl --list --verbose
   ```

5. Confirm the installed Linux distribution reports version `2`.

### Step 0.3: Install and Start Docker Desktop

1. Install Docker Desktop using the approved workstation installer.
2. Enable **Use the WSL 2 based engine** in Docker Desktop settings.
3. Start Docker Desktop and wait until the engine reports that it is running.
4. Verify the daemon and Compose:

   ```powershell
   docker version
   docker compose version
   docker run --rm hello-world
   ```

### Step 0.4: Install Core Developer Tools

Install:

1. Visual Studio 2022 with:
   - ASP.NET and web development
   - .NET desktop development
   - Desktop development with C++
2. Visual Studio Code.
3. Git for Windows and Git LFS.
4. PowerShell 7 and Windows Terminal.
5. CMake.
6. Ninja.
7. OpenSSL.

Verify every tool:

```powershell
git --version
git lfs version
pwsh --version
code --version
cmake --version
ninja --version
openssl version
```

### Step 0.5: Install the Pinned .NET and Node Toolchains

1. Install the .NET SDK version selected by `global.json`.
2. Install Node.js `24.x`.
3. Enable or install pnpm `10.x`.
4. Verify:

   ```powershell
   dotnet --info
   dotnet --list-sdks
   node --version
   pnpm --version
   ```

The repository currently pins .NET SDK `10.0.301`, Node `24.x`, and pnpm `10.x`.

### Step 0.6: Resolve Python 3.11 Application-Control Approval

The current workstation blocks native modules from the `uv`-managed Python 3.11
installation. Before proceeding, ask the workstation administrator to approve the
managed interpreter or install an enterprise-approved Python 3.11 x64 distribution.

After approval:

```powershell
uv --version
uv python install 3.11
uv sync --python 3.11 --group runtime --group ml --group station --group dev
uv run python --version
```

The final command must report Python `3.11.x`. Do not use the temporary Python 3.14
validation environment to close Phase 0.

If Python is still blocked but you need the Docker infrastructure for database,
queue, object-storage, or observability work, run:

```powershell
.\start-development.ps1 -InfrastructureOnly
```

This starts only the Docker Compose services and skips the Python-backed capture
service, station host, platform API, and web UI processes.

Verify the required Python packages:

```powershell
uv run python -c "import cv2, open3d, numpy; print('CV stack OK')"
uv run python -c "import torch; print(torch.__version__); print(torch.cuda.is_available())"
uv run python -c "import pyrealsense2 as rs; print('RealSense Python OK')"
```

### Step 0.7: Start Local Infrastructure

From the repository root:

```powershell
docker compose config --quiet
docker compose up -d
docker compose ps
```

Wait until all services report healthy. Check logs for any unhealthy service:

```powershell
docker compose logs --tail 100 postgres redis minio rabbitmq prometheus grafana loki
```

Open and verify:

- MinIO console: `http://localhost:9001`
- RabbitMQ console: `http://localhost:15672`
- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3000`
- Loki readiness: `http://localhost:3100/ready`

### Step 0.8: Install and Validate RealSense

1. Install the approved Intel RealSense SDK 2.0 for Windows.
2. Install and open RealSense Viewer.
3. Connect a supported D435-class camera directly to a USB 3.x controller.
4. Confirm RGB and depth streams work at the required profiles.
5. Record camera model, serial, firmware, SDK version, USB controller, and cable.
6. Verify Python enumeration:

   ```powershell
   uv run python -c "import pyrealsense2 as rs; print([d.get_info(rs.camera_info.serial_number) for d in rs.context().devices])"
   ```

### Step 0.9: Run the Phase 0 Doctor

Run the standard checks:

```powershell
uv run specproof-doctor
```

On a capture workstation, enforce the hardware checks:

```powershell
uv run specproof-doctor --require-realsense --require-camera-stream
```

On a workstation where NVIDIA acceleration is mandatory:

```powershell
uv run specproof-doctor --require-gpu --require-realsense --require-camera-stream
```

Phase 0 is complete only when all required rows pass, the doctor exits with code `0`,
the local services are healthy, and the applicable camera/GPU policy is satisfied.

## 4. Phase 1: Complete the Project Foundation

Start this section only after the required Phase 0 environment checks pass.

### Step 1.1: Restore Every Workspace

From the repository root:

```powershell
git lfs install
git lfs pull
dotnet restore SpecProof.slnx
pnpm install --frozen-lockfile
uv sync --python 3.11 --group runtime --group ml --group station --group dev
```

### Step 1.2: Validate .NET

```powershell
dotnet build SpecProof.slnx --configuration Release --no-restore
dotnet test SpecProof.slnx --configuration Release --no-build --collect:"XPlat Code Coverage"
```

Expected current result: a warning-free build and 7 passing tests.

### Step 1.3: Validate Python

```powershell
uv run ruff format --check .
uv run ruff check .
uv run pyright
uv run pytest -v --cov --cov-report=term-missing
```

Expected current result: 58 passing tests and at least 80% configured Python coverage.

### Step 1.4: Validate Frontend Applications

```powershell
pnpm lint
pnpm typecheck
pnpm test:coverage
pnpm build
```

Expected current result: 8 passing tests and successful builds for both applications.

### Step 1.5: Run PostgreSQL Migration Acceptance Tests

1. Confirm the PostgreSQL container is healthy:

   ```powershell
   docker compose ps postgres
   docker exec specproof-postgres pg_isready -U Admin -d specproof
   ```

2. Create the isolated test database if it does not exist:

   ```powershell
   $exists = docker exec specproof-postgres psql -U Admin -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='specproof_test'"
   if ($exists.Trim() -ne "1") {
     docker exec specproof-postgres createdb -U Admin specproof_test
   }
   ```

3. Enable and run the real PostgreSQL tests:

   ```powershell
   $env:SPEC_PROOF_RUN_DATABASE_INTEGRATION = "1"
   $env:SPEC_PROOF_TEST_DATABASE = "Host=localhost;Port=55432;Database=specproof_test;Username=Admin;Password=Admin@123"
   dotnet test tests/integration/dotnet/SpecProof.Data.Tests/SpecProof.Data.Tests.csproj --configuration Release
   Remove-Item Env:SPEC_PROOF_RUN_DATABASE_INTEGRATION
   Remove-Item Env:SPEC_PROOF_TEST_DATABASE
   ```

These tests verify forward migration, rollback, constraints, UTC column mapping, and
append-only audit behavior against PostgreSQL.

### Step 1.6: Run Phase 7 Performance Acceptance

Run the repeatable integrated synthetic benchmark test:

```powershell
.venv\Scripts\python.exe -m pytest tests/unit/python/test_inspection_pipeline.py -m performance -q
```

When Docker PostgreSQL is available and `specproof_test` is migrated, capture the seeded
query plans. The profiler always rolls its synthetic data back:

```powershell
$env:SPEC_PROOF_TEST_DATABASE = "Host=localhost;Port=55432;Database=specproof_test;Username=Admin;Password=Admin@123"
.venv\Scripts\python.exe tools/performance/profile_platform_queries.py --output artifacts/performance/platform-query-plans.json
Remove-Item Env:SPEC_PROOF_TEST_DATABASE
```

Treat warm p95 below 15 seconds as the software acceptance gate. Report the 5-second pilot
target separately, and do not close CUDA or database profiling acceptance without runtime
evidence from qualified hardware and PostgreSQL.

### Step 1.7: Run Phase 7 Resilience Acceptance

Run software power-loss, network, checksum, dead-letter, database-failure, and flaky-camera
recovery tests:

```powershell
.venv\Scripts\python.exe -m pytest tests/integration/python/test_phase7_resilience.py -q
dotnet test tests/unit/dotnet/SpecProof.Platform.Api.Tests/SpecProof.Platform.Api.Tests.csproj --configuration Release
```

When Docker PostgreSQL is available, execute the concurrent tenant and audit-linkage stress
test against the isolated migrated database:

```powershell
$env:SPEC_PROOF_RUN_DATABASE_INTEGRATION = "1"
$env:SPEC_PROOF_TEST_DATABASE = "Host=localhost;Port=55432;Database=specproof_test;Username=Admin;Password=Admin@123"
dotnet test tests/unit/dotnet/SpecProof.Platform.Api.Tests/SpecProof.Platform.Api.Tests.csproj --configuration Release --filter "Category=Stress"
Remove-Item Env:SPEC_PROOF_RUN_DATABASE_INTEGRATION
Remove-Item Env:SPEC_PROOF_TEST_DATABASE
```

The flaky provider validates software retry behavior only. Keep physical USB disconnect,
camera process recovery, and qualified-hardware soak acceptance open until hardware exists.

### Step 1.8: Run Phase 7 Deployment Acceptance

Run the shared golden replay and package-definition tests locally:

```powershell
.venv\Scripts\python.exe -m pytest tests/cross-platform/test_golden_replay.py tests/regression/python/test_perception_replay_regression.py tests/unit/tools/test_phase7_deployment.py -q
docker compose --profile application config --quiet
```

With Docker Desktop running, build and start the complete application profile, verify the
four health endpoints, then stop it cleanly:

```powershell
docker compose --profile application up --build --wait
Invoke-RestMethod http://127.0.0.1:5080/healthz
Invoke-RestMethod http://127.0.0.1:8000/healthz
Invoke-RestMethod http://127.0.0.1:4173/healthz
Invoke-RestMethod http://127.0.0.1:4174/healthz
docker compose --profile application down --volumes
```

Build and cryptographically verify a versioned Linux x64 station package:

```powershell
.venv\Scripts\python.exe tools/packaging/build_station_package.py --version 0.1.0-local --output-dir artifacts/packages
.venv\Scripts\python.exe -c "from pathlib import Path; from tools.packaging.build_station_package import verify_station_package; verify_station_package(Path('artifacts/packages/specproof-station-0.1.0-local-linux-x64.tar.gz'))"
```

The local package check proves archive contents, modes, and hashes. Keep Linux startup and
cross-platform equivalence gates open until `.github/workflows/phase7-deployment.yml` passes
on hosted Windows and Ubuntu runners; keep container acceptance open until the live profile
passes with a running Docker daemon.

### Step 1.9: Verify Generated OpenAPI and API Health

Start the API in a dedicated terminal:

```powershell
$env:ASPNETCORE_ENVIRONMENT = "Development"
$env:ASPNETCORE_URLS = "http://127.0.0.1:5080"
dotnet run --project apps/platform-api/SpecProof.Platform.Api.csproj
```

In another terminal:

```powershell
Invoke-RestMethod http://127.0.0.1:5080/healthz
Invoke-WebRequest http://127.0.0.1:5080/api/v1/openapi.json
```

The health and OpenAPI routes do not prove that database-backed endpoints have a
deployed schema. Use the migration acceptance tests for the current Phase 1 database
gate and add a supported deployment migration command before treating this API as a
shared environment.

### Step 1.10: Verify Remote CI

1. Push a branch to GitHub.
2. Open a pull request.
3. Confirm these workflows pass:
   - .NET build and tests
   - Python lint, type-check, tests, and coverage
   - Frontend lint, tests, coverage, and build
   - Docker Compose integration
   - PostgreSQL migrations
4. Confirm the workflows run on every configured Windows and Linux runner.
5. Record the workflow URLs as verification evidence.

### Step 1.10: Configure Branch Protection

A GitHub repository administrator must:

1. Protect the default branch.
2. Require pull requests before merge.
3. Require all Phase 1 CI checks.
4. Require the branch to be current before merge.
5. Prevent direct pushes and force pushes.
6. Require conversation resolution.
7. Test the rule with a pull request.

Do not mark the branch-protection tasks complete until the rule is enabled and tested.

## 5. Phase 2: Run and Complete Capture Station Core

Phase 2 can run with a mock camera today. Implement all software modules using mock,
replay, synthetic, and Docker-backed tests before hardware arrives. Full hardware
acceptance additionally requires physical calibration checks, qualified hardware,
real replay files, cross-platform execution, service integrations, and a stability
test.

### Step 2.1: Start the Mock Capture Service

Open terminal 1:

```powershell
$env:SPEC_PROOF_CAMERA_PROVIDER = "mock"
$env:SPEC_PROOF_STATION_DATA = "station-data"
$env:SPEC_PROOF_CAPTURE_ADDRESS = "127.0.0.1:50051"
uv run specproof-capture-service
```

Keep this terminal running. The gRPC service listens on `127.0.0.1:50051`.

### Step 2.2: Start the .NET Station Host

Open terminal 2:

```powershell
dotnet run --project apps/station-host/SpecProof.Station.Host.csproj
```

The station host checks the capture-service health every 30 seconds. Confirm the logs
show successful health responses.

### Step 2.3: Start the Platform API

Open terminal 3:

```powershell
$env:ASPNETCORE_ENVIRONMENT = "Development"
$env:ASPNETCORE_URLS = "http://127.0.0.1:5080"
dotnet run --project apps/platform-api/SpecProof.Platform.Api.csproj
```

Verify:

```powershell
Invoke-RestMethod http://127.0.0.1:5080/healthz
```

### Step 2.4: Start the Frontend Applications

Open terminal 4 for the operator application:

```powershell
pnpm --filter @specproof/operator-ui exec vite --host 127.0.0.1 --port 5173
```

Open terminal 5 for the admin application:

```powershell
pnpm --filter @specproof/admin-ui exec vite --host 127.0.0.1 --port 5174
```

Open:

- Operator UI: `http://127.0.0.1:5173`
- Admin UI: `http://127.0.0.1:5174`

These Phase 1 shells are not yet wired to every Phase 2 gRPC or platform operation.
Use the automated service tests for current capture-contract verification.

### Step 2.5: Run Phase 2 Automated Tests

```powershell
uv run pytest tests/unit/python/test_capture_core.py tests/unit/python/test_capture_metadata.py tests/unit/python/test_grpc_service.py -v
dotnet test SpecProof.slnx --configuration Release --collect:"XPlat Code Coverage"
```

Verify camera mocks, profile validation, calibration validity, median fusion,
`.spcapture` checksums, queue transitions, and gRPC behavior.

### Step 2.6: Run Replay Mode

Obtain approved `.bag` or `.spcapture` fixtures through Git LFS. Then:

```powershell
$env:SPEC_PROOF_CAMERA_PROVIDER = "replay"
$env:SPEC_PROOF_REPLAY_PATH = "<absolute-path-to-approved-replay-fixture>"
$env:SPEC_PROOF_STATION_DATA = "station-data-replay"
uv run specproof-capture-service
```

Do not add real captures to normal Git storage. Track `.bag` and `.spcapture` files
through Git LFS.

### Step 2.7: Run PostgreSQL and MinIO Integration

1. Keep Docker services running.
2. Run the PostgreSQL migration tests from Step 1.5.
3. Verify MinIO health:

   ```powershell
   Invoke-RestMethod http://localhost:9000/minio/health/live
   ```

4. Run the capture queue, upload, checksum, retry, and restart integration tests when
   those executable integration tests are present.
5. Confirm PostgreSQL stores only capture metadata and MinIO stores `.spcapture`
   payloads.

The current repository does not yet contain the full MinIO/platform end-to-end test.
That test must be implemented and pass before completing the Phase 2 integration gate.

### Step 2.8: Complete Physical Calibration Work

The following tasks require both implementation and manual hardware execution:

1. Intrinsic verification.
2. RGB-to-depth alignment verification.
3. Capture-plane extrinsic calibration.
4. Scale verification with a traceable known-size artefact.
5. Plane flatness and camera tilt checks.
6. Lighting uniformity verification.
7. Capture-zone framing validation.

Acceptance thresholds:

- Scale error: at most `0.1%`.
- Plane RMS: at most `2 mm`.
- Camera tilt: at most `0.5 degrees`.
- Lighting variation: at most `10%`.
- Full calibration validity: `30 days`.
- Daily-check validity: `24 hours`.

Record the station, operator, camera serial, artefact ID, metrics, UTC timestamp,
software version, and calibration checksum.

### Step 2.9: Build the Hardware Replay Corpus

Record and classify:

1. Valid captures.
2. Low-light captures.
3. Reflective-fabric captures.
4. Black-fabric captures.
5. Missing-depth captures.
6. Expired-calibration captures.
7. Corrupted packages.
8. Interrupted captures.

Update `tests/fixtures/capture-replay/v1/scenarios.json`, store large binary fixtures
through Git LFS, and run identical package validation on Windows and Linux.

### Step 2.10: Run Hardware Acceptance

On qualified Windows hardware:

1. Enumerate the camera by serial number.
2. Stream aligned RGB `1280x720@30` and depth `848x480@30`.
3. Record and replay a `.bag`.
4. Capture and validate a `.spcapture`.
5. Disconnect and reconnect USB during controlled operation.
6. Confirm bounded retry and recovery.
7. Verify scale against the known artefact.
8. Run a 30-minute zero-failure stability test.
9. Save logs, metrics, package checksums, and UTC test evidence.

On Linux:

1. Pull the same LFS replay corpus.
2. Run replay and package-validation tests.
3. Confirm exact manifests, checksums, image dimensions, and depth values.

Phase 2 remains `IN_PROGRESS` until every documented hardware, integration, replay,
cross-platform, and stability gate passes.

## 6. Full Local Startup Order

After one-time setup, start the complete local environment from the repository root:

```powershell
.\start-development.ps1
```

The launcher:

- Validates Docker, .NET, Python/uv, pnpm, required project files, and local ports.
- Starts all Docker Compose infrastructure and waits for healthy containers.
- Starts the mock capture service, station host, platform API, operator UI, and admin UI.
- Waits for application ports and HTTP health endpoints.
- Writes process IDs to `.cache/development/processes.json`.
- Writes separate stdout and stderr logs under `.cache/development/logs/`.
- Stops any applications it started if startup fails.

Check prerequisites without starting services:

```powershell
.\start-development.ps1 -ValidateOnly
```

Start only Docker infrastructure while Python Application Control approval is pending:

```powershell
.\start-development.ps1 -InfrastructureOnly
```

Start without changing Docker infrastructure:

```powershell
.\start-development.ps1 -SkipInfrastructure
```

Use a replay fixture:

```powershell
.\start-development.ps1 -CameraProvider replay -ReplayPath "D:\captures\approved.spcapture"
```

Use a physical RealSense camera:

```powershell
.\start-development.ps1 -CameraProvider realsense
```

The default provider is `mock`. The application endpoints are:

- Platform API: `http://127.0.0.1:5080`
- OpenAPI: `http://127.0.0.1:5080/api/v1/openapi.json`
- Operator UI: `http://127.0.0.1:5173`
- Admin UI: `http://127.0.0.1:5174`

## 7. Shutdown

Stop all applications tracked by the launcher and stop Compose services:

```powershell
.\stop-development.ps1
```

Stop applications but keep infrastructure running:

```powershell
.\stop-development.ps1 -KeepInfrastructure
```

To remove containers but retain named volumes:

```powershell
docker compose down
```

Delete named volumes only when intentionally resetting all local service data:

```powershell
docker compose down --volumes
```

The last command permanently deletes local PostgreSQL, Redis, MinIO, RabbitMQ,
Prometheus, Grafana, and Loki data.

## 8. Updating Completion Evidence

After a gate passes:

1. Change only the objectively completed checkbox in the matching phase document.
2. Add the UTC completion timestamp.
3. Update phase counts and blockers in `docs/tracking/PROGRESS.md`.
4. Add the change under `[Unreleased]` in `docs/tracking/CHANGELOG.md`.
5. Update `documentation/FEATURE-SOURCE-OF-TRUTH.md` when behavior changes.
6. Update `documentation/USER-MANUAL.md` or `documentation/ADMIN-MANUAL.md` when an
   operator or administrator procedure changes.
7. Attach or link CI, hardware, calibration, or stability evidence where applicable.

Use UTC timestamps:

```powershell
[DateTime]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ")
```

Do not mark blocked hardware, administrative, or remote checks complete from local
source inspection alone.
