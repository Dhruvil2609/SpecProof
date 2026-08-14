# Phase 5 — Platform and Trust Layer

**Phase ID:** PHASE-5  
**Status:** `IN_PROGRESS`  
**Created:** 2026-07-25T13:15:00Z  
**Last Updated:** 2026-08-14T18:58:15Z
**Estimated Duration:** 6–8 weeks  
**Dependencies:** Phase 4  
**Language:** en  

---

## 5.1 Objective

Build the multi-tenant platform API, authentication and authorisation, signed evidence records, device management, and data synchronisation. This is the enterprise backbone connecting stations, users, and brands.

Hardware is not required for Phase 5 coding. Station management, device identity,
sync, evidence signing, reporting, and API behavior should be implemented and tested
with simulated stations, generated capture metadata, Docker PostgreSQL, and MinIO.

---

## 5.2 Tasks

### 5.2.1 Platform API (ASP.NET Core)

- [x] **TASK-5.2.1.1** — API structure with Minimal APIs or Controllers ✅ (2026-08-06T17:32:54Z)
- [x] **TASK-5.2.1.2** — OpenAPI 3.x auto-generation ✅ (2026-08-06T17:32:54Z)
- [x] **TASK-5.2.1.3** — Request validation (FluentValidation) ✅ (2026-08-06T17:32:54Z)
- [x] **TASK-5.2.1.4** — Global error handling with RFC 7807 Problem Details ✅ (2026-08-06T17:32:54Z)
- [x] **TASK-5.2.1.5** — API versioning strategy ✅ (2026-08-06T17:32:54Z)
- [x] **TASK-5.2.1.6** — Rate limiting ✅ (2026-08-06T17:32:54Z)
- [ ] **TASK-5.2.1.7** — Write API endpoint tests

### 5.2.2 Multi-Tenancy

- [x] **TASK-5.2.2.1** — Tenant resolution middleware ✅ (2026-08-06T17:32:54Z)
- [x] **TASK-5.2.2.2** — Tenant-scoped data access (EF Core query filters) ✅ (2026-08-06T17:32:54Z)
- [x] **TASK-5.2.2.3** — Tenant-scoped object storage buckets ✅ (2026-08-06T17:32:54Z)
- [x] **TASK-5.2.2.4** — Tenant configuration management ✅ (2026-08-06T17:32:54Z)
- [x] **TASK-5.2.2.5** — Write tenant isolation tests ✅ (2026-08-06T17:32:54Z)

### 5.2.3 Authentication and Authorisation

- [x] **TASK-5.2.3.1** — JWT or OIDC authentication ✅ (2026-08-06T17:32:54Z)
- [x] **TASK-5.2.3.2** — Role-based access control (RBAC) ✅ (2026-08-06T17:32:54Z)
- [x] **TASK-5.2.3.3** — User, Role, Permission entities ✅ (2026-08-06T17:32:54Z)
- [x] **TASK-5.2.3.4** — Device identity and certificate authentication ✅ (2026-08-06T17:32:54Z)
- [x] **TASK-5.2.3.5** — Certificate rotation mechanism ✅ (2026-08-14T18:58:15Z)
- [x] **TASK-5.2.3.6** — Write auth/authz tests ✅ (2026-08-06T17:32:54Z)

### 5.2.4 Station and Device Management

- [x] **TASK-5.2.4.1** — Station registration API ✅ (2026-08-06T17:32:54Z)
- [x] **TASK-5.2.4.2** — Device health reporting API ✅ (2026-08-06T17:32:54Z)
- [x] **TASK-5.2.4.3** — Remote diagnostics endpoint ✅ (2026-08-06T17:32:54Z)
- [x] **TASK-5.2.4.4** — Station configuration push ✅ (2026-08-06T17:32:54Z)
- [x] **TASK-5.2.4.5** — Firmware and software version tracking ✅ (2026-08-06T17:32:54Z)
- [ ] **TASK-5.2.4.6** — Write station management tests

### 5.2.5 Trust and Signing Layer

- [x] **TASK-5.2.5.1** — Evidence record digital signature (service-side) ✅ (2026-08-06T17:32:54Z)
- [ ] **TASK-5.2.5.2** — Secure key storage (Windows CNG/DPAPI/TPM abstraction)
- [x] **TASK-5.2.5.3** — Signature verification API ✅ (2026-08-06T17:32:54Z)
- [x] **TASK-5.2.5.4** — Append-only audit event stream ✅ (2026-08-06T17:32:54Z)
- [x] **TASK-5.2.5.5** — Tamper-evident hash chain ✅ (2026-08-06T17:32:54Z)
- [x] **TASK-5.2.5.6** — Write signature and verification tests ✅ (2026-08-06T17:32:54Z)

