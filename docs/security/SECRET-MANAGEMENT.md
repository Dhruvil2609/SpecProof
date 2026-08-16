# Production Secret Management

## Policy

Production credentials and private keys are injected at runtime by an approved secret
manager, protected signing service, operating-system credential store, or container secret.
They are never committed, embedded in images/installers, printed in logs, exported in support
bundles, or copied into release evidence. Example files contain placeholders only.

## Secret Inventory

| Secret | Owner and storage | Rotation trigger |
| --- | --- | --- |
| Platform JWT signing material | Platform security owner; managed secret/key service | Scheduled rotation, suspected disclosure, identity-policy change |
| Evidence signing key | Trust owner; protected signing service/HSM | Cryptoperiod, compromise, algorithm migration |
| Station client private key | Device identity owner; TPM/CNG/DPAPI or Linux secure store | Certificate rotation, station replacement, compromise |
| PostgreSQL credentials | Platform operations; workload identity or secret manager | Scheduled rotation, role change, incident |
| Object-storage credentials/KMS key | Storage owner; workload identity and KMS | Scheduled rotation, access-policy change, incident |
| Registry/signing credentials | Release owner; CI OIDC/protected signing service | Trust-policy change or incident |
| Backup encryption credentials | Disaster-recovery owner; separate protected store | Scheduled recovery drill and cryptoperiod |

## Runtime Rules

- Production startup rejects missing or development identity and signing values.
- Prefer workload identity, managed identity, short-lived tokens, and OIDC over static secrets.
- Grant each station and service only the tenant, bucket, database, telemetry, and update
  permissions it requires.
- Never pass production secrets as command-line arguments where they can appear in process
  listings; use protected environment injection, files with restrictive permissions, or SDKs.
- Record rotation as an audit event without recording the secret value.

## Repository Enforcement

`tools/security/scan_secrets.py` scans Git-tracked text and rejects private-key files, private
key blocks, provider token formats, and credential-shaped assignments. Development-only
credentials and explicit deployment placeholders are not production secrets, but production
startup policy ensures they cannot be used outside Development/Test.

Run before commit and in CI:

```powershell
.venv\Scripts\python.exe tools/security/scan_secrets.py
```

Any finding is investigated rather than silently baselined. If a real secret reaches Git,
revoke and rotate it immediately; deleting the line or history alone is insufficient.
