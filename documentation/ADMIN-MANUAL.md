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
- Use tenant isolation and role-based access.
- Use TLS for remote access.
- Rotate credentials and certificates.
- Keep audit logs append-only.
- Review data-retention and deletion requirements with each tenant.

## 12. Capture Storage and Credentials

- Keep station credentials behind the configured credential-store abstraction; Windows workstations use DPAPI.
- Store `.spcapture` payloads in filesystem staging and MinIO/S3, never in PostgreSQL.
- PostgreSQL stores capture identity, object key, checksum, size, status, and UTC timestamps.
- Treat `Admin` / `Admin@123` and all Compose credentials as local-development values only.
- Real `.bag` and `.spcapture` fixtures belong in Git LFS.
