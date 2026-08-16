# Production Quality-Gate Evidence

Every release candidate must provide one evidence record for each of the 15 production
quality gates defined in the development environment requirements. The canonical machine
contract is `schemas/release/quality-gate-evidence.schema.json`.

## Gate Catalogue

| Gate | Required evidence |
| --- | --- |
| QG-01 | Successful Windows and Linux CI workflow runs |
| QG-02 | Windows camera hardware-in-loop result |
| QG-03 | Linux camera hardware-in-loop result, or approved non-Linux scope decision |
| QG-04 | Cross-platform golden replay comparison |
| QG-05 | Calibration and known-artefact accuracy report |
| QG-06 | Thirty-minute and eight-hour stability reports |
| QG-07 | USB disconnect and recovery qualification |
| QG-08 | Offline operation, restart recovery, and later synchronisation result |
| QG-09 | Signed upgrade and rollback result |
| QG-10 | Installer install, upgrade, uninstall, and residue checks |
| QG-11 | Reviewed SBOM, vulnerability, secret, container, and license scans |
| QG-12 | Independent evidence-record verification result |
| QG-13 | Empty-environment PostgreSQL and object-storage restore result |
| QG-14 | Operator acceptance and training sign-off |
| QG-15 | Release documentation and support-runbook review |

## Evidence Rules

- Evidence timestamps are UTC and evidence files are immutable release artifacts.
- Every evidence reference includes its SHA-256 hash.
- `PASS` requires at least one independently retrievable evidence reference.
- `NOT_APPLICABLE` requires an approver and written scope justification.
- `BLOCKED` and `FAIL` force the release decision to `NO_GO` or `PENDING`.
- Hardware, signing, legal, and external-review gates remain blocked until real evidence
  exists; synthetic or test-key evidence cannot satisfy them.

The final go/no-go record identifies the release version, source revision, artifact manifest,
decision owner, decision timestamp, and exact evidence contract used.
