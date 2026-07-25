# SpecProof — Agent Rules

## Project Identity
- **Project:** SpecProof — Automated Garment Measurement System
- **Website:** https://specproof.co.uk/
- **Dev Host:** Windows 11 x64
- **Release Targets:** Windows x64, Linux x64, Web (cross-browser)

## Required Skills — Always Load

Before starting ANY task, read and follow ALL of these skill files:

1. `.agents/skills/specproof-development/SKILL.md` — Master development workflow
2. `.agents/skills/specproof-testing/SKILL.md` — Test writing rules
3. `.agents/skills/specproof-python/SKILL.md` — Python code patterns
4. `.agents/skills/specproof-dotnet/SKILL.md` — .NET/C# code patterns
5. `.agents/skills/specproof-frontend/SKILL.md` — Frontend/TypeScript patterns
6. `.agents/skills/specproof-database/SKILL.md` — Database schema and access
7. `.agents/skills/specproof-progress-tracking/SKILL.md` — Progress updates

These are NOT optional. Load the relevant skill for the technology you are working with PLUS the master development skill AND the testing skill AND the progress tracking skill. At minimum, every task requires: `specproof-development` + `specproof-testing` + `specproof-progress-tracking` + the technology-specific skill.

## Mandatory Rules for All Agents

1. **Production-grade code only** — no placeholders, no TODOs, no minimal implementations
2. **All timestamps in UTC** — never use local time in code, database, or logs
3. **All user-facing strings via i18n** — default language is English (`en`)
4. **Every change includes automated tests** — no exceptions
5. **Update progress tracking** after completing any task
6. **Follow coding standards** in `docs/standards/CODING-STANDARDS.md`
7. **Follow test strategy** in `docs/testing/TEST-STRATEGY.md`
8. **Platform-specific code behind interfaces** — domain logic is platform-independent
9. **Use `pathlib.Path`** (Python) and **`Path.Combine`** (.NET) — no hardcoded paths
10. **Cross-platform data formats** — JSON, PNG, PLY, glTF, Parquet, UTF-8

## UTC Timestamp Rules (All Languages)

```python
# Python — CORRECT
from datetime import datetime, timezone
now = datetime.now(timezone.utc)

# Python — WRONG (never use)
now = datetime.now()        # naive local time
now = datetime.utcnow()    # naive UTC (deprecated)
```

```csharp
// C# — CORRECT
var now = DateTime.UtcNow;
var nowOffset = DateTimeOffset.UtcNow;

// C# — WRONG (never use)
var now = DateTime.Now;
```

```typescript
// TypeScript — CORRECT
const now = new Date().toISOString(); // "2026-07-25T13:15:00.000Z"
```

```sql
-- PostgreSQL — CORRECT
created_at_utc timestamptz NOT NULL DEFAULT now()

-- WRONG (never use timestamp without time zone)
```

## i18n Rules (All Layers)

- Frontend: All display strings via `useTranslation()` (react-i18next) or equivalent
- Backend .NET: Localised via `Accept-Language` header and resource files
- Backend Python: Log messages in English; API responses localised
- Database: Store canonical IDs, never translated strings
- Evidence records: Language-neutral (status codes, SI units, ISO 8601 UTC)
- Default language: `en` (English)

## Testing Rules (All Code)

- Every feature, fix, or refactor MUST include tests
- Unit tests: `test_{feature}_{scenario}_{expected}` (Python), `{Method}_{Scenario}_{Expected}` (.NET)
- Coverage minimums: Domain 90%, API 85%, Geometry 85%, DB 80%, Frontend 75%
- Use AAA pattern: Arrange → Act → Assert
- Float comparisons: `pytest.approx()`, `Assert.InRange()`, `toBeCloseTo()`
- All test timestamps in UTC
- No production data in tests
- Tests must be independent and idempotent

## Path Handling (All Code)

```python
# Python
from pathlib import Path
capture_dir = Path("captures") / station_id / capture_id
```

```csharp
// C#
var capturePath = Path.Combine("captures", stationId, captureId);
```

- No hardcoded drive letters or slash direction
- Store logical object keys in database, not absolute paths
- Treat filenames as case-sensitive in tests

## Database Rules

- PostgreSQL with `timestamptz` for all datetime columns
- All tables: `created_at_utc` and `updated_at_utc` columns
- Snake_case for table and column names
- Audit tables are append-only (triggers prevent UPDATE/DELETE)
- Tenant isolation via RLS or EF Core query filters
- Migrations must be reversible

## Progress Tracking (After Every Task)

1. Mark task `[x]` in phase document with UTC timestamp
2. Update task counts in `docs/tracking/PROGRESS.md`
3. Add entry to `docs/tracking/CHANGELOG.md`
4. Update phase status if applicable

## Key Documents
- Requirements: `SpecProof_Project_Requirements_and_Analysis.md`
- Dev Environment: `SpecProof_Development_Environment_Requirements.md`
- Phases: `docs/phases/PHASE-*.md`
- Progress: `docs/tracking/PROGRESS.md`
- Changelog: `docs/tracking/CHANGELOG.md`
- Decisions: `docs/tracking/DECISIONS.md`
- Tests: `docs/testing/TEST-STRATEGY.md`
- Standards: `docs/standards/CODING-STANDARDS.md`
- i18n: `docs/i18n/I18N-STRATEGY.md`
