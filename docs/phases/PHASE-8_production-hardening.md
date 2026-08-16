# Phase 8 — Production Hardening

**Phase ID:** PHASE-8  
**Status:** `IN_PROGRESS`
**Created:** 2026-07-25T13:15:00Z  
**Last Updated:** 2026-08-16T10:21:03Z
**Estimated Duration:** 4–6 weeks  
**Dependencies:** Phase 7  
**Language:** en  

---

## 8.1 Objective

Harden all components for production deployment: security audit, installer packaging, code signing, update mechanism, compliance documentation, and full quality gates. The system must be ready for factory deployment.

Most Phase 8 software hardening can proceed before hardware is available: packaging,
signing, update/rollback, security scans, SBOM, observability, backup/restore, and
support runbooks. Hardware-in-loop, calibration accuracy, USB recovery, and stability
quality gates remain deferred final-release gates.

Phase 8 contains 50 implementation and acceptance tasks. Repository hardening proceeds as a
software track while managed signing, independent penetration testing, legal/privacy review,
remote release workflows, and qualified-hardware evidence remain explicit external gates.

---

## 8.2 Tasks

### 8.2.1 Security Hardening

- [x] **TASK-8.2.1.1** — Security audit of authentication and authorisation ✅ (2026-08-16T08:32:52Z)
- [x] **TASK-8.2.1.2** — Secret management review (no secrets in source) ✅ (2026-08-16T08:53:45Z)
- [x] **TASK-8.2.1.3** — TLS configuration audit ✅ (2026-08-16T08:32:52Z)
- [x] **TASK-8.2.1.4** — Encryption at rest for sensitive captures ✅ (2026-08-16T08:44:57Z)
- [ ] **TASK-8.2.1.5** — Dependency vulnerability scan (SBOM)
- [ ] **TASK-8.2.1.6** — Container vulnerability scan
- [ ] **TASK-8.2.1.7** — Penetration test remediation
- [x] **TASK-8.2.1.8** — Write security regression tests ✅ (2026-08-16T08:32:52Z)

### 8.2.2 Installer and Packaging

- [ ] **TASK-8.2.2.1** — Windows installer (MSIX/MSI)
- [x] **TASK-8.2.2.2** — Windows service package ✅ (2026-08-16T09:48:28Z)
- [x] **TASK-8.2.2.3** — Linux installer (Debian package or signed bundle) ✅ (2026-08-16T10:13:27Z)
- [x] **TASK-8.2.2.4** — Linux systemd service definitions ✅ (2026-08-16T10:13:27Z)
- [x] **TASK-8.2.2.5** — OCI container images for platform services ✅ (2026-08-16T10:21:03Z)
- [ ] **TASK-8.2.2.6** — Write installer tests (install, upgrade, uninstall)

### 8.2.3 Code Signing

- [ ] **TASK-8.2.3.1** — Windows code-signing certificate setup
- [ ] **TASK-8.2.3.2** — Sign all Windows executables and installers
- [ ] **TASK-8.2.3.3** — Sign container images
- [ ] **TASK-8.2.3.4** — SHA-256 checksum publication
- [ ] **TASK-8.2.3.5** — Write signature verification tests

### 8.2.4 Update Mechanism

- [ ] **TASK-8.2.4.1** — Signed package verification
- [ ] **TASK-8.2.4.2** — Staged rollout support
- [ ] **TASK-8.2.4.3** — Rollback mechanism
- [ ] **TASK-8.2.4.4** — Schema compatibility check
- [ ] **TASK-8.2.4.5** — Offline update package support
- [ ] **TASK-8.2.4.6** — Write update/rollback tests

### 8.2.5 Observability Production Setup

- [ ] **TASK-8.2.5.1** — Production Prometheus/Grafana configuration
- [ ] **TASK-8.2.5.2** — Production alerting rules
- [ ] **TASK-8.2.5.3** — Central log aggregation
- [ ] **TASK-8.2.5.4** — Distributed tracing
- [ ] **TASK-8.2.5.5** — Support bundle generation
- [ ] **TASK-8.2.5.6** — Write monitoring integration tests

