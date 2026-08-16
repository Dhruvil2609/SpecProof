# SpecProof Admin Manual

**Audience:** System administrators, quality managers, and SpecProof support engineers  
**Status:** Living draft  
**Last Updated:** 2026-07-29T17:07:31Z

## 1. Admin Scope

Administrators manage tenants, users, stations, calibration readiness, retention policies, diagnostics, and operational support. Admins do not change historical inspection records.

## 2. Local Development Services

For the development environment, PostgreSQL runs through Docker Compose.

| Service | Host | Development Credential |
|---------|------|------------------------|
| PostgreSQL | `localhost:55432` | Username `Admin`, password `Admin@123` |
| Redis | `localhost:6379` | No password in local dev |
| MinIO | `localhost:9000` / `localhost:9001` | Local-only dev credentials in `docker-compose.yml` |
| RabbitMQ | `localhost:5672` / `localhost:15672` | Local-only dev credentials in `docker-compose.yml` |

These credentials are local development defaults only. Production secrets must be stored outside source control.

## 3. Tenant Administration

Admins should be able to:

- Create and update tenants.
- Configure organisation and factory records.
- Assign stations to factories.
- Configure data retention policies.
- Configure approved garment categories and spec sources.
- Review tenant-level audit history.

## 4. User and Role Administration

Supported role concepts:

| Role | Typical Permissions |
|------|---------------------|
| Operator | Run inspections and view assigned station results. |
| Reviewer | Review `FAIL`, `REVIEW`, and `INVALID` results. |
| Quality Manager | View reports, trends, and inspection history. |
| Tenant Admin | Manage tenant users, factories, stations, and policies. |
| SpecProof Support | Diagnose stations and support controlled remediation. |

Role changes must be audited.

## 5. Station Administration

Admins should track:

- Station ID.
- Factory assignment.
- Camera serial number.
- Camera firmware/SDK version.
- Calibration status and expiry.
- Software version.
- Local queue status.
- Last successful sync.
- Hardware health events.

## 6. Calibration Administration

Calibration records must include:

- Station ID.
- Camera serial.
- Calibration artefact ID.
- Operator or technician.
- Calibration timestamp in UTC.
- Expiry timestamp in UTC.
- Calibration files or checksum references.

Expired calibration should prevent automated inspection decisions.

## 7. Tech-Pack and Rule Administration

Admins or approved technical users manage:

- Structured tech-pack imports.
- Style, size, and tolerance data.
- Brand-specific POM terminology.
- Canonical POM mappings.
- Human approval for ambiguous mappings.
- Version activation and retirement.

Historical inspections must always point to immutable spec/ruleset versions.

## 8. Audit and Evidence Administration

Audit records are append-only. Admin users may view and export audit data but must not update or delete audit events.

Inspection evidence should bind:

- Raw/derived capture hashes.
- Calibration ID.
- Camera serial.
- Model and ruleset versions.
- Tech-pack/spec version.
- Measurement results.
- Human review actions.
- UTC timestamps.

## 9. Diagnostics

Use `specproof-doctor` when available to verify:

- OS/toolchain readiness.
- Docker daemon and compose services.
- PostgreSQL, Redis, MinIO, and RabbitMQ connectivity.
- Camera SDK and RealSense Python binding.
- GPU/CUDA availability where configured.

Recommended local commands:

```powershell
.\start-development.ps1
uv run specproof-doctor
.\stop-development.ps1
```

The launcher starts Compose infrastructure and all current applications, writes logs
under `.cache/development/logs/`, and records process IDs for controlled shutdown.
Run `.\start-development.ps1 -ValidateOnly` for a non-starting prerequisite check.
If Python 3.11 native modules are blocked by workstation Application Control, run
`.\start-development.ps1 -InfrastructureOnly` to start Docker services while the
interpreter approval is pending.

The capture service listens on `127.0.0.1:50051` by default. Configure `SPEC_PROOF_CAMERA_PROVIDER` as `mock`, `replay`, or `realsense`; replay mode also requires `SPEC_PROOF_REPLAY_PATH`. Persistent station data defaults to `station-data/` and can be changed with `SPEC_PROOF_STATION_DATA`.

Queue states are `pending`, `uploading`, `completed`, and `failed`. On restart, interrupted `uploading` records are recovered for retry. Do not delete queued package files before checksum-verified completion.

## 10. Incident Response

For repeated failures:

1. Stop new inspections on the affected station.
2. Preserve recent logs and support bundle.
3. Check calibration and camera health.
4. Confirm local services are healthy.
5. Confirm sync status.
6. Escalate to SpecProof support with station ID, timestamps, and symptoms.

## 11. Production Security Rules

- Do not commit production secrets.
- Inject production secrets from the approved secret manager, protected signing service,
  operating-system credential store, or container secret; never embed them in images,
  installers, support bundles, logs, or command-line arguments.
- Use tenant isolation and role-based access.
- Use TLS for every remote service and terminate only TLS 1.2 or 1.3.
- Rotate credentials and certificates.
- Keep audit logs append-only.
- Review data-retention and deletion requirements with each tenant.
- Configure production JWT issuer, audience, and a secret of at least 32 characters.
- Configure a non-development evidence signing key ID and protected signing secret.
- Set `Security:RequireHttps=true` and provide station CA SHA-256 roots under
  `Security:DeviceCertificates:AllowedRootCertificateSha256`.
- Require station certificate chain trust, client-authentication EKU, and online revocation.

Production startup fails when these controls are absent. Development Compose explicitly runs
the platform API in the `Development` environment and is not production evidence. Follow
`docs/security/TLS-BASELINE.md` for deployment acceptance.
Use `config/production.env.example` only as a deployment inventory and follow
`docs/security/SECRET-MANAGEMENT.md` for ownership, rotation, and incident response.

## 12. Capture Storage and Credentials

- Keep station credentials behind the configured credential-store abstraction; Windows workstations use DPAPI.
- Store `.spcapture` payloads only on a BitLocker/LUKS-protected station volume and encrypted
  MinIO/S3 storage, never in PostgreSQL.
- PostgreSQL stores capture identity, object key, checksum, size, status, and UTC timestamps.
- Treat `Admin` / `Admin@123` and all Compose credentials as local-development values only.
- Real `.bag` and `.spcapture` fixtures belong in Git LFS.
- Production station storage requires `SPEC_PROOF_S3_SERVER_SIDE_ENCRYPTION`; use `aws:kms`
  with `SPEC_PROOF_S3_KMS_KEY_ID` where managed KMS is available.

## 13. Windows Station Service

Use the versioned `specproof-station-<version>-win-x64.zip` artifact on Windows stations.
Verify and extract the archive locally, then run `install-service.ps1` as Administrator. The
installer preserves `C:\ProgramData\SpecProof\Station` during upgrades, installs dependencies
from the packaged offline wheelhouse, and configures `SpecProofStationHost` under the
least-privileged `LocalService` account.

Before starting the service, replace every placeholder in
`C:\ProgramData\SpecProof\Station\config\station.env`. Use `uninstall-service.ps1` to remove
program files while preserving station data; supply `-RemoveData` only after backup and
retention approval. The ZIP is not an MSI and must not be treated as signed release evidence
until the Phase 8 signing gate completes.
