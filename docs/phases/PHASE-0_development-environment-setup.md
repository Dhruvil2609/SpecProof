# Phase 0 — Development Environment Setup

**Phase ID:** PHASE-0  
**Status:** `IN_PROGRESS`
**Created:** 2026-07-25T13:15:00Z  
**Last Updated:** 2026-07-30T17:19:06Z
**Estimated Duration:** 1–2 weeks  
**Dependencies:** None  
**Language:** en

## 0.1 Objective

Provide reproducible repository configuration and diagnostics for a Windows 11 development workstation. Privileged host configuration remains a documented manual responsibility and is verified by `specproof-doctor`.

Software development can proceed without physical capture hardware. RealSense camera,
GPU, and physical streaming checks are capture-workstation acceptance gates and remain
deferred until hardware is available.

## 0.2 Tasks

### 0.3.1 Windows System Preparation

- [ ] **TASK-0.3.1.1** — Verify Windows 11 version, architecture, and updates
- [ ] **TASK-0.3.1.2** — Enable Developer Mode
- [ ] **TASK-0.3.1.3** — Configure NTP and UTC time synchronization
- [x] **TASK-0.3.1.4** — Enable BitLocker where supported ✅ (2026-07-28T17:50:19Z)
- [ ] **TASK-0.3.1.5** — Install qualified chipset and USB-controller drivers

### 0.3.2 WSL2 and Docker Desktop

- [x] **TASK-0.3.2.1** — Install and verify WSL2 ✅ (2026-07-28T17:50:19Z)
- [x] **TASK-0.3.2.2** — Install and start Docker Desktop with the WSL2 backend ✅ (2026-07-28T17:50:19Z)
- [x] **TASK-0.3.2.3** — Verify Docker daemon, Compose, and container execution ✅ (2026-07-28T18:06:57Z)

Docker Desktop responds through the daemon and WSL reports Ubuntu and
`docker-desktop` at version 2. Container execution and the project services still
require runtime verification.

### 0.3.3 Core Developer Tools

- [ ] **TASK-0.3.3.1** — Install Visual Studio with .NET and C++ workloads
- [ ] **TASK-0.3.3.2** — Install Visual Studio Code and required extensions
- [x] **TASK-0.3.3.3** — Install Git for Windows and Git LFS
- [x] **TASK-0.3.3.4** — Install PowerShell 7 and Windows Terminal ✅ (2026-07-28T17:50:19Z)
- [ ] **TASK-0.3.3.5** — Install CMake and Ninja
- [ ] **TASK-0.3.3.6** — Install OpenSSL

### 0.3.4 Python Environment

- [x] **TASK-0.3.4.1** — Install a usable Python 3.11 through `uv` ✅ (2026-07-29T17:22:46Z)
- [x] **TASK-0.3.4.2** — Create a usable Python 3.11 `.venv` ✅ (2026-07-29T17:22:46Z)
- [x] **TASK-0.3.4.3** — Install pinned CV/ML packages ✅ (2026-07-28T17:50:19Z)
- [x] **TASK-0.3.4.4** — Install development tools in the Python 3.11 environment ✅ (2026-07-28T17:50:19Z)
- [ ] **TASK-0.3.4.5** — Verify NVIDIA GPU and CUDA availability

`uv` created the Python 3.11.9 project `.venv` and installed the locked runtime, ML,
station, and development groups. Python native modules `asyncio` and `ssl` import
successfully, and `specproof-doctor` now validates NumPy, OpenCV, Open3D, PyTorch,
and pyrealsense2.

### 0.3.5 .NET SDK

- [x] **TASK-0.3.5.1** — Install .NET 10 LTS SDK
- [x] **TASK-0.3.5.2** — Pin the SDK in `global.json`
- [x] **TASK-0.3.5.3** — Verify restore and release build

### 0.3.6 Node.js and Frontend Tools

- [x] **TASK-0.3.6.1** — Install Node.js 24 LTS
- [x] **TASK-0.3.6.2** — Install pnpm
- [x] **TASK-0.3.6.3** — Verify lint, type-check, test, and production build

### 0.3.7 Database and Infrastructure Services

