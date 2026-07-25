# SpecProof — Windows Development Environment and Cross-Platform Release Requirements

**Document type:** Engineering workstation, software toolchain, repository, build, test, packaging, and release specification  
**Version:** 2.0  
**Date:** 25 July 2026  
**Development host:** Windows 11 x64  
**Release targets:** Windows and Linux x64, with macOS support for platform applications where hardware dependencies permit  
**Project stage:** Research prototype through production pilot

---

## 1. Purpose

This document defines the development environment for building the complete SpecProof production system on Windows while ensuring that released software remains cross-platform.

It covers:

- Windows developer workstation requirements.
- Native RGB-D camera development on Windows.
- Computer-vision, 3D geometry, and machine-learning tooling.
- Cross-platform backend, frontend, station-agent, and shared-library design.
- Local infrastructure through Docker Desktop and WSL2.
- Windows and Linux build and test requirements.
- Release packaging, signing, versioning, and deployment.
- Production-readiness controls for a factory measurement appliance.

The product described in the project material combines a calibrated RGB-D capture station, controlled lighting, 3D garment-surface reconstruction, landmark location, point-of-measure calculation, graded-spec validation, and a signed evidence record. The development environment must therefore support both hardware-connected metrology work and ordinary platform software development.

---

## 2. Primary Engineering Decision

The entire project may be developed from a Windows 11 workstation.

Use the following split:

| Workload | Windows development approach |
|---|---|
| RealSense camera capture | Run natively on Windows |
| Camera calibration and diagnostics | Run natively on Windows |
| Python CV/ML development | Run natively on Windows in a virtual environment |
| NVIDIA GPU training and inference | Run natively on Windows with a qualified CUDA/PyTorch stack |
| ASP.NET Core API | Run natively on Windows; publish for Windows and Linux |
| Angular or React web application | Run natively on Windows; browser-based cross-platform release |
| PostgreSQL, Redis, MinIO, message broker | Run in Docker Desktop Linux containers |
| Linux compatibility validation | Run in Docker, WSL2, and CI Linux runners |
| Production station qualification | Test on both Windows and the selected Linux appliance image |

The RGB-D camera should not depend on WSL2 USB forwarding for normal development. Camera access, firmware updates, RealSense Viewer, capture stability tests, and calibration should run directly on Windows.

---

## 3. Cross-Platform Product Policy

### 3.1 Required release platforms

The initial production release shall support:

1. **Windows 11 x64** for development, demonstrations, pilot stations, service tooling, and supported customer installations.
2. **Ubuntu Linux x64** for unattended factory stations and server/container deployment.
3. **Modern web browsers** on Windows, Linux, and macOS for operator and administration interfaces.

### 3.2 Optional later platforms

These are not required for the first production release unless commercially justified:

- Windows on ARM64.
- Linux ARM64.
- macOS desktop station software.
- Android or iOS operator applications.

### 3.3 Cross-platform definition

Cross-platform means that:

- Core domain logic compiles and runs on Windows and Linux.
- Measurement rules produce equivalent results on supported platforms.
- Stored capture formats are platform-neutral.
- API contracts and evidence records are independent of the host OS.
- Build and release pipelines generate separate platform artefacts from the same source revision.
- Platform-specific code is isolated behind interfaces.

It does not mean that every hardware SDK behaves identically on every operating system. The camera integration layer must be qualified separately per supported OS, SDK, firmware, USB controller, and stream profile.

---

## 4. Architecture Constraints for Portability

### 4.1 Separate platform-dependent and platform-independent code

#### Platform-dependent layer

- RealSense device enumeration.
- USB and device permissions.
- Camera firmware tools.
- Native SDK loading.
- Windows services and Linux systemd integration.
- GPU runtime discovery.
- Local secure-key storage.
- Installer and auto-update integration.

#### Platform-independent layer

