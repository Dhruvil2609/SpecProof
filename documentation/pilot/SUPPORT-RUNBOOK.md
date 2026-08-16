# Pilot Support Runbook

## First Response

Record the incident ID, UTC start time, tenant, station, inspection/capture IDs, software
versions, operator impact, dashboard snapshot, and recent deployment/configuration changes.
Preserve station queues, sealed evidence, database records, audit events, and logs.

## Offline Station

Confirm power, clock, station-host/capture-service state, certificate validity, and network
reachability. Restart only the failed process after collecting logs. Escalate if no health
report arrives within five minutes or more than one station is affected.

## Queue Backlog

Check platform health and authentication before inspecting pending/retryable/dead-letter
counts. Restore connectivity and allow bounded retry. Requeue dead letters only after hash
verification and operator review. Never edit payloads or SQLite rows manually.

## Processing Latency

Compare capture, perception, measurement, evidence, persistence, and total histograms.
Capture CPU/memory/provider data and active workload. Preserve the 15-second acceptance gate;
do not disable quality or evidence stages to meet the five-second optimisation target.

## Inspection Failures

Group failures by station, calibration, tech-pack version, POM, and software version. Stop the
affected station when failures may produce incorrect acceptance decisions. Preserve replay
packages and evidence for engineering review.

## Calibration Expiry

Remove the station from production until approved calibration completes. Verify artefact ID,
camera serial, operator, UTC timestamp, thresholds, and immutable calibration hash.

## Database Unavailable

Confirm PostgreSQL container/service health, storage, connections, and recent migrations.
Stations may continue durable offline capture; tell operators not to repeat acknowledged
captures. Escalate as severity 1 if all sites are affected or durability is uncertain.

## Recovery Verification

Verify health, queue drain, idempotent inspection counts, evidence hashes/signatures, audit
chain continuity, and operator visibility. Attach the verification evidence before closure.
