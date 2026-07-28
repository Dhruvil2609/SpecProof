# Phase 1 — Project Foundation

**Phase ID:** PHASE-1
**Status:** `IN_PROGRESS`
**Created:** 2026-07-25T13:15:00Z
**Last Updated:** 2026-07-28T16:34:20Z
**Estimated Duration:** 2–3 weeks
**Dependencies:** Phase 0
**Language:** en

## 1.1 Objective

Establish the monorepo scaffold, shared libraries, database schema foundation, CI pipelines, coding standards, coverage reporting, and i18n framework used by later phases.

## 1.2 Tasks

### 1.2.1 Monorepo Structure

- [x] **TASK-1.2.1.1** — Create repository directory tree
- [x] **TASK-1.2.1.2** — Configure workspace-level build orchestration
- [x] **TASK-1.2.1.3** — Create shared contracts package
- [x] **TASK-1.2.1.4** — Create camera abstractions package
- [ ] **TASK-1.2.1.5** — Create placeholder projects for every future app and package

Placeholder generation remains deferred to the phase that owns each application.

### 1.2.2 .NET Solution Setup

- [x] **TASK-1.2.2.1** — Create solution with active .NET projects
- [x] **TASK-1.2.2.2** — Configure nullable, warnings-as-errors, and analyzers
- [x] **TASK-1.2.2.3** — Configure central package management
- [x] **TASK-1.2.2.4** — Create ASP.NET Core platform API
- [x] **TASK-1.2.2.5** — Create station host
- [x] **TASK-1.2.2.6** — Generate OpenAPI from ASP.NET Core endpoints
- [x] **TASK-1.2.2.7** — Add OpenTelemetry traces, metrics, and OTLP export
- [x] **TASK-1.2.2.8** — Test contract serialization

### 1.2.3 Python Project Setup

- [x] **TASK-1.2.3.1** — Configure dependency groups and reproducible `uv.lock`
- [x] **TASK-1.2.3.2** — Configure Ruff
- [x] **TASK-1.2.3.3** — Configure strict Pyright checks for maintained source
- [x] **TASK-1.2.3.4** — Create capture-service package
- [x] **TASK-1.2.3.5** — Create measurement-service package
- [x] **TASK-1.2.3.6** — Create shared geometry utilities
- [x] **TASK-1.2.3.7** — Test utility and service functions

The locked project targets Python 3.11. Local execution used an ignored Python 3.14 validation environment because Windows Application Control blocks the managed Python 3.11 native extension modules on this workstation.

### 1.2.4 Frontend Project Setup

- [x] **TASK-1.2.4.1** — Initialize React and TypeScript applications with Vite
- [x] **TASK-1.2.4.2** — Configure strict TypeScript
- [x] **TASK-1.2.4.3** — Configure ESLint and formatting
- [x] **TASK-1.2.4.4** — Configure react-i18next
- [x] **TASK-1.2.4.5** — Create design-system tokens
- [x] **TASK-1.2.4.6** — Create layout shells and routing
- [x] **TASK-1.2.4.7** — Add component, routing, and i18n tests

### 1.2.5 Database Schema Foundation

- [x] **TASK-1.2.5.1** — Design the EF Core DbContext
- [x] **TASK-1.2.5.2** — Add core tenant and identity entities
- [x] **TASK-1.2.5.3** — Add station, camera, and calibration entities
- [x] **TASK-1.2.5.4** — Add garment category, style, and size entities
- [x] **TASK-1.2.5.5** — Add append-only audit events
- [x] **TASK-1.2.5.6** — Store timestamps as UTC `timestamptz`
- [x] **TASK-1.2.5.7** — Add forward, rollback, constraint, and append-only migration tests

Real PostgreSQL tests are opt-in locally and enabled in the database CI workflow. They remain unexecuted on this workstation while Docker is stopped.

### 1.2.6 Internationalisation Framework

- [x] **TASK-1.2.6.1** — Define backend i18n architecture
- [x] **TASK-1.2.6.2** — Define frontend i18n architecture
- [x] **TASK-1.2.6.3** — Create English base translations
- [x] **TASK-1.2.6.4** — Implement locale selection
- [x] **TASK-1.2.6.5** — Define translation-key conventions
- [x] **TASK-1.2.6.6** — Test English translation completeness

### 1.2.7 CI/CD Pipeline

- [x] **TASK-1.2.7.1** — Add .NET build and test workflow
- [x] **TASK-1.2.7.2** — Add Python lint, type-check, test, and coverage workflow
- [x] **TASK-1.2.7.3** — Add frontend lint, test, coverage, and build workflow
- [x] **TASK-1.2.7.4** — Add Docker compose integration workflow
- [x] **TASK-1.2.7.5** — Add PostgreSQL migration workflow
- [ ] **TASK-1.2.7.6** — Configure branch protection rules
- [x] **TASK-1.2.7.7** — Configure coverage collection and artifact reporting

Branch protection requires repository administrative access and cannot be verified from the local checkout.

### 1.2.8 Coding Standards Enforcement

- [x] **TASK-1.2.8.1** — Create `.editorconfig`
- [x] **TASK-1.2.8.2** — Create pre-commit quality hooks
- [x] **TASK-1.2.8.3** — Document coding standards
- [ ] **TASK-1.2.8.4** — Enforce required CI checks on pull requests

## 1.3 Verification Evidence

| Check | Status | Evidence |
|-------|--------|----------|
| .NET release build | PASS | Zero warnings and zero errors |
| .NET tests | PASS | 7 tests |
| Ruff | PASS | 66 files formatted; zero violations |
| Pyright | PASS | Zero errors |
| Python tests | PASS | 58 tests; 80.15% total coverage |
| Frontend lint and type-check | PASS | Both applications |
| Frontend tests | PASS | 8 tests |
| Frontend production builds | PASS | Both applications |
| Generated OpenAPI configuration | PASS | `AddOpenApi` and `MapOpenApi` build successfully |
| Docker compose configuration | PASS | `docker compose config --quiet` |
| PostgreSQL apply and rollback | BLOCKED | Docker daemon unavailable |
| Windows and Linux CI | BLOCKED | Remote workflow execution not verified |
| Branch protection | BLOCKED | GitHub administrative access required |

## 1.4 Exit Criteria

- [x] Active workspace projects build and pass local linting
- [ ] Database migrations run forward and backward against PostgreSQL
- [ ] CI is green on Windows and Linux runners
- [x] English i18n framework is functional
- [x] OpenAPI is generated from endpoints
- [ ] All required remote checks are enforced

Phase 1 remains `IN_PROGRESS` until PostgreSQL integration and remote repository enforcement are verified.
