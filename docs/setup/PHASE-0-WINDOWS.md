# Phase 0 Windows Development Environment Setup

**Last Updated:** 2026-07-25T13:15:00Z  
**Timezone:** UTC  
**Language:** en

This guide covers workstation-level setup for SpecProof Phase 0. The repository provides configuration and diagnostics, but privileged installs and hardware validation remain manual host actions.

## Required Workstation Baseline

- Windows 11 Pro x64 with current Windows updates.
- Developer Mode enabled.
- System clock synchronised through Windows Time Service.
- BitLocker enabled when supported by the workstation security policy.
- Current motherboard, chipset, GPU, and USB-controller drivers installed.
- Dedicated USB 3.x controller recommended for RealSense camera validation.

Verification:

```powershell
winver
Get-ComputerInfo | Select-Object WindowsProductName, WindowsVersion, OsBuildNumber, OsArchitecture
w32tm /query /status
```

## WSL2 and Docker Desktop

Install WSL2, then install Docker Desktop and enable the WSL2 backend.

Verification:

```powershell
wsl --status
docker version
docker compose version
docker run --rm hello-world
```

Start SpecProof local infrastructure from the repository root:

```powershell
docker compose up -d
docker compose ps
```

Local service endpoints:

- PostgreSQL: `localhost:5432`, database `specproof`, user `specproof`.
- Redis: `localhost:6379`.
- MinIO API: `http://localhost:9000`.
- MinIO console: `http://localhost:9001`.
- RabbitMQ AMQP: `localhost:5672`.
- RabbitMQ management: `http://localhost:15672`.
- Prometheus: `http://localhost:9090`.
- Grafana: `http://localhost:3000`.
- Loki: `http://localhost:3100`.

The checked-in compose credentials are local development defaults only.

## Core Developer Tools

Install and verify:

- Visual Studio 2022 with .NET desktop, ASP.NET/web, and C++ desktop workloads.
- Visual Studio Code.
- Git for Windows and Git LFS.
- PowerShell 7 and Windows Terminal.
- CMake and Ninja.
- OpenSSL.

Verification:

```powershell
git --version
git lfs version
pwsh --version
cmake --version
ninja --version
code --version
openssl version
```

## Python Environment

SpecProof Phase 0 pins Python 3.11 and uses `uv` for environments and dependency groups.

Verification:

```powershell
python --version
uv --version
uv sync --group dev
uv run pytest tests/unit/tools/specproof_doctor -v
```

Install CV/ML and station groups after native prerequisites are installed:

```powershell
uv sync --group runtime --group ml --group station --group dev
uv run python -c "import cv2, open3d, numpy; print('CV stack OK')"
uv run python -c "import torch; print(torch.__version__); print(torch.cuda.is_available())"
uv run python -c "import pyrealsense2 as rs; print('RealSense Python OK')"
```

## .NET and Node.js

The repository pins .NET SDK `10.0.301` in `global.json` and expects Node.js `24.x` LTS.

Verification:

```powershell
dotnet --info
dotnet --list-sdks
node --version
pnpm --version
```

## RealSense SDK

Install the qualified Intel RealSense SDK 2.0 Windows release and RealSense Viewer. Validate camera streaming natively on Windows rather than through WSL2 USB forwarding.

Verification:

```powershell
uv run python -c "import pyrealsense2 as rs; print('RealSense Python OK')"
```

Manual validation:

- Open RealSense Viewer.
- Confirm the camera is detected.
- Validate depth and RGB streams.
- Record the camera model, firmware version, SDK version, USB controller, cable, and stream profile.

## SpecProof Doctor

Run diagnostics from the repository root:

```powershell
uv run specproof-doctor
```

Optional hardware gates:

```powershell
uv run specproof-doctor --require-gpu --require-realsense
```

`PASS` means the component is available, `FAIL` means a required component is missing or unhealthy, and `SKIP` means an optional hardware component is not required for the current workstation.
