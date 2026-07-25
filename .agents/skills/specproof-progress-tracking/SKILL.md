---
name: specproof-progress-tracking
description: Progress tracking skill for SpecProof. ALWAYS ACTIVE — every SpecProof task requires progress updates. Covers updating PROGRESS.md, CHANGELOG.md, phase documents, task status, test counts, and activity logs after any code, test, fix, refactor, document, review, or deployment work.
---

# SpecProof Progress Tracking Skill

## When to Use
Activate this skill after completing any SpecProof development task. Progress must be tracked for every change.

## After Completing a Task

### Step 1: Mark Task Complete in Phase Document
Open the relevant `docs/phases/PHASE-N_*.md` and change:
```markdown
- [ ] **TASK-N.X.Y.Z** — Description
```
to:
```markdown
- [x] **TASK-N.X.Y.Z** — Description ✅ (2026-07-25T13:15:00Z)
```

### Step 2: Update Progress Tracker
Open `docs/tracking/PROGRESS.md` and update:
1. **Phase Summary table** — increment `Tasks Done` and recalculate `Progress`
2. **Test Summary table** — increment test counts by type
3. **Recent Activity Log** — add a new row:

```markdown
| 2026-07-25T13:15:00Z | 2 | TASK-2.2.1.1 | Implemented ICameraProvider | AI Codex | Unit tests passing |
```

### Step 3: Update Changelog
Open `docs/tracking/CHANGELOG.md` and add entry under `[Unreleased]`:

```markdown
### Added
- 2026-07-25T13:15:00Z — Implemented ICameraProvider for RealSense on Windows (TASK-2.2.1.1)
```

Use the correct section:
- `Added` — new features
- `Changed` — changes to existing features
- `Fixed` — bug fixes
- `Removed` — removed features
- `Security` — security-related changes

### Step 4: Update Phase Status
If all tasks in a phase section are complete, update the phase document status:
```markdown
**Status:** `IN_PROGRESS`  →  `COMPLETE`
```

If starting a new phase, update:
```markdown
**Status:** `NOT_STARTED`  →  `IN_PROGRESS`
```

### Step 5: Log Blocked Items
If a task is blocked, add to the Blocked Items table in `docs/tracking/PROGRESS.md`:
```markdown
| TASK-2.2.1.4 | 2 | 2026-07-25T13:15:00Z | Camera SDK not installed | Requires Phase 0 completion |
```

## Status Values
- `NOT_STARTED` — work has not begun
- `IN_PROGRESS` — actively being developed
- `BLOCKED` — blocked by dependency or issue
- `COMPLETE` — finished and all tests pass
- `SKIPPED` — intentionally deferred

## Timestamp Format
Always use ISO 8601 UTC: `YYYY-MM-DDTHH:MM:SSZ`

Example: `2026-07-25T13:15:00Z`

## Progress Calculation
```
Progress = (tasks_done / tasks_total) × 100
```
Round to nearest whole percentage.
