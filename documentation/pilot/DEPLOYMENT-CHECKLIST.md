# Pilot Station Deployment Checklist

## Before Arrival

- Approve site, station identity, tenant/factory assignment, network ports, power, mounting,
  operator accounts, and support contacts.
- Record package version and SHA-256; verify the Linux archive manifest before transfer.
- Confirm current database and evidence backups and a completed restore drill.

## Installation

- Install the signed/versioned station package using `installers/linux/install.sh`.
- Place secrets outside the package with owner-only permissions; never store credentials in
  the checklist or source repository.
- Apply station and capture service templates, station UUID, camera serial, API endpoint,
  object-storage endpoint, and certificate paths.
- Start dependencies, apply migrations once, then start platform, measurement, station, and
  UI services in dependency order.

## Acceptance

- Verify service health, UTC clock, tenant/station identity, camera profile, calibration,
  storage capacity, and monitoring target visibility.
- Run a golden replay and three synthetic inspections; confirm unique inspection IDs,
  canonical evidence, audit linkage, operator-visible results, and queue drain.
- Disconnect the platform, capture once, reconnect, and verify exactly-once delivery.
- Record UTC evidence, versions, hashes, test IDs, operator sign-off, and support owner.

## Rollback

Stop capture, preserve queues and logs, restore the previous package/configuration, restart
services, verify health and queue integrity, and document the rollback as an incident. Never
delete a station SQLite queue or evidence object to make rollback appear successful.
