# Authentication and Authorisation Audit

**Audit date:** 2026-08-16T08:16:19Z

## Scope

The audit covers all routes registered by the platform API, tenant resolution, role and
permission mappings, station certificate authentication, station binding, certificate
rotation, development token issuance, and production TLS configuration.

## Route Boundary

Only `/healthz`, `/api/v1/openapi.json`, and the development/test-only token endpoint are
anonymous. `ApiAuthenticationBoundaryMiddleware` rejects every other `/api/v1` request
before endpoint execution. Endpoint filters then enforce the least permission required by
the operation.

| Route family | Required control |
| --- | --- |
| Inspection reads, dashboard, reports | `inspections.read` or report/export permission |
| Inspection submission and sync | `sync.write`, tenant match, station match |
| Station registration and certificate rotation | `stations.manage`, tenant match |
| Station health and version reporting | station health permission, tenant and station match |
| Diagnostics and configuration | station management permission and station route match |
| Evidence reads and verification | `evidence.verify` and tenant-scoped database/object reads |
| Tech-pack import and approval | `specs.manage` |
| Review actions | `inspections.review` |
| Webhooks and background jobs | export/job management permission and tenant match |

## Findings and Resolution

| Finding | Severity | Resolution |
| --- | --- | --- |
| New API routes could omit authentication filters | High | Added a fail-closed `/api/v1` authentication boundary |
| JWT validation accepted malformed payload exceptions as server errors | Medium | Invalid encodings, JSON, claims, roles, issuer, audience, and lifetime now return authentication failure |
| Production could use development JWT and evidence secrets | Critical | Production startup rejects missing, short, or development identity/signing configuration |
| Certificate authentication matched only stored hash and database validity | High | Added certificate validity, client-authentication EKU, chain, revocation, and root allow-list policy |
| HTTPS and response security headers were not enforced | High | Production requires HTTPS/HSTS and emits restrictive API security headers |

## Residual Risks

- HMAC identity and evidence secrets remain process configuration until the managed key
  provider and signing work is completed.
- Certificate revocation depends on production CA availability and network policy.
- Reverse-proxy TLS termination requires deployment-specific cipher and certificate testing.
- Independent penetration and cryptographic reviews remain external release gates.