- RGB-D capture schema.
- Calibration schema.
- Depth filtering.
- Point-cloud and mesh processing.
- Garment segmentation.
- Landmark inference.
- Drape compensation.
- Point-of-measure compiler.
- Tolerance validation.
- Evidence-record generation.
- API contracts.
- Database models.
- Audit and reporting logic.

### 4.2 Mandatory abstraction boundaries

Use explicit interfaces such as:

```text
ICameraProvider
ICalibrationProvider
ICaptureRepository
IInferenceRuntime
IMeasurementEngine
ISpecCompiler
IEvidenceSigner
IObjectStore
IPlatformKeyStore
IStationServiceHost
```

The application layer must not call Windows registry APIs, Windows paths, shell commands, or native RealSense functions directly.

### 4.3 Path handling

- Use `Path.Combine` in .NET.
- Use `pathlib.Path` in Python.
- Do not hard-code drive letters or slash direction.
- Store logical object keys rather than local absolute file paths in the database.
- Treat file names as case-sensitive during automated testing, even on Windows.

### 4.4 Process and shell handling

- Do not assume PowerShell, `cmd.exe`, Bash, or `/bin/sh` is always present.
- Put platform-specific scripts in separate folders.
- Prefer application APIs over shelling out.
- When an external process is necessary, define separate Windows and Linux implementations.

### 4.5 Data formats

Use platform-neutral formats:

- JSON or MessagePack for contracts and metadata.
- PNG/TIFF for lossless images where suitable.
- RealSense `.bag` files for source replay when supported.
- A project capture package containing RGB, depth, intrinsics, extrinsics, timestamps, and checksums.
- PLY/PCD for diagnostic point clouds.
- glTF/GLB or a documented mesh format for visualisation.
- Parquet for analytical datasets.
- UTF-8 without BOM for source-controlled text files unless a tool requires otherwise.

---

## 5. Windows Development Workstation Requirements

### 5.1 Minimum workstation

| Component | Minimum |
|---|---|
| Operating system | Windows 11 64-bit |
| CPU | Modern 6-core Intel or AMD processor |
| RAM | 16 GB |
| Storage | 512 GB NVMe SSD |
| GPU | Integrated GPU or entry-level discrete GPU |
| USB | Stable USB 3.x port for the RGB-D camera |
| Network | Gigabit Ethernet or reliable Wi-Fi |
| Security | TPM 2.0 and BitLocker preferred |

This configuration is sufficient for camera integration, backend/frontend development, basic point-cloud work, and small-model inference.

### 5.2 Recommended production-development workstation

| Component | Recommended |
|---|---|
| Operating system | Windows 11 Pro 64-bit |
| CPU | Intel Core i7/i9 or AMD Ryzen 7/9, 8–16 cores |
| RAM | 32–64 GB |
| Storage | 1–2 TB NVMe SSD |
| Dataset storage | Additional 4–8 TB SSD/HDD or network storage |
| GPU | NVIDIA RTX GPU with at least 12 GB VRAM |
| USB | Dedicated USB 3.x controller or verified motherboard port |
| Displays | Two monitors recommended |
| Power | UPS for long training, capture, and calibration runs |
| Security | TPM 2.0, BitLocker, Secure Boot |

For heavier transformer vision models, large 3D experiments, or synthetic-data generation, use 24 GB or more GPU VRAM and 64 GB or more system RAM.

---

## 6. Capture Rig Hardware

Initial reference configuration:

- Intel RealSense D435 or a validated equivalent RGB-D camera.
- Short, high-quality USB 3.x cable with strain relief.
- Fixed camera mount.
- Controlled LED panels with diffusers.
- Rigid aluminium-extrusion frame.
- Dimensionally stable matte capture surface.
- Calibration target with known dimensions.
- Optional lighting controller.
- Optional barcode scanner for garment/sample identification.

The RealSense SDK officially supports Windows 10 and Windows 11. The project must still qualify the exact camera model, firmware, SDK build, USB controller, cable, stream profile, and lighting configuration used in production.

