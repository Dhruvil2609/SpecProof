# Phase 6 — Web Application

**Phase ID:** PHASE-6  
**Status:** `IN_PROGRESS`  
**Created:** 2026-07-25T13:15:00Z  
**Last Updated:** 2026-08-14T18:25:20Z
**Estimated Duration:** 6–8 weeks  
**Dependencies:** Phase 5  
**Language:** en  

---

## 6.1 Objective

Build the operator and admin web applications (React/TypeScript or Angular/TypeScript) with full i18n support, live camera preview, inspection workflows, measurement overlays, reporting dashboards, and user/role management.

Hardware is not required for Phase 6 coding. Live preview, capture workflow, station
health, calibration status, and result review should be implemented against simulated
station APIs, mock gRPC/web adapters, replay packages, and seeded platform data.

---

## 6.2 Tasks

### 6.2.1 Design System and Shell

- [x] **TASK-6.2.1.1** — Design token system (colours, typography, spacing, breakpoints)
- [x] **TASK-6.2.1.2** — Component library (buttons, forms, tables, modals, toasts, cards)
- [x] **TASK-6.2.1.3** — Application shell with responsive sidebar navigation
- [x] **TASK-6.2.1.4** — Dark mode support
- [x] **TASK-6.2.1.5** — Loading and error states
- [x] **TASK-6.2.1.6** — Write component Storybook stories or visual tests

### 6.2.2 i18n Integration

- [x] **TASK-6.2.2.1** — react-i18next (or Angular i18n) setup
- [x] **TASK-6.2.2.2** — English (en) base translation file
- [x] **TASK-6.2.2.3** — Language switcher component
- [x] **TASK-6.2.2.4** — Date/time formatting (UTC display + local conversion)
- [x] **TASK-6.2.2.5** — Number and unit formatting (metric/imperial)
- [x] **TASK-6.2.2.6** — Write i18n completeness tests

### 6.2.3 Operator UI — Capture Workflow

- [x] **TASK-6.2.3.1** — Order/style/size selection screen
- [x] **TASK-6.2.3.2** — Live camera preview with depth overlay
- [x] **TASK-6.2.3.3** — Capture zone framing guide
- [x] **TASK-6.2.3.4** — Capture trigger and progress indicator
- [x] **TASK-6.2.3.5** — Recapture instruction screen
- [x] **TASK-6.2.3.6** — Write capture workflow E2E tests

### 6.2.4 Operator UI — Results and Review

- [x] **TASK-6.2.4.1** — Pass/fail result display with colour coding
- [x] **TASK-6.2.4.2** — Measurement overlay on garment image
- [x] **TASK-6.2.4.3** — Deviation details per POM
- [x] **TASK-6.2.4.4** — Review workflow for REVIEW-status items
- [x] **TASK-6.2.4.5** — Inspection history view
- [x] **TASK-6.2.4.6** — Write results display tests

### 6.2.5 Admin UI — Station Management

- [x] **TASK-6.2.5.1** — Station list and status dashboard
- [x] **TASK-6.2.5.2** — Device health details
- [x] **TASK-6.2.5.3** — Calibration status and history
- [x] **TASK-6.2.5.4** — Station configuration editor
- [x] **TASK-6.2.5.5** — Write station management UI tests

### 6.2.6 Admin UI — Spec and Brand Management

- [x] **TASK-6.2.6.1** — Tech-pack upload and mapping interface
- [x] **TASK-6.2.6.2** — POM mapping approval workflow UI
- [x] **TASK-6.2.6.3** — Garment category management
- [x] **TASK-6.2.6.4** — Spec version history
- [x] **TASK-6.2.6.5** — Write spec management tests

### 6.2.7 Admin UI — User and Permissions

- [x] **TASK-6.2.7.1** — User management CRUD
- [x] **TASK-6.2.7.2** — Role management and assignment
- [x] **TASK-6.2.7.3** — Permission matrix display
- [x] **TASK-6.2.7.4** — Tenant/organisation switching
- [x] **TASK-6.2.7.5** — Write user management tests

### 6.2.8 Reporting Dashboard

- [x] **TASK-6.2.8.1** — Batch/order summary view
- [x] **TASK-6.2.8.2** — Defect Pareto analysis charts
- [x] **TASK-6.2.8.3** — Supplier/style/size trend charts
- [x] **TASK-6.2.8.4** — Export to CSV/PDF
- [x] **TASK-6.2.8.5** — Evidence-record inspection viewer
- [x] **TASK-6.2.8.6** — Write reporting dashboard tests

### 6.2.9 API Client Generation

- [x] **TASK-6.2.9.1** — Auto-generate TypeScript API client from OpenAPI spec
- [x] **TASK-6.2.9.2** — Type-safe API hooks/services
- [x] **TASK-6.2.9.3** — Error handling and retry logic
- [x] **TASK-6.2.9.4** — Write API client integration tests

---

## 6.3 Test Cases

| Test ID | Test Description | Type | Expected Result |
|---------|-----------------|------|-----------------|
| T-6.001 | Application loads and renders shell | E2E | No console errors |
| T-6.002 | All routes are accessible | E2E | No 404s |
| T-6.003 | i18n keys all resolve in English | Unit | Zero missing keys |
| T-6.004 | Language switcher changes display language | E2E | UI text changes |
| T-6.005 | UTC timestamps display correctly | Unit | Correct formatting |
| T-6.006 | Capture workflow completes end-to-end | E2E | Result displayed |
| T-6.007 | PASS result shows green indicator | Visual | Green colour shown |
| T-6.008 | FAIL result shows deviation details | E2E | All POMs listed |
| T-6.009 | Admin cannot access without role | Security | Redirected to login |
| T-6.010 | CSV export downloads valid file | E2E | Valid CSV content |
| T-6.011 | Responsive layout on 1280px+ | Visual | No overflow/clipping |
| T-6.012 | Dark mode toggles correctly | Visual | Theme switches |
| T-6.013 | Generated API client matches spec | Build | Type-check passes |
| T-6.014 | Cross-browser: Chrome + Edge | E2E | Both pass |

---

## 6.4 Exit Criteria

- [x] Operator capture workflow runs end-to-end
- [x] Admin UI manages stations, specs, users, and permissions
- [x] i18n framework works with English; new languages addable
- [x] Reporting dashboards display accurate data
- [ ] All test cases pass on Chrome and Edge
- [x] No accessibility violations (WCAG 2.1 AA basic checks)

When hardware becomes available, the same UI workflows must be rerun against a live
station. That hardware pass is acceptance evidence, not a blocker for UI development.