### 8.2.6 Quality Gates

- [ ] **TASK-8.2.6.1** — All CI (Windows + Linux) green
- [ ] **TASK-8.2.6.2** — Hardware-in-loop tests pass
- [ ] **TASK-8.2.6.3** — Cross-platform replay tests pass
- [ ] **TASK-8.2.6.4** — Calibration and accuracy tests pass
- [ ] **TASK-8.2.6.5** — 30-minute and 8-hour stability tests pass
- [ ] **TASK-8.2.6.6** — USB disconnect/reconnect recovery tests pass
- [ ] **TASK-8.2.6.7** — Offline operation and sync tests pass
- [ ] **TASK-8.2.6.8** — Upgrade and rollback tests pass
- [ ] **TASK-8.2.6.9** — Installer and uninstall tests pass
- [ ] **TASK-8.2.6.10** — Security scan and SBOM review pass
- [ ] **TASK-8.2.6.11** — Evidence-record independent verification passes
- [ ] **TASK-8.2.6.12** — Backup and restore tests pass
- [ ] **TASK-8.2.6.13** — Operator acceptance tests pass
- [ ] **TASK-8.2.6.14** — Release documentation complete
- [ ] **TASK-8.2.6.15** — Support runbooks complete

### 8.2.7 Compliance Documentation

- [x] **TASK-8.2.7.1** — SBOM generation for all components ✅ (2026-08-16T09:21:20Z)
- [ ] **TASK-8.2.7.2** — Data protection impact assessment
- [ ] **TASK-8.2.7.3** — Third-party license compliance
- [ ] **TASK-8.2.7.4** — Release notes generation

---

## 8.3 Test Cases

| Test ID | Test Description | Type | Expected Result |
|---------|-----------------|------|-----------------|
| T-8.001 | Windows installer installs cleanly | Installer | Exit code 0 |
| T-8.002 | Windows installer upgrades existing | Installer | Data preserved |
| T-8.003 | Windows uninstaller removes cleanly | Installer | No orphan files |
| T-8.004 | Linux package installs and starts | Installer | Service running |
| T-8.005 | Code signature validates | Security | Signature valid |
| T-8.006 | Signed update installs | Update | Version upgraded |
| T-8.007 | Rollback restores previous version | Update | Previous version active |
| T-8.008 | 8-hour stability test | Stress | Zero failures |
| T-8.009 | SBOM is complete and valid | Compliance | All deps listed |
| T-8.010 | No high/critical CVEs in dependencies | Security | Zero high/critical |
| T-8.011 | Support bundle redacts secrets | Security | No secrets in bundle |
| T-8.012 | All 15 quality gates pass | Release | Green across all |

---

## 8.4 Exit Criteria

- [ ] All software quality gates pass
- [ ] Hardware-in-loop quality gates pass after hardware becomes available
- [ ] Signed installers for Windows and Linux
- [ ] Update and rollback mechanism tested
- [ ] Security scan clean
- [ ] Compliance documentation complete
- [ ] Production go/no-go decision documented

---

## 8.5 Implementation Evidence

- 2026-08-16T08:16:19Z — Started Phase 8, corrected its task count from 36 to 50,
  documented production assets, principals, trust boundaries, threats, invariants, and
  deferred external risks, and added the canonical schema and catalogue for all 15 release
  quality gates. Three baseline regression tests pass. No Phase 8 implementation task is
  closed by this planning baseline.
- 2026-08-16T08:32:52Z — Completed the authentication/authorisation and TLS audits.
  Added a fail-closed authentication boundary for all non-public API routes, hardened JWT
  issuer/audience/lifetime/role/tenant parsing, production startup validation for identity,
  signing, HTTPS, and station certificate policy, restrictive API response headers, and
  station certificate validity, client-authentication EKU, chain, revocation, and root
  allow-list checks. Documented resolved findings and the deployment TLS baseline. Validation
  passed with six new security tests, 34 platform tests, 17 data tests, six contract tests,
  Compose configuration, and a zero-warning release build.