### 6.1 Lab and verification equipment

- Calibrated steel rule or traceable dimensional artefact.
- Reference tailor's tape under a documented manual protocol.
- Spirit level or digital inclinometer.
- Lux meter.
- Colour/grey card.
- Matte calibration boards.
- Temperature and humidity logger.
- USB bandwidth and power diagnostic tools.

---

## 7. Windows Software Toolchain

### 7.1 Core tools

Install:

- Visual Studio 2022 with .NET and C++ workloads.
- Visual Studio Code.
- Git for Windows.
- Git LFS.
- PowerShell 7.
- Windows Terminal.
- CMake.
- Ninja.
- Python 3.11.
- Node.js LTS.
- pnpm.
- .NET LTS SDK.
- Docker Desktop using the WSL2 backend.
- PostgreSQL client tools.
- OpenSSL.
- Optional GitHub Desktop.

### 7.2 Recommended package managers

Use one or more of:

- `winget` for workstation tooling.
- `uv` for Python environments and lock files.
- `pnpm` for JavaScript/TypeScript packages.
- NuGet with central package management for .NET.
- vcpkg or Conan only for native C++ dependencies that cannot be handled otherwise.

Do not depend on untracked global Python or Node packages.

---

## 8. RealSense Development on Windows

### 8.1 Installation

Install the qualified RealSense SDK 2.0 Windows release or build it from source using Visual Studio and CMake when required.

Install and validate:

- RealSense Viewer.
- Depth Quality Tool where supplied.
- Firmware update utility.
- SDK examples.
- Python binding `pyrealsense2` when Python owns capture.

### 8.2 Initial validation

Verify:

1. Camera detection by serial number.
2. USB 3.x connection speed.
3. Simultaneous RGB and depth streaming.
4. Depth-to-colour alignment.
5. Intrinsics and extrinsics retrieval.
6. Exposure and gain control.
7. Recording and replay.
8. Thirty-minute minimum stability run.
9. Restart after unplug/replug.
10. Recovery after application crash or forced termination.

### 8.3 Capture-service rule

The camera acquisition service shall run natively on Windows during development.

Do not make the normal capture workflow depend on:

- WSL2 USB/IP forwarding.
- A conventional VM USB translation layer.
- Remote-desktop camera redirection.
- Browser-only camera APIs.

### 8.4 Camera interface

```text
CameraProvider
  enumerate_devices()
  open(serial_number)
  configure(stream_profile)
  get_device_info()
  get_intrinsics()
  get_extrinsics()
  get_depth_scale()
  start()
  capture_aligned_rgbd()
  record_capture()
  health()
  stop()
```

Create separate adapters for Windows and Linux only where the SDK behaviour genuinely differs. Keep the public capture contract identical.

---

## 9. Python Computer-Vision and ML Environment

### 9.1 Python version

Use Python 3.11 as the initial qualified version. Upgrade only after the complete camera, OpenCV, Open3D, PyTorch, ONNX, and annotation stack passes regression tests.

### 9.2 Environment setup

Example using `uv` in PowerShell:

```powershell
winget install astral-sh.uv
uv python install 3.11
uv venv --python 3.11
.\.venv\Scripts\Activate.ps1
uv sync --frozen
```

### 9.3 Core Python packages

- NumPy.
- SciPy.
- pandas.
- OpenCV.
- Open3D.
- scikit-image.
- scikit-learn.
- Shapely.
- trimesh.
- PyTorch and torchvision.
- ONNX.
- ONNX Runtime.
- Albumentations.
- Pydantic.
- pytest.
- Ruff.
- Pyright or mypy.

### 9.4 GPU environment

PyTorch provides Windows packages and supports CUDA-capable NVIDIA GPUs. Select the supported Windows/Pip/CUDA combination from the official installer matrix instead of choosing CUDA and PyTorch versions independently.

Verification:

```powershell
nvidia-smi
python -c "import torch; print(torch.__version__); print(torch.cuda.is_available())"
python -c "import cv2, open3d, numpy; print('CV stack OK')"
```

### 9.5 Portable inference strategy

Training may use PyTorch, but production inference should support one or more portable runtimes:

- ONNX Runtime CPU.
- ONNX Runtime CUDA.
- OpenVINO where benchmarked and justified.
- Native PyTorch only when packaging and performance are acceptable.

Every exported model must have:

- Model version.
- Input/output schema.
- Pre-processing version.
- Post-processing version.
- Training dataset version.
- Evaluation report.
- SHA-256 checksum.
- Supported runtime and hardware matrix.

---

## 10. Backend and Platform Services

### 10.1 Recommended backend

Use ASP.NET Core on the current .NET LTS release.

Recommended components:

- ASP.NET Core Web API or Minimal APIs.
- Entity Framework Core.
- PostgreSQL provider.
- FluentValidation where appropriate.
- OpenAPI.
- OpenTelemetry.
- Background services for station synchronisation and processing jobs.

.NET and ASP.NET Core are cross-platform and can be built and published for Windows and Linux from the same source base.

### 10.2 Python service boundary

Keep camera, geometry, and ML-heavy processing in Python/C++ services where that produces the best SDK and library support.

Use one of these integration patterns:

1. Local gRPC between the .NET station host and Python measurement engine.
2. Local HTTP over loopback for early development.
3. Message-based jobs for asynchronous processing.
4. Embedded Python only after careful packaging and fault-isolation review.

Prefer gRPC or a documented process boundary for production so native crashes or model failures do not terminate the full station application.

### 10.3 Cross-platform publishing

Generate runtime-specific packages:

```powershell
dotnet publish -c Release -r win-x64 --self-contained true
dotnet publish -c Release -r linux-x64 --self-contained true
```

Use framework-dependent deployment only when the target runtime lifecycle is centrally managed.

---

## 11. Web Application

Recommended frontend:

- Angular with TypeScript, or React with TypeScript and Vite.

Required modules:

- Station registration.
- Live camera preview.
- Calibration workflow.
- Garment and SKU selection.
- Tech-pack import and mapping.
- Capture progress.
- Measurement overlays.
- Pass/fail/manual-review display.
- Evidence-record inspection.
- Device health.
- User, role, and permission management.
- Reporting and export.

Cross-platform requirements:

- Browser-based UI.
- No ActiveX, COM, registry, or Internet Explorer dependencies.
- Test on current Chrome and Edge; include Firefox where commercially required.
- Use generated OpenAPI clients.
- Use responsive layouts for standard workstation displays.

---

## 12. Data and Infrastructure Services on Windows

Use Docker Desktop with the WSL2 backend for Linux containers.

Local services:

- PostgreSQL.
- MinIO or another S3-compatible object store.
- Redis.
- RabbitMQ when durable messaging is required.
- MLflow.
- Label Studio or CVAT.
- Prometheus.
- Grafana.
- Loki or an equivalent logging service.

The Docker documentation identifies the WSL2 backend as the default and suitable for the majority of Docker Desktop users on Windows.

### 12.1 Host versus container rule

Run these directly on Windows:

- Camera capture.
- RealSense Viewer and firmware tools.
- Hardware calibration utility.
- Device diagnostics.
- IDEs and interactive debugging.

Run these in Linux containers where practical:

- PostgreSQL.
- Redis.
- MinIO.
- RabbitMQ.
- Monitoring stack.
- Platform API for Linux compatibility testing.
- CI-like integration environments.

### 12.2 Storage rule

Do not store large captures directly in ordinary PostgreSQL columns.

Store captures in object storage and retain in PostgreSQL:

- Object key.
- Content type.
- Size.
- SHA-256 checksum.
- Station ID.
- Capture ID.
- Retention category.
- Encryption status.
- Created timestamp.

---

