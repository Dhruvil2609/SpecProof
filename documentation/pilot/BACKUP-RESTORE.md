# Pilot Backup and Restore

## Scope and Schedule

Back up PostgreSQL metadata and the configured MinIO evidence bucket together at least daily
and before migrations or pilot releases. Retain encrypted copies according to tenant policy.
Each backup directory contains a custom-format PostgreSQL dump, evidence objects, and a
versioned UTC manifest with byte lengths and SHA-256 checksums.

## Backup

Set secrets in the process environment, then run:

```powershell
$env:SPEC_PROOF_DATABASE_URL = "postgresql://Admin:<password>@127.0.0.1:55432/specproof"
$env:SPEC_PROOF_OBJECT_STORAGE_ACCESS_KEY = "<access-key>"
$env:SPEC_PROOF_OBJECT_STORAGE_SECRET_KEY = "<secret-key>"
.venv\Scripts\python.exe tools/pilot/backup_restore.py --bucket specproof-evidence backup artifacts/backups
```

Copy the resulting directory atomically to approved encrypted storage and record its manifest
hash, release version, operator, destination, and UTC completion time.

## Verification

```powershell
.venv\Scripts\python.exe tools/pilot/backup_restore.py verify artifacts/backups/<backup>/manifest.json
```

Verification must pass before retention or restore. A size/hash mismatch is a SEV-2 incident;
do not restore a partially verified backup.

## Restore Drill

Provision an empty PostgreSQL database and empty evidence bucket, set
`SPEC_PROOF_DATABASE_URL` to the empty target, then run:

```powershell
.venv\Scripts\python.exe tools/pilot/backup_restore.py --bucket specproof-evidence restore artifacts/backups/<backup>/manifest.json
```

After restore, run migrations only if the restored release requires them. Verify tenant and
inspection counts, one sample per tenant, capture/evidence hashes, evidence signatures, audit
chain continuity, and object readability. Record the target environment, manifest SHA-256,
queries, sampled inspection IDs, outcome, and UTC timestamps. Destroy the drill environment
after evidence is approved.

## Failure Handling

Do not overwrite the only backup, restore into a non-empty database, or bypass verification.
If restore fails, preserve logs and target state, classify the incident, and retry with a new
empty target after correcting the cause.