- 2026-08-16T08:44:57Z — Added production capture encryption-at-rest enforcement.
  Station object uploads now support `AES256` and KMS server-side encryption, preserve the
  plaintext capture checksum as immutable metadata, report encryption during upload
  initiation, and reject missing encryption, missing KMS keys, or plaintext endpoints in
  production. The platform rejects unencrypted production capture registrations and records
  encryption state. Documented mandatory BitLocker/LUKS protection for local durable queues.
  Validation passed with four new Python tests, one new platform test, Ruff, strict Pyright
  on production modules, 20 focused Python tests, 35 platform tests, and a zero-warning build.
- 2026-08-16T08:53:45Z — Completed the production secret-management review. Added a
  tracked-file scanner for private-key material, provider token formats, forbidden key files,
  and credential-shaped assignments; documented runtime injection, least privilege,
  rotation, incident response, and the production secret inventory; and added a
  placeholder-only production environment template. Four scanner regression tests, Ruff,
  strict Pyright, and a zero-finding repository scan pass.
- 2026-08-16T09:21:20Z — Added deterministic CycloneDX 1.6 SBOM generation across the
  resolved Python `uv.lock`, restored NuGet assets, npm `pnpm-lock.yaml`, and pinned OCI base
  images. The local workspace SBOM contains 725 normalized components. Added a scheduled and
  pull-request security workflow for credential scanning, Python/NuGet/npm audits, Trivy
  source/configuration checks, five image builds, high/critical vulnerability gates, and
  per-image CycloneDX artifacts. Three SBOM tests, seven adjacent Phase 8 security tests,
  Ruff, strict Pyright, workflow parsing/formatting, and a zero-finding repository scan pass.
  Dependency/container scan tasks and the scan quality gate remain open until remote CI runs.
- 2026-08-16T09:48:28Z — Added the offline Windows x64 station service package. Station Host
  now integrates with Windows Service Control Manager, loads only approved keys from a
  protected station environment file, and supervises/restarts the local Python capture
  process without shell argument parsing. The versioned ZIP contains self-contained host
  output, frozen requirements, a dependency wheelhouse, the SpecProof wheel, production
  templates, SHA-256 manifest verification, and administrator install/upgrade/uninstall
  scripts that preserve station data by default. Windows CI builds and verifies the package.
  Three Python package tests, three .NET service tests, PowerShell parsing, strict Python
  typing/lint, and a zero-warning .NET build pass. MSI creation and elevated lifecycle
  acceptance remain open.
- 2026-08-16T10:13:27Z — Added a production Linux amd64 Debian package with self-contained
  Station Host output, frozen Python requirements, an offline dependency wheelhouse, the
  SpecProof wheel, preserved `/etc/specproof/station.env`, maintainer lifecycle scripts, and
  a payload SHA-256 manifest. Hardened both systemd units with filesystem, home, kernel,
  privilege, personality, realtime, architecture, write-path, and umask restrictions. Linux
  CI builds the package and validates it with `dpkg-deb`. Three portable Debian/systemd tests,
  Ruff, strict Pyright, workflow formatting, and diff validation pass. Remote CI and live
  install/upgrade/uninstall acceptance remain open.
- 2026-08-16T10:21:03Z — Hardened all four production application OCI definitions. Platform
  API, measurement service, operator UI, and admin UI now expose image identity/vendor/source
  labels, run as non-root users, and provide image-native health checks. Application Compose
  drops every Linux capability, sets `no-new-privileges`, mounts only `/tmp` as writable, and
  makes each root filesystem read-only. Added a non-root nginx main configuration with all
  runtime files under `/tmp` and bypassed root-oriented entrypoint scripts. Six focused
  container/deployment tests and Compose configuration validation pass. Docker image build and
  runtime acceptance remain open because the local daemon is stopped; CI definitions cover it.