## 13. Repository Structure

```text
specproof/
├── README.md
├── global.json
├── Directory.Packages.props
├── pyproject.toml
├── uv.lock
├── pnpm-workspace.yaml
├── docker-compose.yml
├── docs/
│   ├── architecture/
│   ├── adr/
│   ├── calibration/
│   ├── measurement-protocols/
│   ├── release/
│   └── security/
├── apps/
│   ├── station-host/              # .NET cross-platform host
│   ├── capture-service/           # Python/C++ camera adapter
│   ├── measurement-service/       # Python geometry/ML pipeline
│   ├── platform-api/              # ASP.NET Core
│   ├── operator-ui/               # Angular/React
│   └── admin-ui/
├── packages/
│   ├── contracts/
│   ├── camera-abstractions/
│   ├── calibration/
│   ├── geometry/
│   ├── landmark-graph/
│   ├── pom-ontology/
│   ├── pom-compiler/
│   ├── measurement-engine/
│   ├── decision-engine/
│   └── evidence-record/
├── native/
│   ├── windows/
│   └── linux/
├── ml/
│   ├── datasets/
│   ├── annotations/
│   ├── training/
│   ├── evaluation/
│   ├── exports/
│   └── model-cards/
├── infra/
│   ├── docker/
│   ├── compose/
│   ├── windows/
│   ├── linux/
│   └── monitoring/
├── installers/
│   ├── windows/
│   └── linux/
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── contract/
│   ├── regression/
│   ├── cross-platform/
│   ├── hardware-in-loop/
│   └── acceptance/
├── tools/
│   ├── specproof-doctor/
│   ├── calibration-cli/
│   ├── capture-replay/
│   ├── dataset-import/
│   └── benchmark/
└── .github/workflows/
```

---

## 14. Windows Setup Procedure

## Step 1 — Prepare Windows

1. Install Windows 11 Pro 64-bit.
2. Apply security and driver updates.
3. Enable BitLocker.
4. Enable Developer Mode if required.
5. Install current motherboard/chipset and USB-controller drivers.
6. Configure reliable time synchronisation.
7. Create separate administrator and daily development accounts where practical.

Verification:

```powershell
winver
Get-ComputerInfo | Select-Object WindowsProductName, WindowsVersion, OsBuildNumber
w32tm /query /status
```

## Step 2 — Install WSL2 and Docker Desktop

```powershell
wsl --install
wsl --update
wsl --status
```

Install Docker Desktop and select the WSL2 backend.

Verification:

```powershell
docker version
docker compose version
docker run --rm hello-world
```

WSL2 is used for Linux tooling and container support, not as the primary camera host.

## Step 3 — Install developer tools

Install Visual Studio 2022, VS Code, Git, Git LFS, PowerShell 7, CMake, Ninja, Python, Node.js, pnpm, and .NET SDK.

Verification:

```powershell
git --version
git lfs version
pwsh --version
cmake --version
ninja --version
python --version
node --version
pnpm --version
dotnet --info
```

## Step 4 — Install and verify RealSense

1. Install the qualified RealSense SDK.
2. Connect the camera directly to USB 3.x.
3. Open RealSense Viewer.
4. Record camera serial, firmware, and SDK versions.
5. Validate aligned RGB and depth.
6. Record a test `.bag` capture.
7. Replay the capture.
8. Run a thirty-minute stability test.

## Step 5 — Configure Python

```powershell
uv python install 3.11
uv venv --python 3.11
.\.venv\Scripts\Activate.ps1
uv sync --frozen
```

Verification:

```powershell
python -c "import pyrealsense2 as rs; print('RealSense Python OK')"
python -c "import cv2, open3d, torch; print('Vision environment OK')"
```

## Step 6 — Configure .NET and frontend

```powershell
dotnet restore
pnpm install --frozen-lockfile
```

Verification:

```powershell
dotnet build -c Debug
pnpm lint
pnpm test
pnpm build
```

