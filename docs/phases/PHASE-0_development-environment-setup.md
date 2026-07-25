# Phase 0 — Development Environment Setup

**Phase ID:** PHASE-0  
**Status:** `NOT_STARTED`  
**Created:** 2026-07-25T13:15:00Z  
**Last Updated:** 2026-07-25T13:15:00Z  
**Estimated Duration:** 1–2 weeks  
**Dependencies:** None  
**Language:** en  

---

## 0.1 Objective

Establish a fully reproducible, production-grade development environment on Windows 11 x64 that supports all SpecProof workloads: camera SDK, Python CV/ML, .NET backend, TypeScript frontend, Docker infrastructure, and CI/CD pipelines. Every tool installation must be verified and documented.

---

## 0.2 Prerequisites

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| OS | Windows 11 64-bit | Windows 11 Pro 64-bit |
| CPU | 6-core Intel/AMD | 8–16 core i7/i9 or Ryzen 7/9 |
| RAM | 16 GB | 32–64 GB |
| Storage | 512 GB NVMe | 1–2 TB NVMe |
| GPU | Integrated | NVIDIA RTX ≥12 GB VRAM |
| USB | USB 3.x port | Dedicated USB 3.x controller |
| Network | Gigabit Ethernet / Wi-Fi | Gigabit Ethernet |
| Security | TPM 2.0 preferred | TPM 2.0 + BitLocker |

---

## 0.3 Tasks

### 0.3.1 Windows System Preparation

- [ ] **TASK-0.3.1.1** — Verify Windows 11 version, architecture, and updates
- [ ] **TASK-0.3.1.2** — Enable Developer Mode
- [ ] **TASK-0.3.1.3** — Configure time synchronisation (NTP → UTC)
- [ ] **TASK-0.3.1.4** — Enable BitLocker (if supported)
- [ ] **TASK-0.3.1.5** — Install motherboard/chipset and USB-controller drivers

**Verification:**
```powershell
winver
Get-ComputerInfo | Select-Object WindowsProductName, WindowsVersion, OsBuildNumber
w32tm /query /status
```

### 0.3.2 WSL2 and Docker Desktop

- [ ] **TASK-0.3.2.1** — Install WSL2
- [ ] **TASK-0.3.2.2** — Install Docker Desktop (WSL2 backend)
- [ ] **TASK-0.3.2.3** — Verify Docker and Docker Compose

**Verification:**
```powershell
wsl --status
docker version
docker compose version
docker run --rm hello-world
```

### 0.3.3 Core Developer Tools

- [ ] **TASK-0.3.3.1** — Install Visual Studio 2022 (.NET + C++ workloads)
- [ ] **TASK-0.3.3.2** — Install Visual Studio Code with extensions
- [ ] **TASK-0.3.3.3** — Install Git for Windows + Git LFS
- [ ] **TASK-0.3.3.4** — Install PowerShell 7 + Windows Terminal
- [ ] **TASK-0.3.3.5** — Install CMake + Ninja
- [ ] **TASK-0.3.3.6** — Install OpenSSL

**Verification:**
```powershell
git --version
git lfs version
pwsh --version
cmake --version
ninja --version
code --version
```

### 0.3.4 Python Environment

- [ ] **TASK-0.3.4.1** — Install Python 3.11 via `uv`
- [ ] **TASK-0.3.4.2** — Create virtual environment
- [ ] **TASK-0.3.4.3** — Install core CV/ML packages (NumPy, SciPy, OpenCV, Open3D, PyTorch, ONNX Runtime)
- [ ] **TASK-0.3.4.4** — Install development tools (pytest, ruff, pyright)
- [ ] **TASK-0.3.4.5** — Verify GPU/CUDA availability

**Verification:**
```powershell
python --version
uv --version
nvidia-smi
python -c "import torch; print(torch.__version__); print(torch.cuda.is_available())"
python -c "import cv2, open3d, numpy; print('CV stack OK')"
```

### 0.3.5 .NET SDK

- [ ] **TASK-0.3.5.1** — Install .NET LTS SDK
- [ ] **TASK-0.3.5.2** — Configure `global.json` with SDK version
- [ ] **TASK-0.3.5.3** — Verify build and restore

**Verification:**
```powershell
dotnet --info
dotnet --list-sdks
```

### 0.3.6 Node.js and Frontend Tools

- [ ] **TASK-0.3.6.1** — Install Node.js LTS
- [ ] **TASK-0.3.6.2** — Install pnpm
- [ ] **TASK-0.3.6.3** — Verify toolchain

**Verification:**
```powershell
node --version
pnpm --version
```

### 0.3.7 Database and Infrastructure Services