### 5.2.6 Data Synchronisation

- [x] **TASK-5.2.6.1** — Offline queue → central platform sync ✅ (2026-08-06T17:32:54Z)
- [x] **TASK-5.2.6.2** — Idempotent sync protocol ✅ (2026-08-06T17:32:54Z)
- [x] **TASK-5.2.6.3** — Conflict detection and resolution ✅ (2026-08-06T17:32:54Z)
- [x] **TASK-5.2.6.4** — Retry and dead-letter handling ✅ (2026-08-06T17:32:54Z)
- [ ] **TASK-5.2.6.5** — Write sync integration tests

### 5.2.7 Reporting and Export

- [x] **TASK-5.2.7.1** — Inspection result API ✅ (2026-08-06T17:32:54Z)
- [x] **TASK-5.2.7.2** — Batch/order summary API ✅ (2026-08-06T17:32:54Z)
- [ ] **TASK-5.2.7.3** — CSV and PDF export
- [x] **TASK-5.2.7.4** — Webhook/event output ✅ (2026-08-06T17:32:54Z)
- [x] **TASK-5.2.7.5** — Data retention and deletion API ✅ (2026-08-06T17:32:54Z)
- [x] **TASK-5.2.7.6** — Write export tests ✅ (2026-08-06T17:32:54Z)

### 5.2.8 Background Processing

- [x] **TASK-5.2.8.1** — Background job infrastructure (Hangfire or custom) ✅ (2026-08-06T17:32:54Z)
- [ ] **TASK-5.2.8.2** — Measurement processing queue
- [x] **TASK-5.2.8.3** — Report generation queue ✅ (2026-08-06T17:32:54Z)
- [ ] **TASK-5.2.8.4** — Notification dispatch
- [ ] **TASK-5.2.8.5** — Write background job tests

---

## 5.3 Test Cases

| Test ID | Test Description | Type | Expected Result |
|---------|-----------------|------|-----------------|
| T-5.001 | Tenant A cannot access Tenant B data | Security | 403 or empty result |
| T-5.002 | JWT auth accepts valid token | Unit | 200 OK |
| T-5.003 | JWT auth rejects expired token | Unit | 401 Unauthorized |
| T-5.004 | RBAC prevents operator from admin actions | Security | 403 Forbidden |
| T-5.005 | Station registers with device certificate | Integration | Station created |
| T-5.006 | Evidence record signature validates | Unit | Signature valid |
| T-5.007 | Tampered evidence record detected | Unit | Verification fails |
| T-5.008 | Offline sync delivers all queued records | E2E | Zero lost records |
| T-5.009 | Duplicate sync is idempotent | Integration | No duplicate records |
| T-5.010 | CSV export contains correct data | Unit | Data matches source |
| T-5.011 | API versioning returns correct schema | Integration | Correct version |
| T-5.012 | Rate limiting returns 429 | Integration | 429 Too Many Requests |
| T-5.013 | Audit events are append-only | Integration | DELETE/UPDATE fails |
| T-5.014 | OpenAPI spec is valid | Build | Spec validates |
| T-5.015 | Authenticated tenant header differs from JWT tenant claim | Security | 403 Forbidden |
| T-5.016 | Tenant-bound write request differs from authenticated tenant | Security | 403 Forbidden |
| T-5.017 | Valid active station certificate authenticates device | Unit | Tenant/station principal created |
| T-5.018 | Unknown or inactive station certificate is presented | Security | 401 Unauthorized |
| T-5.019 | Authenticated station targets another station | Security | 403 Forbidden |
| T-5.020 | Station certificate rotates | Unit | Previous identity retired and audit event created |

### 5.3.1 Security Remediation Evidence

- 2026-08-14T18:41:43Z — Made the authenticated JWT `tenant_id` claim authoritative, rejected missing or conflicting tenant context, guarded every tenant-bearing platform write request, and protected station registration with station-management permission.
- 2026-08-14T18:41:43Z — Passed 16 focused platform API unit tests, including six tenant-boundary regression tests.
- 2026-08-14T18:58:15Z — Added active-window client-certificate authentication, least-privilege station claims, same-station request enforcement, globally conflict-safe certificate registration, audited certificate rotation, and seven focused regressions; 23 platform API tests pass.

---

## 5.4 Exit Criteria

- [ ] Multi-tenant API serves requests with proper isolation
- [ ] Authentication and RBAC working
- [ ] Evidence records are signed and verifiable
- [ ] Offline sync delivers zero-loss
- [ ] Reporting and export APIs functional
- [ ] All security test cases pass
- [ ] All test cases pass on both Windows and Linux runners

Hardware-originated capture payloads can be substituted with synthetic or replay
packages until physical stations are available.