## Step 7 — Start local services

```powershell
docker compose up -d postgres minio redis rabbitmq mlflow prometheus grafana
```

Then run database migrations and create development object-storage buckets.

## Step 8 — Run station diagnostics

Provide one cross-platform command:

```powershell
specproof doctor
```

It must validate:

- OS and architecture.
- Camera SDK and firmware.
- Camera serial number.
- USB connection speed.
- Required stream profile.
- Calibration presence and age.
- CPU, RAM, and disk.
- GPU runtime where configured.
- Database and object-storage connectivity.
- System clock health.
- Local certificate and signing-key access.
- Lighting controller or manual-lighting checklist.

## Step 9 — Capture calibration and baseline datasets

Capture:

- Empty surface.
- Dark frame.
- Uniform-light frame.
- RGB-depth alignment target.
- Known-dimensional artefacts.
- Repeated garment placements.
- Multiple fabric colours and reflectance levels.

Record station ID, camera serial, firmware, SDK, exposure settings, lighting settings, temperature, humidity, and operator.

## Step 10 — Execute smoke test

The test must:

1. Capture aligned RGB-D frames.
2. Save a platform-neutral capture package.
3. Generate a point cloud.
4. Detect the reference plane.
5. Measure a known artefact.
6. Render a measurement overlay.
7. Create an evidence record.
8. Verify hashes.
9. Persist metadata and object references.
10. Replay the same capture on Windows and Linux and compare results.

---

## 15. Cross-Platform Build and Test Matrix

Every pull request must run at least:

| Test | Windows runner | Linux runner |
|---|---:|---:|
| .NET restore/build | Required | Required |
| .NET unit tests | Required | Required |
| Python lint/type checks | Required | Required |
| Python unit tests | Required | Required |
| Frontend lint/test/build | Required | Required |
| Contract tests | Required | Required |
| Database integration tests | Required | Required |
| ONNX inference smoke test | Required | Required |
| Capture-replay regression | Required | Required |
| Installer/package test | Release branch | Release branch |
| Hardware-in-loop camera test | Qualified Windows agent | Qualified Linux agent |

### 15.1 Numeric reproducibility

Define tolerances for cross-platform numeric differences.

Do not require bit-for-bit equality for every floating-point geometry operation unless the implementation guarantees it. Require:

- Same pass/fail result.
- Measurement differences below an approved tolerance.
- Same ruleset and model versions.
- Same evidence inputs and hashes.
- Documented exceptions for GPU kernels or native libraries.

### 15.2 Replay-first testing

Maintain a versioned capture-replay corpus so Windows and Linux builds can run identical inputs without a camera.

Include:

- Valid captures.
- Low-light captures.
- Missing-depth regions.
- Reflective or black fabric.
- Folded and occluded landmarks.
- Incorrect camera height.
- Calibration-expired cases.
- Corrupted files.
- Interrupted capture packages.

---

## 16. Dependency Management

### 16.1 Python

- Commit `pyproject.toml` and `uv.lock`.
- Separate runtime, development, training, station, and documentation dependency groups.
- Build Windows and Linux lock validation in CI.
- Produce platform wheels or packaged environments for native dependencies.
- Generate a software bill of materials for releases.

### 16.2 .NET

- Pin the SDK with `global.json`.
- Use central package management.
- Enable nullable reference types.
- Treat warnings as errors in core projects.
- Avoid Windows-only packages in shared projects.
- Mark any platform-specific assembly clearly.

### 16.3 TypeScript

- Use Node.js LTS.
- Use `pnpm` and commit the lock file.
- Enable strict TypeScript.
- Run formatting, linting, tests, and production build in CI.

### 16.4 Native libraries

Pin and document:

- RealSense SDK.
- Camera firmware.
- CMake.
- Visual C++ runtime.
- GCC/Clang version for Linux.
- OpenCV.
- Open3D.
- CUDA and GPU driver.
- ONNX Runtime.

