# Pilot Incident Response

## Severity Matrix

| Severity | Definition | Acknowledge | Escalation |
| --- | --- | ---: | --- |
| SEV-1 | Safety concern, possible data/evidence loss, tenant isolation failure, or all pilot sites unavailable | 15 min | Incident commander, security, engineering, pilot owner immediately |
| SEV-2 | One site unavailable, repeated incorrect decisions, database outage with durable station retention | 30 min | Engineering and pilot owner within 30 min |
| SEV-3 | Single station degraded, queue/latency/calibration alert with workaround | 2 h | Support lead; engineering if unresolved in 4 h |
| SEV-4 | Documentation, cosmetic, or non-production issue | 1 business day | Product backlog owner |

## Response Process

1. Declare severity and incident commander using UTC timestamps.
2. Contain risk without deleting queues, evidence, audit events, or logs.
3. Preserve identifiers, versions, hashes, metrics, configuration, and operator statements.
4. Communicate status at 30-minute intervals for SEV-1 and hourly for SEV-2.
5. Recover using approved runbooks and verify integrity before resuming production.
6. Close only after impact, timeline, root cause, corrective actions, owners, and due dates are
   recorded. Complete a review within two business days for SEV-1/2.

## Stop-Production Authority

Operators and support may stop a station when safety, calibration, tenant isolation,
measurement validity, or evidence integrity is uncertain. Only the pilot owner or delegated
quality lead may return it to production after documented verification.
