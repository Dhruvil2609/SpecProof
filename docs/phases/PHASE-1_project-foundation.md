# Phase 1 — Project Foundation

**Phase ID:** PHASE-1  
**Status:** `NOT_STARTED`  
**Created:** 2026-07-25T13:15:00Z  
**Last Updated:** 2026-07-25T13:15:00Z  
**Estimated Duration:** 2–3 weeks  
**Dependencies:** Phase 0  
**Language:** en  

---

## 1.1 Objective

Establish the monorepo scaffold, shared libraries, database schema foundation, CI/CD pipelines, coding standards enforcement, and i18n framework. This phase creates the architectural skeleton that all subsequent phases build upon.

---

## 1.2 Tasks

### 1.2.1 Monorepo Structure

- [ ] **TASK-1.2.1.1** — Create full directory tree per repository spec (apps/, packages/, native/, ml/, infra/, tests/, tools/)
- [ ] **TASK-1.2.1.2** — Configure workspace-level build orchestration
- [ ] **TASK-1.2.1.3** — Create shared `contracts/` package with API DTOs and event schemas
- [ ] **TASK-1.2.1.4** — Create `camera-abstractions/` package with `ICameraProvider` interface
- [ ] **TASK-1.2.1.5** — Create placeholder projects for all apps and packages

### 1.2.2 .NET Solution Setup

- [ ] **TASK-1.2.2.1** — Create solution file with all .NET projects
- [ ] **TASK-1.2.2.2** — Configure `Directory.Build.props` (nullable, warnings-as-errors, analyzers)
- [ ] **TASK-1.2.2.3** — Configure central package management (`Directory.Packages.props`)
- [ ] **TASK-1.2.2.4** — Create `platform-api` ASP.NET Core project
- [ ] **TASK-1.2.2.5** — Create `station-host` project
- [ ] **TASK-1.2.2.6** — Add OpenAPI generation
- [ ] **TASK-1.2.2.7** — Add OpenTelemetry instrumentation
- [ ] **TASK-1.2.2.8** — Write unit tests for contract serialisation

### 1.2.3 Python Project Setup

- [ ] **TASK-1.2.3.1** — Configure `pyproject.toml` with dependency groups (runtime, dev, ml, station)
- [ ] **TASK-1.2.3.2** — Configure Ruff linter and formatter
- [ ] **TASK-1.2.3.3** — Configure Pyright type checker
- [ ] **TASK-1.2.3.4** — Create `capture-service` Python package
- [ ] **TASK-1.2.3.5** — Create `measurement-service` Python package
- [ ] **TASK-1.2.3.6** — Create shared geometry utilities package
- [ ] **TASK-1.2.3.7** — Write unit tests for utility functions

### 1.2.4 Frontend Project Setup

- [ ] **TASK-1.2.4.1** — Initialise React/TypeScript project with Vite (or Angular CLI)
- [ ] **TASK-1.2.4.2** — Configure strict TypeScript
- [ ] **TASK-1.2.4.3** — Configure ESLint + Prettier
- [ ] **TASK-1.2.4.4** — Set up i18n framework (react-i18next or Angular i18n)
- [ ] **TASK-1.2.4.5** — Create design system tokens (colours, typography, spacing)
- [ ] **TASK-1.2.4.6** — Create initial layout shell with routing
- [ ] **TASK-1.2.4.7** — Write component tests

### 1.2.5 Database Schema Foundation

- [ ] **TASK-1.2.5.1** — Design initial EF Core DbContext
- [ ] **TASK-1.2.5.2** — Create migration for core entities (Tenant, Organisation, Factory, User, Role)
- [ ] **TASK-1.2.5.3** — Create migration for Station, Camera, CalibrationRecord
- [ ] **TASK-1.2.5.4** — Create migration for GarmentCategory, Style, Size
- [ ] **TASK-1.2.5.5** — Create audit event schema (append-only)
- [ ] **TASK-1.2.5.6** — All timestamps stored as UTC `timestamptz`
- [ ] **TASK-1.2.5.7** — Write integration tests for migrations

### 1.2.6 Internationalisation (i18n) Framework

- [ ] **TASK-1.2.6.1** — Define i18n architecture for backend (.NET resource files / JSON)
- [ ] **TASK-1.2.6.2** — Define i18n architecture for frontend (react-i18next / ngx-translate)
- [ ] **TASK-1.2.6.3** — Create `en` (English) base translation files
- [ ] **TASK-1.2.6.4** — Implement locale detection middleware
- [ ] **TASK-1.2.6.5** — Create translation key naming convention
- [ ] **TASK-1.2.6.6** — Write tests verifying all keys have English translations

### 1.2.7 CI/CD Pipeline

- [ ] **TASK-1.2.7.1** — Create GitHub Actions workflow: `.NET build + test` (Windows + Linux)
- [ ] **TASK-1.2.7.2** — Create GitHub Actions workflow: `Python lint + test` (Windows + Linux)
- [ ] **TASK-1.2.7.3** — Create GitHub Actions workflow: `Frontend lint + test + build`
- [ ] **TASK-1.2.7.4** — Create GitHub Actions workflow: `Docker compose integration tests`
- [ ] **TASK-1.2.7.5** — Create GitHub Actions workflow: `Database migration test`
- [ ] **TASK-1.2.7.6** — Configure branch protection rules
- [ ] **TASK-1.2.7.7** — Configure code coverage reporting

### 1.2.8 Coding Standards Enforcement

- [ ] **TASK-1.2.8.1** — Create `.editorconfig`
- [ ] **TASK-1.2.8.2** — Create pre-commit hooks (lint, format, type-check)
- [ ] **TASK-1.2.8.3** — Document coding standards in `docs/standards/CODING-STANDARDS.md`
- [ ] **TASK-1.2.8.4** — Enforce all CI checks on PRs

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