---

## 17. Packaging and Release

### 17.1 Release artefacts

Produce separate signed artefacts:

#### Windows

- Station installer: MSIX, MSI, or signed bootstrapper.
- Windows service package.
- Camera/measurement runtime bundle.
- Operator application or local web-host package.
- Diagnostic and support bundle.

#### Linux

- Debian package, OCI container, or signed installation bundle.
- systemd service definitions.
- Udev rules where required.
- Camera/measurement runtime bundle.
- Diagnostic and support bundle.

#### Platform services

- Versioned OCI container images.
- Database migration package.
- Web static artefact or container.
- SBOM.
- Checksums.
- Release notes.

### 17.2 Code signing

- Sign Windows executables and installers with an organisation-controlled code-signing certificate.
- Sign container images and Linux packages.
- Publish SHA-256 checksums.
- Store signing keys in managed secure hardware or a protected signing service.
- Never place production signing keys on ordinary developer machines.

### 17.3 Versioning

Use one product release version with component versions recorded separately:

```text
Product release: 1.0.0
Station host: 1.0.0
Capture service: 1.0.0
Measurement engine: 1.2.0
Model: garment-landmarks-0.8.3
Ontology: 2026.07.01
Ruleset: brand-style-size revision
Calibration: station-specific revision
```

Every evidence record must include the exact versions used.

### 17.4 Update mechanism

The station updater must support:

- Signed packages only.
- Staged rollout.
- Rollback.
- Database/schema compatibility checks.
- Model and ruleset compatibility checks.
- Offline update package.
- Update audit history.
- Prevention of automatic camera firmware changes outside a qualified release.

---

## 18. Production Station Options

### Option A — Windows production station

Use when:

- The customer requires Windows.
- Support staff are Windows-oriented.
- Native SDK behaviour is more stable for the selected camera.
- Group Policy and enterprise endpoint management are available.

Recommended controls:

- Windows 11 IoT Enterprise or managed Windows 11 Pro/Enterprise where licensing permits.
- Kiosk or dedicated station account.
- Windows Service for background components.
- Controlled Windows Update rings.
- Application allow-listing.
- BitLocker.
- Remote support with audited access.

### Option B — Ubuntu Linux production station

Use when:

- An unattended appliance is preferred.
- Lower OS overhead and simpler service supervision are priorities.
- Container-first deployment is required.
- The complete camera and GPU stack is qualified on the chosen hardware.

Recommended controls:

- Fixed Ubuntu LTS image and kernel.
- systemd-managed services.
- Controlled package repositories.
- Full-disk encryption where operationally feasible.
- SSH keys and audited support access.
- Immutable or image-based updates where practical.

### Release rule

Windows may be the main development and initial pilot platform, but a Linux production claim may only be made after hardware-in-loop, calibration, performance, recovery, and measurement-equivalence testing passes on the exact Linux target.

---

## 19. Security Requirements

- No secrets in source control.
- Per-station device identity.
- TLS for all remote communication.
- Certificate rotation.
- Encryption at rest for sensitive captures.
- Role-based access control.
- Append-only audit events.
- Signed evidence records.
- Secure local key storage through Windows CNG/DPAPI/TPM or Linux TPM/secure key store.
- Dependency and container vulnerability scanning.
- SBOM generation.
- Least-privilege Windows services and Linux service users.
- Configurable retention and deletion of garment imagery.

The tamper-evident record should bind at minimum:

- Capture checksum.
- Station identity.
- Calibration revision.
- Camera serial and firmware.
- Capture software version.
- Model version.
- Ontology/compiler version.
- Tech-pack/spec revision.
- Measurement result.
- Timestamp.
- Signer identity and signature metadata.

---

## 20. Observability and Support

Use:

- Structured JSON logs.
- OpenTelemetry traces and metrics.
- Prometheus-compatible metrics.
- Grafana dashboards.
- Central log aggregation.
- Application error tracking.