- [x] **TASK-0.3.7.1** — Define pinned local Compose services
- [x] **TASK-0.3.7.2** — Start PostgreSQL ✅ (2026-07-28T18:06:57Z)
- [x] **TASK-0.3.7.3** — Start Redis ✅ (2026-07-28T18:06:57Z)
- [x] **TASK-0.3.7.4** — Start MinIO ✅ (2026-07-28T18:06:57Z)
- [x] **TASK-0.3.7.5** — Start RabbitMQ ✅ (2026-07-28T18:06:57Z)
- [ ] **TASK-0.3.7.6** — Install PostgreSQL client tools
- [x] **TASK-0.3.7.7** — Verify all service protocols ✅ (2026-07-29T17:22:46Z)

All seven Compose containers start healthy. PostgreSQL `SELECT 1`, Redis `PING`,
RabbitMQ authenticated channel open, MinIO health, Prometheus health, Grafana health,
and Loki readiness respond successfully. Development PostgreSQL is published on
`localhost:55432` to avoid conflict with a local Windows PostgreSQL process.
Development PostgreSQL credentials are local-only:
`Username=Admin;Password=Admin@123`.

### 0.3.8 RealSense Camera SDK

- [ ] **TASK-0.3.8.1** — Install the qualified RealSense SDK
- [ ] **TASK-0.3.8.2** — Install RealSense Viewer
- [x] **TASK-0.3.8.3** — Install `pyrealsense2` in the Python 3.11 environment ✅ (2026-07-28T17:50:19Z)
- [ ] **TASK-0.3.8.4** — Validate camera enumeration and streaming

### 0.3.9 Monitoring Stack

- [x] **TASK-0.3.9.1** — Add pinned Prometheus service
- [x] **TASK-0.3.9.2** — Add pinned Grafana service
- [x] **TASK-0.3.9.3** — Add pinned Loki service
- [ ] **TASK-0.3.9.4** — Verify local dashboards

### 0.3.10 Repository Initialization

- [x] **TASK-0.3.10.1** — Initialize Git repository
- [x] **TASK-0.3.10.2** — Create `.gitignore`
- [x] **TASK-0.3.10.3** — Configure Git LFS attributes
- [x] **TASK-0.3.10.4** — Create root `README.md`
- [x] **TASK-0.3.10.5** — Create Phase 0 directory structure
- [x] **TASK-0.3.10.6** — Create `pyproject.toml`
- [x] **TASK-0.3.10.7** — Create `pnpm-workspace.yaml`
- [x] **TASK-0.3.10.8** — Create `Directory.Packages.props`
- [x] **TASK-0.3.10.9** — Create `global.json`
- [x] **TASK-0.3.10.10** — Verify the historical initial repository commit exists

No new commit was created during this implementation.

### 0.3.11 Environment Validation

- [x] **TASK-0.3.11.1** — Create `specproof-doctor`
- [x] **TASK-0.3.11.2** — Check host tools, protocols, Python CV packages, and optional hardware
- [x] **TASK-0.3.11.3** — Emit deterministic `PASS`, `FAIL`, and `SKIP` output
- [x] **TASK-0.3.11.4** — Add parsing, aggregation, protocol, and formatting tests

## 0.3 Verification Evidence

| Check | Status |
|-------|--------|
| Git and Git LFS | PASS |
| .NET 10 release build | PASS |
| Node 24, pnpm, frontend checks | PASS |
| Compose configuration | PASS |
| Doctor source tests | PASS, 34 tests on Python 3.11 with external plugin autoload disabled |
| Usable managed Python 3.11 | PASS |
| Docker daemon | PASS |
| Docker Compose containers | PASS, all seven healthy |
| Container-local service protocols | PASS |
| WSL2 | PASS |
| PowerShell 7 | PASS, version 7.6.4 |
| CMake, Ninja, OpenSSL | BLOCKED |
| RealSense SDK and camera stream | DEFERRED until hardware is available |
| NVIDIA/CUDA | DEFERRED unless GPU acceleration is required |

## 0.4 Exit Criteria

- [ ] All required host verification commands pass
- [x] `specproof-doctor` exits zero in the pinned Python 3.11 environment ✅ (2026-07-29T17:22:46Z)
- [x] Initial repository structure and historical initial commit exist
- [x] `docker compose up -d` starts all services ✅ (2026-07-29T17:22:46Z)
- [ ] Python, .NET, and Node environments are reproducible and usable
- [ ] RealSense and optional GPU requirements are resolved for the target capture workstation

See `docs/setup/PHASE-0-WINDOWS.md` for manual remediation. Phase 0 remains
`IN_PROGRESS` for workstation-level acceptance, but it no longer blocks software
module development.
