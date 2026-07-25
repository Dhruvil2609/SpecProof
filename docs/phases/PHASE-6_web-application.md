# Phase 6 — Web Application

**Phase ID:** PHASE-6  
**Status:** `NOT_STARTED`  
**Created:** 2026-07-25T13:15:00Z  
**Last Updated:** 2026-07-25T13:15:00Z  
**Estimated Duration:** 6–8 weeks  
**Dependencies:** Phase 5  
**Language:** en  

---

## 6.1 Objective

Build the operator and admin web applications (React/TypeScript or Angular/TypeScript) with full i18n support, live camera preview, inspection workflows, measurement overlays, reporting dashboards, and user/role management.

---

## 6.2 Tasks

### 6.2.1 Design System and Shell

- [ ] **TASK-6.2.1.1** — Design token system (colours, typography, spacing, breakpoints)
- [ ] **TASK-6.2.1.2** — Component library (buttons, forms, tables, modals, toasts, cards)
- [ ] **TASK-6.2.1.3** — Application shell with responsive sidebar navigation
- [ ] **TASK-6.2.1.4** — Dark mode support
- [ ] **TASK-6.2.1.5** — Loading and error states
- [ ] **TASK-6.2.1.6** — Write component Storybook stories or visual tests

### 6.2.2 i18n Integration

- [ ] **TASK-6.2.2.1** — react-i18next (or Angular i18n) setup
- [ ] **TASK-6.2.2.2** — English (en) base translation file
- [ ] **TASK-6.2.2.3** — Language switcher component
- [ ] **TASK-6.2.2.4** — Date/time formatting (UTC display + local conversion)
- [ ] **TASK-6.2.2.5** — Number and unit formatting (metric/imperial)
- [ ] **TASK-6.2.2.6** — Write i18n completeness tests

### 6.2.3 Operator UI — Capture Workflow

- [ ] **TASK-6.2.3.1** — Order/style/size selection screen
- [ ] **TASK-6.2.3.2** — Live camera preview with depth overlay
- [ ] **TASK-6.2.3.3** — Capture zone framing guide
- [ ] **TASK-6.2.3.4** — Capture trigger and progress indicator
- [ ] **TASK-6.2.3.5** — Recapture instruction screen
- [ ] **TASK-6.2.3.6** — Write capture workflow E2E tests

### 6.2.4 Operator UI — Results and Review

- [ ] **TASK-6.2.4.1** — Pass/fail result display with colour coding
- [ ] **TASK-6.2.4.2** — Measurement overlay on garment image
- [ ] **TASK-6.2.4.3** — Deviation details per POM
- [ ] **TASK-6.2.4.4** — Review workflow for REVIEW-status items
- [ ] **TASK-6.2.4.5** — Inspection history view
- [ ] **TASK-6.2.4.6** — Write results display tests

### 6.2.5 Admin UI — Station Management

- [ ] **TASK-6.2.5.1** — Station list and status dashboard
- [ ] **TASK-6.2.5.2** — Device health details
- [ ] **TASK-6.2.5.3** — Calibration status and history
- [ ] **TASK-6.2.5.4** — Station configuration editor
- [ ] **TASK-6.2.5.5** — Write station management UI tests

### 6.2.6 Admin UI — Spec and Brand Management

- [ ] **TASK-6.2.6.1** — Tech-pack upload and mapping interface
- [ ] **TASK-6.2.6.2** — POM mapping approval workflow UI
- [ ] **TASK-6.2.6.3** — Garment category management
- [ ] **TASK-6.2.6.4** — Spec version history
- [ ] **TASK-6.2.6.5** — Write spec management tests

### 6.2.7 Admin UI — User and Permissions

- [ ] **TASK-6.2.7.1** — User management CRUD
- [ ] **TASK-6.2.7.2** — Role management and assignment
- [ ] **TASK-6.2.7.3** — Permission matrix display
- [ ] **TASK-6.2.7.4** — Tenant/organisation switching
- [ ] **TASK-6.2.7.5** — Write user management tests

### 6.2.8 Reporting Dashboard

- [ ] **TASK-6.2.8.1** — Batch/order summary view
- [ ] **TASK-6.2.8.2** — Defect Pareto analysis charts
- [ ] **TASK-6.2.8.3** — Supplier/style/size trend charts
- [ ] **TASK-6.2.8.4** — Export to CSV/PDF
- [ ] **TASK-6.2.8.5** — Evidence-record inspection viewer
- [ ] **TASK-6.2.8.6** — Write reporting dashboard tests

### 6.2.9 API Client Generation

- [ ] **TASK-6.2.9.1** — Auto-generate TypeScript API client from OpenAPI spec
- [ ] **TASK-6.2.9.2** — Type-safe API hooks/services
- [ ] **TASK-6.2.9.3** — Error handling and retry logic
- [ ] **TASK-6.2.9.4** — Write API client integration tests

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

- [ ] Operator capture workflow runs end-to-end
- [ ] Admin UI manages stations, specs, users, and permissions
- [ ] i18n framework works with English; new languages addable
- [ ] Reporting dashboards display accurate data
- [ ] All test cases pass on Chrome and Edge
- [ ] No accessibility violations (WCAG 2.1 AA basic checks)
