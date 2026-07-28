# Phase 0 — Development Environment Setup

**Phase ID:** PHASE-0  
**Status:** `IN_PROGRESS`
**Created:** 2026-07-25T13:15:00Z  
**Last Updated:** 2026-07-28T16:34:20Z
**Estimated Duration:** 1–2 weeks  
**Dependencies:** None  
**Language:** en

## 0.1 Objective

Provide reproducible repository configuration and diagnostics for a Windows 11 development workstation. Privileged host configuration remains a documented manual responsibility and is verified by `specproof-doctor`.

## 0.2 Tasks

### 0.3.1 Windows System Preparation

- [ ] **TASK-0.3.1.1** — Verify Windows 11 version, architecture, and updates
- [ ] **TASK-0.3.1.2** — Enable Developer Mode
- [ ] **TASK-0.3.1.3** — Configure NTP and UTC time synchronization
- [ ] **TASK-0.3.1.4** — Enable BitLocker where supported
- [ ] **TASK-0.3.1.5** — Install qualified chipset and USB-controller drivers

### 0.3.2 WSL2 and Docker Desktop

- [ ] **TASK-0.3.2.1** — Install and verify WSL2
- [ ] **TASK-0.3.2.2** — Install and start Docker Desktop with the WSL2 backend
- [ ] **TASK-0.3.2.3** — Verify Docker daemon, Compose, and container execution

The Docker CLI and Compose plugin are present, but the daemon is not running. WSL status is inaccessible from the current environment.

### 0.3.3 Core Developer Tools

- [ ] **TASK-0.3.3.1** — Install Visual Studio with .NET and C++ workloads
- [ ] **TASK-0.3.3.2** — Install Visual Studio Code and required extensions
- [x] **TASK-0.3.3.3** — Install Git for Windows and Git LFS
- [ ] **TASK-0.3.3.4** — Install PowerShell 7 and Windows Terminal
- [ ] **TASK-0.3.3.5** — Install CMake and Ninja
- [ ] **TASK-0.3.3.6** — Install OpenSSL

### 0.3.4 Python Environment

- [ ] **TASK-0.3.4.1** — Install a usable Python 3.11 through `uv`
- [ ] **TASK-0.3.4.2** — Create a usable Python 3.11 `.venv`
- [ ] **TASK-0.3.4.3** — Install pinned CV/ML packages
- [ ] **TASK-0.3.4.4** — Install development tools in the Python 3.11 environment
- [ ] **TASK-0.3.4.5** — Verify NVIDIA GPU and CUDA availability

`uv.lock` and Python packaging are reproducible. `uv` downloaded Python 3.11.15, but Windows Application Control blocks its `_socket.pyd`; therefore the managed interpreter and project `.venv` are not usable. Repository validation used an ignored Python 3.14 fallback environment and does not close these workstation tasks.

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
- [ ] **TASK-0.3.7.2** — Start PostgreSQL
- [ ] **TASK-0.3.7.3** — Start Redis
- [ ] **TASK-0.3.7.4** — Start MinIO
- [ ] **TASK-0.3.7.5** — Start RabbitMQ
- [ ] **TASK-0.3.7.6** — Install PostgreSQL client tools
- [ ] **TASK-0.3.7.7** — Verify all service protocols

The Compose definition validates. Runtime checks remain blocked until Docker Desktop is running. Development PostgreSQL credentials are local-only: `Username=Admin;Password=Admin@123`.

### 0.3.8 RealSense Camera SDK

- [ ] **TASK-0.3.8.1** — Install the qualified RealSense SDK
- [ ] **TASK-0.3.8.2** — Install RealSense Viewer
- [ ] **TASK-0.3.8.3** — Install `pyrealsense2` in the Python 3.11 environment
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
| Doctor source tests | PASS in fallback interpreter |
| Usable managed Python 3.11 | BLOCKED by Windows Application Control |
| Docker daemon and service protocols | BLOCKED |
| WSL2 | BLOCKED |
| PowerShell 7, CMake, Ninja | BLOCKED |
| RealSense SDK and camera stream | BLOCKED |
| NVIDIA/CUDA | BLOCKED or unavailable |

## 0.4 Exit Criteria

- [ ] All required host verification commands pass
- [ ] `specproof-doctor` exits zero in the pinned Python 3.11 environment
- [x] Initial repository structure and historical initial commit exist
- [ ] `docker compose up -d` starts all services
- [ ] Python, .NET, and Node environments are reproducible and usable
- [ ] RealSense and optional GPU requirements are resolved for the target workstation

See `docs/setup/PHASE-0-WINDOWS.md` for manual remediation. Phase 0 remains `IN_PROGRESS`.
