# Phase 5 — Platform and Trust Layer

**Phase ID:** PHASE-5  
**Status:** `NOT_STARTED`  
**Created:** 2026-07-25T13:15:00Z  
**Last Updated:** 2026-07-25T13:15:00Z  
**Estimated Duration:** 6–8 weeks  
**Dependencies:** Phase 4  
**Language:** en  

---

## 5.1 Objective

Build the multi-tenant platform API, authentication and authorisation, signed evidence records, device management, and data synchronisation. This is the enterprise backbone connecting stations, users, and brands.

---

## 5.2 Tasks

### 5.2.1 Platform API (ASP.NET Core)

- [ ] **TASK-5.2.1.1** — API structure with Minimal APIs or Controllers
- [ ] **TASK-5.2.1.2** — OpenAPI 3.x auto-generation
- [ ] **TASK-5.2.1.3** — Request validation (FluentValidation)
- [ ] **TASK-5.2.1.4** — Global error handling with RFC 7807 Problem Details
- [ ] **TASK-5.2.1.5** — API versioning strategy
- [ ] **TASK-5.2.1.6** — Rate limiting
- [ ] **TASK-5.2.1.7** — Write API endpoint tests

### 5.2.2 Multi-Tenancy

- [ ] **TASK-5.2.2.1** — Tenant resolution middleware
- [ ] **TASK-5.2.2.2** — Tenant-scoped data access (EF Core query filters)
- [ ] **TASK-5.2.2.3** — Tenant-scoped object storage buckets
- [ ] **TASK-5.2.2.4** — Tenant configuration management
- [ ] **TASK-5.2.2.5** — Write tenant isolation tests

### 5.2.3 Authentication and Authorisation

- [ ] **TASK-5.2.3.1** — JWT or OIDC authentication
- [ ] **TASK-5.2.3.2** — Role-based access control (RBAC)
- [ ] **TASK-5.2.3.3** — User, Role, Permission entities
- [ ] **TASK-5.2.3.4** — Device identity and certificate authentication
- [ ] **TASK-5.2.3.5** — Certificate rotation mechanism
- [ ] **TASK-5.2.3.6** — Write auth/authz tests

### 5.2.4 Station and Device Management

- [ ] **TASK-5.2.4.1** — Station registration API
- [ ] **TASK-5.2.4.2** — Device health reporting API
- [ ] **TASK-5.2.4.3** — Remote diagnostics endpoint
- [ ] **TASK-5.2.4.4** — Station configuration push
- [ ] **TASK-5.2.4.5** — Firmware and software version tracking
- [ ] **TASK-5.2.4.6** — Write station management tests

### 5.2.5 Trust and Signing Layer

- [ ] **TASK-5.2.5.1** — Evidence record digital signature (service-side)
- [ ] **TASK-5.2.5.2** — Secure key storage (Windows CNG/DPAPI/TPM abstraction)
- [ ] **TASK-5.2.5.3** — Signature verification API
- [ ] **TASK-5.2.5.4** — Append-only audit event stream
- [ ] **TASK-5.2.5.5** — Tamper-evident hash chain
- [ ] **TASK-5.2.5.6** — Write signature and verification tests

### 5.2.6 Data Synchronisation

- [ ] **TASK-5.2.6.1** — Offline queue → central platform sync
- [ ] **TASK-5.2.6.2** — Idempotent sync protocol
- [ ] **TASK-5.2.6.3** — Conflict detection and resolution
- [ ] **TASK-5.2.6.4** — Retry and dead-letter handling
- [ ] **TASK-5.2.6.5** — Write sync integration tests

### 5.2.7 Reporting and Export

- [ ] **TASK-5.2.7.1** — Inspection result API
- [ ] **TASK-5.2.7.2** — Batch/order summary API
- [ ] **TASK-5.2.7.3** — CSV and PDF export
- [ ] **TASK-5.2.7.4** — Webhook/event output
- [ ] **TASK-5.2.7.5** — Data retention and deletion API
- [ ] **TASK-5.2.7.6** — Write export tests

### 5.2.8 Background Processing

- [ ] **TASK-5.2.8.1** — Background job infrastructure (Hangfire or custom)
- [ ] **TASK-5.2.8.2** — Measurement processing queue
- [ ] **TASK-5.2.8.3** — Report generation queue
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

---

## 5.4 Exit Criteria

- [ ] Multi-tenant API serves requests with proper isolation
- [ ] Authentication and RBAC working
- [ ] Evidence records are signed and verifiable
- [ ] Offline sync delivers zero-loss
- [ ] Reporting and export APIs functional
- [ ] All security test cases pass
- [ ] All test cases pass on both Windows and Linux runners
