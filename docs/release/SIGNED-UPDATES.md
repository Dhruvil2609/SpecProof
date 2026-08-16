# Signed Station Updates

## Trust Model

Release manifests are canonical JSON signed with RSA-PSS and SHA-256. The private key remains
in the approved release signing service; stations contain only the pinned public key. A
signature envelope records the algorithm, key ID, canonical manifest hash, and detached
signature. Package SHA-256 and size are verified after signature validation.

## Manifest Controls

`schemas/release/update-manifest.schema.json` defines release version, UTC generation time,
compatible data-schema range, rollout percentage, and one or more runtime artifacts. Station
cohorts are selected deterministically from the station UUID, so staged rollout remains stable
without server-side assignment state.

## Offline Activation and Rollback

`tools/release_management/signed_updates.py` verifies a manifest and local package directory,
then stages packages under `versions/<version>`. Activation atomically replaces `current.json`
and preserves `previous.json`; rollback atomically exchanges those descriptors. Package
installers consume the selected artifact after verification. Update processing never deletes
station queues, captures, configuration, or inspection evidence.

Private keys must not be passed on the command line or stored with packages. Production
signing, checksum publication, Windows Authenticode, container signing, and public-key
rotation remain controlled release operations and require independent evidence.
