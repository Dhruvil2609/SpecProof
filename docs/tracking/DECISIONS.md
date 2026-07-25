# SpecProof — Architecture Decision Records (ADR)

**Created:** 2026-07-25T13:15:00Z  
**Last Updated:** 2026-07-25T13:15:00Z  
**Timezone:** UTC  
**Language:** en  

---

## ADR Index

| ADR | Title | Status | Date (UTC) |
|-----|-------|--------|------------|
| ADR-001 | Use UTC for all timestamps | Accepted | 2026-07-25T13:15:00Z |
| ADR-002 | Monorepo with workspace structure | Accepted | 2026-07-25T13:15:00Z |
| ADR-003 | i18n from day one, English default | Accepted | 2026-07-25T13:15:00Z |
| ADR-004 | All development by AI Codex with auto-testing | Accepted | 2026-07-25T13:15:00Z |

---

## ADR-001: Use UTC for All Timestamps

**Status:** Accepted  
**Date:** 2026-07-25T13:15:00Z  

### Context
SpecProof is a globally-available system used across time zones. Consistent timestamps are critical for audit trails, evidence records, and cross-site comparisons.

### Decision
All timestamps in code, database, API, logs, and documentation use UTC. Display layers convert to local time for user presentation.

### Consequences
- Database columns use `timestamptz` (PostgreSQL) storing UTC
- API responses include ISO 8601 timestamps with `Z` suffix
- Frontend converts UTC to local time for display
- Logs use UTC exclusively
- No DST-related ambiguity in evidence records

---

## ADR-002: Monorepo with Workspace Structure

**Status:** Accepted  
**Date:** 2026-07-25T13:15:00Z  

### Context
SpecProof comprises .NET backend, Python CV/ML services, TypeScript frontend, Docker infrastructure, and shared contracts. These components share types and must be tested together.

### Decision
Use a single monorepo with workspace-level tooling (pnpm workspaces for TS, solution files for .NET, pyproject.toml groups for Python).

### Consequences
- Single source of truth for all contracts
- Atomic cross-component changes in one PR
- CI must build and test all components
- Git LFS for large binary assets

---

## ADR-003: i18n from Day One, English Default

**Status:** Accepted  
**Date:** 2026-07-25T13:15:00Z  

### Context
SpecProof targets UK, European, and global factories. Multi-language support will be needed.

### Decision
Implement i18n framework from the start. English (en) as the default language. All user-visible strings must use translation keys.

### Consequences
- No hardcoded user-facing strings
- Translation files are source-controlled
- New languages added by creating translation files
- Backend API supports `Accept-Language` header
- Frontend supports language switcher

---

## ADR-004: AI Codex Development with Auto-Testing

**Status:** Accepted  
**Date:** 2026-07-25T13:15:00Z  

### Context
All development is performed by AI Codex agents. Every change must be verifiable without human code review being the sole quality gate.

### Decision
Every feature, fix, or change must include automatically generated test cases. AI agents follow skill files that enforce testing, coding standards, and documentation requirements.

### Consequences
- Minimum test coverage enforced per component
- Skill files define agent behaviour per phase
- Progress tracked automatically
- CI blocks merges without passing tests

---

## ADR Template

```markdown
## ADR-NNN: Title

**Status:** Proposed | Accepted | Deprecated | Superseded  
**Date:** YYYY-MM-DDTHH:MM:SSZ  

### Context
Why is this decision needed?

### Decision
What was decided?

### Consequences
What are the results?
```