Minimum station metrics:

- RGB and depth FPS.
- Dropped frames.
- Invalid-depth percentage.
- USB disconnects.
- Capture latency.
- Inference latency by stage.
- Measurement latency.
- CPU, RAM, GPU, disk, and temperature.
- Calibration age.
- Offline queue depth.
- Synchronisation status.
- Pass/fail/review counts.

Support bundle must redact credentials and include:

- OS and architecture.
- Hardware inventory.
- Camera serial, firmware, and SDK.
- Application versions.
- Recent logs.
- Health-check results.
- Calibration metadata.
- Network test results.
- Crash dumps where permitted.

---

## 21. Quality Gates Before Production Release

A release is not production-ready until all applicable gates pass:

1. Windows and Linux CI are green.
2. Windows camera hardware-in-loop tests pass.
3. Linux camera hardware-in-loop tests pass for Linux-supported releases.
4. Cross-platform replay results are within approved tolerances.
5. Calibration and known-artefact accuracy tests pass.
6. Thirty-minute and eight-hour stability tests pass.
7. USB disconnect and recovery tests pass.
8. Offline operation and later synchronisation pass.
9. Upgrade and rollback pass.
10. Installer and uninstall tests pass.
11. Security scan and SBOM review pass.
12. Evidence-record verification passes independently.
13. Backup and restore tests pass.
14. Operator acceptance tests pass.
15. Release documentation and support runbooks are complete.

---

## 22. Recommended Initial Technology Selection

| Area | Initial selection |
|---|---|
| Development OS | Windows 11 Pro x64 |
| Camera runtime | Native RealSense SDK on Windows |
| Camera service | Python 3.11 or C++ behind a stable IPC contract |
| CV/geometry | OpenCV, Open3D, NumPy, SciPy, trimesh |
| ML training | PyTorch on Windows with NVIDIA CUDA |
| Portable inference | ONNX Runtime CPU/CUDA |
| Station host | ASP.NET Core Worker Service or cross-platform console/service host |
| Platform API | ASP.NET Core .NET LTS |
| Web UI | Angular or React with TypeScript |
| Database | PostgreSQL in Docker for development |
| Object storage | MinIO/S3-compatible storage |
| Messaging | Redis initially; RabbitMQ when durability requires it |
| Local infrastructure | Docker Desktop with WSL2 backend |
| Production server deployment | Linux containers |
| Station release | Windows x64 and qualified Ubuntu Linux x64 packages |
| CI | Windows and Ubuntu hosted runners plus hardware agents |

---

## 23. Final Recommendation

Develop the full SpecProof product on Windows 11.

Use native Windows camera capture and calibration, native Windows Python/CUDA development, ASP.NET Core for the cross-platform platform layer, and Docker Desktop for local infrastructure. Keep Windows-specific functionality behind adapters, publish runtime-specific Windows and Linux artefacts, and require automated cross-platform replay and hardware-in-loop tests before release.

The recommended release sequence is:

1. Windows developer build.
2. Windows integrated prototype.
3. Windows pilot station.
4. Linux container validation for platform services.
5. Ubuntu station qualification on the selected mini PC.
6. Dual Windows/Linux production release after measurement-equivalence and recovery testing.

This approach allows all day-to-day engineering to remain on Windows without locking the final product to Windows.

---

## 24. Official Technical References

- RealSense, **Supported Operating Systems**: Windows 10/11 and supported Linux platforms.
- RealSense, **Windows Installation — From Source**.
- RealSense, **SDK Installation Guides and Supported Languages**.
- Microsoft Learn, **Install .NET on Windows, Linux, and macOS**.
- Microsoft Learn, **ASP.NET Core documentation** describing cross-platform web apps and services.
- PyTorch, **Start Locally** for Windows and CUDA installation selection.
- Docker, **Install Docker Desktop on Windows**.
- Docker, **Docker Desktop WSL2 backend**.

