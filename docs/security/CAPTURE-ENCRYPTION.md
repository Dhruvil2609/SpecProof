# Capture Encryption at Rest

## Production Policy

Sensitive capture objects must use S3-compatible server-side encryption. Production station
startup rejects missing encryption, an unsupported algorithm, KMS without a key ID, or a
plaintext object-storage endpoint. Supported modes are `AES256` and `aws:kms`; KMS is
preferred because it provides centrally controlled key rotation and audit evidence.

The station reports the encryption state when initiating an upload. The production platform
rejects an unencrypted capture registration and records the encryption state with immutable
capture metadata. The original plaintext SHA-256 remains bound to the capture and evidence;
server-side encryption therefore does not change idempotency or evidence verification.

## Local Station Storage

Offline `.spcapture`, SQLite queue, calibration, configuration, and update data reside only
on an operating-system encrypted volume: BitLocker on Windows or LUKS/full-disk encryption on
Linux. The dedicated station account has access; operator browser accounts and unrelated
users do not. Recovery keys are escrowed under the site security process and are never stored
in source, station configuration, telemetry, or support bundles.

## Configuration

- `SPEC_PROOF_ENVIRONMENT=Production`
- `SPEC_PROOF_S3_ENDPOINT=https://...`
- `SPEC_PROOF_S3_SERVER_SIDE_ENCRYPTION=aws:kms`
- `SPEC_PROOF_S3_KMS_KEY_ID=<managed-key-id>`

Deployment acceptance verifies object encryption headers, KMS audit events, denied plaintext
registration, disk-encryption status, key rotation, backup encryption, and restore access.
