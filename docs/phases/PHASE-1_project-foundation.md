# Phase 1 Ã¢â‚¬â€ Project Foundation

**Phase ID:** PHASE-1
**Status:** `IN_PROGRESS`
**Created:** 2026-07-25T13:15:00Z
**Last Updated:** 2026-07-26T13:09:09Z
**Estimated Duration:** 2Ã¢â‚¬â€œ3 weeks
**Dependencies:** Phase 0
**Language:** en

---

## 1.1 Objective

Establish the monorepo scaffold, shared libraries, database schema foundation, CI/CD pipelines, coding standards enforcement, and i18n framework. This phase creates the architectural skeleton that all subsequent phases build upon.

---

## 1.2 Tasks

### 1.2.1 Monorepo Structure

- [x] **TASK-1.2.1.1** Ã¢â‚¬â€ Create full directory tree per repository spec (apps/, packages/, native/, ml/, infra/, tests/, tools/) âœ… (2026-07-26T10:17:24Z)
- [x] **TASK-1.2.1.2** Ã¢â‚¬â€ Configure workspace-level build orchestration âœ… (2026-07-26T10:17:24Z)
- [x] **TASK-1.2.1.3** Ã¢â‚¬â€ Create shared `contracts/` package with API DTOs and event schemas âœ… (2026-07-26T10:17:24Z)
- [x] **TASK-1.2.1.4** Ã¢â‚¬â€ Create `camera-abstractions/` package with `ICameraProvider` interface âœ… (2026-07-26T10:17:24Z)
- [ ] **TASK-1.2.1.5** Ã¢â‚¬â€ Create placeholder projects for all apps and packages

### 1.2.2 .NET Solution Setup

- [x] **TASK-1.2.2.1** Ã¢â‚¬â€ Create solution file with all .NET projects âœ… (2026-07-26T10:17:24Z)
- [x] **TASK-1.2.2.2** Ã¢â‚¬â€ Configure `Directory.Build.props` (nullable, warnings-as-errors, analyzers) âœ… (2026-07-26T10:17:24Z)
- [x] **TASK-1.2.2.3** Ã¢â‚¬â€ Configure central package management (`Directory.Packages.props`) âœ… (2026-07-26T10:17:24Z)
- [x] **TASK-1.2.2.4** Ã¢â‚¬â€ Create `platform-api` ASP.NET Core project âœ… (2026-07-26T10:17:24Z)
- [x] **TASK-1.2.2.5** Ã¢â‚¬â€ Create `station-host` project âœ… (2026-07-26T10:17:24Z)
- [ ] **TASK-1.2.2.6** Ã¢â‚¬â€ Add OpenAPI generation
- [ ] **TASK-1.2.2.7** Ã¢â‚¬â€ Add OpenTelemetry instrumentation
- [x] **TASK-1.2.2.8** Ã¢â‚¬â€ Write unit tests for contract serialisation âœ… (2026-07-26T10:17:24Z)

### 1.2.3 Python Project Setup

- [x] **TASK-1.2.3.1** Ã¢â‚¬â€ Configure `pyproject.toml` with dependency groups (runtime, dev, ml, station) âœ… (2026-07-26T10:17:24Z)
- [x] **TASK-1.2.3.2** Ã¢â‚¬â€ Configure Ruff linter and formatter âœ… (2026-07-26T10:17:24Z)
- [x] **TASK-1.2.3.3** Ã¢â‚¬â€ Configure Pyright type checker âœ… (2026-07-26T10:17:24Z)
- [x] **TASK-1.2.3.4** Ã¢â‚¬â€ Create `capture-service` Python package âœ… (2026-07-26T10:17:24Z)
- [x] **TASK-1.2.3.5** Ã¢â‚¬â€ Create `measurement-service` Python package âœ… (2026-07-26T10:17:24Z)
- [x] **TASK-1.2.3.6** Ã¢â‚¬â€ Create shared geometry utilities package âœ… (2026-07-26T10:17:24Z)
- [ ] **TASK-1.2.3.7** Ã¢â‚¬â€ Write unit tests for utility functions

### 1.2.4 Frontend Project Setup

- [x] **TASK-1.2.4.1** Ã¢â‚¬â€ Initialise React/TypeScript project with Vite (or Angular CLI) âœ… (2026-07-26T10:17:24Z)
- [x] **TASK-1.2.4.2** Ã¢â‚¬â€ Configure strict TypeScript âœ… (2026-07-26T10:17:24Z)
- [x] **TASK-1.2.4.3** Ã¢â‚¬â€ Configure ESLint + Prettier âœ… (2026-07-26T10:17:24Z)
- [x] **TASK-1.2.4.4** Ã¢â‚¬â€ Set up i18n framework (react-i18next or Angular i18n) âœ… (2026-07-26T10:17:24Z)
- [x] **TASK-1.2.4.5** Ã¢â‚¬â€ Create design system tokens (colours, typography, spacing) âœ… (2026-07-26T10:17:24Z)
- [x] **TASK-1.2.4.6** Ã¢â‚¬â€ Create initial layout shell with routing ✅ (2026-07-26T13:09:09Z)
- [x] **TASK-1.2.4.7** Ã¢â‚¬â€ Write component tests âœ… (2026-07-26T10:17:24Z)

### 1.2.5 Database Schema Foundation