- [ ] **TASK-0.3.7.1** — Create `docker-compose.yml` for local services
- [ ] **TASK-0.3.7.2** — Start PostgreSQL container
- [ ] **TASK-0.3.7.3** — Start Redis container
- [ ] **TASK-0.3.7.4** — Start MinIO (S3-compatible) container
- [ ] **TASK-0.3.7.5** — Start RabbitMQ container
- [ ] **TASK-0.3.7.6** — Install PostgreSQL client tools
- [ ] **TASK-0.3.7.7** — Verify all service connections

**Verification:**
```powershell
docker compose ps
psql -h localhost -U specproof -c "SELECT version();"
```

### 0.3.8 RealSense Camera SDK

- [ ] **TASK-0.3.8.1** — Install qualified RealSense SDK 2.0
- [ ] **TASK-0.3.8.2** — Install RealSense Viewer
- [ ] **TASK-0.3.8.3** — Install `pyrealsense2` Python binding
- [ ] **TASK-0.3.8.4** — Validate camera detection and streaming

**Verification:**
```powershell
python -c "import pyrealsense2 as rs; print('RealSense Python OK')"
```

### 0.3.9 Monitoring Stack

- [ ] **TASK-0.3.9.1** — Add Prometheus container to compose
- [ ] **TASK-0.3.9.2** — Add Grafana container to compose
- [ ] **TASK-0.3.9.3** — Add Loki container to compose
- [ ] **TASK-0.3.9.4** — Verify dashboards accessible

### 0.3.10 Repository Initialisation

- [ ] **TASK-0.3.10.1** — Initialise Git repository
- [ ] **TASK-0.3.10.2** — Create `.gitignore` (Python, .NET, Node, IDE, OS)
- [ ] **TASK-0.3.10.3** — Create `.gitattributes` for LFS
- [ ] **TASK-0.3.10.4** — Create `README.md` at repo root
- [ ] **TASK-0.3.10.5** — Create initial directory structure per spec
- [ ] **TASK-0.3.10.6** — Create `pyproject.toml` with dependency groups
- [ ] **TASK-0.3.10.7** — Create `pnpm-workspace.yaml`
- [ ] **TASK-0.3.10.8** — Create `Directory.Packages.props` for .NET
- [ ] **TASK-0.3.10.9** — Create `global.json`
- [ ] **TASK-0.3.10.10** — Initial commit

### 0.3.11 Environment Validation Script

- [ ] **TASK-0.3.11.1** — Create `specproof-doctor` diagnostic script
- [ ] **TASK-0.3.11.2** — Script must validate: OS, Git, Python, .NET, Node, Docker, DB, Camera SDK
- [ ] **TASK-0.3.11.3** — Output clear PASS/FAIL for each component
- [ ] **TASK-0.3.11.4** — Write automated tests for the doctor script itself

---

## 0.4 Test Cases (Auto-generated)

| Test ID | Test Description | Type | Expected Result |
|---------|-----------------|------|-----------------|
| T-0.001 | Git is installed and ≥ 2.40 | Smoke | Version string returned |
| T-0.002 | Python 3.11 is active | Smoke | `sys.version` starts with `3.11` |
| T-0.003 | .NET SDK is LTS version | Smoke | `dotnet --info` shows LTS |
| T-0.004 | Node.js is LTS | Smoke | Even major version number |
| T-0.005 | Docker Desktop is running | Smoke | `docker info` succeeds |
| T-0.006 | PostgreSQL accepts connections | Integration | `SELECT 1` returns `1` |
| T-0.007 | Redis accepts connections | Integration | `PING` returns `PONG` |
| T-0.008 | MinIO accepts connections | Integration | Health endpoint returns OK |
| T-0.009 | PyTorch imports successfully | Smoke | `import torch` no error |
| T-0.010 | OpenCV imports successfully | Smoke | `import cv2` no error |
| T-0.011 | Open3D imports successfully | Smoke | `import open3d` no error |
| T-0.012 | `specproof-doctor` passes all checks | E2E | All checks green |
| T-0.013 | Git LFS is installed and configured | Smoke | `git lfs version` returns version |
| T-0.014 | Directory structure matches spec | Validation | All required dirs exist |

---

## 0.5 Exit Criteria

- [ ] All verification commands pass
- [ ] `specproof-doctor` reports all green
- [ ] Initial Git commit with full directory structure
- [ ] `docker compose up` starts all infrastructure services
- [ ] Python, .NET, and Node environments are isolated and reproducible
- [ ] All test cases in section 0.4 pass
- [ ] Environment documented in `docs/tracking/PROGRESS.md`

---

## 0.6 Risks

| Risk | Mitigation |
|------|-----------|
| CUDA/PyTorch version mismatch | Use official PyTorch installer matrix; pin exact versions |
| Docker Desktop licensing | Verify license tier; alternative: Rancher Desktop |
| RealSense SDK version compatibility | Pin SDK version; test before upgrading |
| USB 3.x bandwidth issues | Use dedicated USB controller; test with camera |