- [x] **TASK-1.2.5.1** Ã¢â‚¬â€ Design initial EF Core DbContext âœ… (2026-07-26T10:17:24Z)
- [x] **TASK-1.2.5.2** Ã¢â‚¬â€ Create migration for core entities (Tenant, Organisation, Factory, User, Role) ✅ (2026-07-26T13:09:09Z)
- [x] **TASK-1.2.5.3** Ã¢â‚¬â€ Create migration for Station, Camera, CalibrationRecord ✅ (2026-07-26T13:09:09Z)
- [x] **TASK-1.2.5.4** Ã¢â‚¬â€ Create migration for GarmentCategory, Style, Size ✅ (2026-07-26T13:09:09Z)
- [x] **TASK-1.2.5.5** Ã¢â‚¬â€ Create audit event schema (append-only) ✅ (2026-07-26T13:09:09Z)
- [x] **TASK-1.2.5.6** Ã¢â‚¬â€ All timestamps stored as UTC `timestamptz` ✅ (2026-07-26T13:09:09Z)
- [x] **TASK-1.2.5.7** Ã¢â‚¬â€ Write integration tests for migrations ✅ (2026-07-26T13:09:09Z)

### 1.2.6 Internationalisation (i18n) Framework

- [x] **TASK-1.2.6.1** Ã¢â‚¬â€ Define i18n architecture for backend (.NET resource files / JSON) âœ… (2026-07-26T10:17:24Z)
- [x] **TASK-1.2.6.2** Ã¢â‚¬â€ Define i18n architecture for frontend (react-i18next / ngx-translate) âœ… (2026-07-26T10:17:24Z)
- [x] **TASK-1.2.6.3** Ã¢â‚¬â€ Create `en` (English) base translation files âœ… (2026-07-26T10:17:24Z)
- [x] **TASK-1.2.6.4** Ã¢â‚¬â€ Implement locale detection middleware âœ… (2026-07-26T10:17:24Z)
- [x] **TASK-1.2.6.5** Ã¢â‚¬â€ Create translation key naming convention ✅ (2026-07-26T13:09:09Z)
- [x] **TASK-1.2.6.6** Ã¢â‚¬â€ Write tests verifying all keys have English translations ✅ (2026-07-26T13:09:09Z)

### 1.2.7 CI/CD Pipeline

- [x] **TASK-1.2.7.1** Ã¢â‚¬â€ Create GitHub Actions workflow: `.NET build + test` (Windows + Linux) âœ… (2026-07-26T10:17:24Z)
- [x] **TASK-1.2.7.2** Ã¢â‚¬â€ Create GitHub Actions workflow: `Python lint + test` (Windows + Linux) âœ… (2026-07-26T10:17:24Z)
- [x] **TASK-1.2.7.3** Ã¢â‚¬â€ Create GitHub Actions workflow: `Frontend lint + test + build` âœ… (2026-07-26T10:17:24Z)
- [x] **TASK-1.2.7.4** Ã¢â‚¬â€ Create GitHub Actions workflow: `Docker compose integration tests` âœ… (2026-07-26T10:17:24Z)
- [x] **TASK-1.2.7.5** Ã¢â‚¬â€ Create GitHub Actions workflow: `Database migration test` âœ… (2026-07-26T10:17:24Z)
- [ ] **TASK-1.2.7.6** Ã¢â‚¬â€ Configure branch protection rules
- [ ] **TASK-1.2.7.7** Ã¢â‚¬â€ Configure code coverage reporting

### 1.2.8 Coding Standards Enforcement

- [x] **TASK-1.2.8.1** Ã¢â‚¬â€ Create `.editorconfig` âœ… (2026-07-26T10:17:24Z)
- [x] **TASK-1.2.8.2** Ã¢â‚¬â€ Create pre-commit hooks (lint, format, type-check) âœ… (2026-07-26T10:17:24Z)
- [x] **TASK-1.2.8.3** Ã¢â‚¬â€ Document coding standards in `docs/standards/CODING-STANDARDS.md` âœ… (2026-07-26T10:17:24Z)
- [ ] **TASK-1.2.8.4** Ã¢â‚¬â€ Enforce all CI checks on PRs

---

## 1.3 Test Cases

| Test ID | Test Description | Type | Expected Result |
|---------|-----------------|------|-----------------|
| T-1.001 | .NET solution builds without warnings | Build | Exit code 0, zero warnings |
| T-1.002 | Python lint passes (Ruff) | Lint | Zero violations |
| T-1.003 | Python type-check passes (Pyright) | Lint | Zero errors |
| T-1.004 | Frontend builds without errors | Build | Exit code 0 |
| T-1.005 | Frontend lint passes | Lint | Zero violations |
| T-1.006 | Database migrations apply cleanly | Integration | All migrations succeed |
| T-1.007 | Database migrations roll back cleanly | Integration | Rollback succeeds |
| T-1.008 | Contract DTOs serialise/deserialise correctly | Unit | Round-trip equality |
| T-1.009 | All i18n keys have English values | Validation | Zero missing keys |
| T-1.010 | OpenAPI spec generates without errors | Build | Valid OpenAPI 3.x JSON |
| T-1.011 | CI pipeline completes on Windows runner | CI | Green status |
| T-1.012 | CI pipeline completes on Linux runner | CI | Green status |
| T-1.013 | Pre-commit hooks block bad formatting | Integration | Commit rejected |
| T-1.014 | Audit event inserts are append-only | Integration | UPDATE/DELETE fails |

---

## 1.4 Exit Criteria

- [ ] All workspace projects build and pass linting
- [ ] Database migrations run forward and backward
- [ ] CI pipeline green on both Windows and Linux runners
- [ ] i18n framework functional with English strings
- [ ] OpenAPI spec auto-generated
- [ ] All test cases pass
- [ ] Coding standards documented and enforced
