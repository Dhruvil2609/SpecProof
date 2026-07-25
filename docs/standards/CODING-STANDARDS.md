# SpecProof — Coding Standards

**Created:** 2026-07-25T13:15:00Z  
**Last Updated:** 2026-07-25T13:15:00Z  
**Timezone:** UTC  
**Language:** en  

---

## 1. General Rules

1. **Production-grade code only** — no TODO hacks, no placeholder implementations
2. **All timestamps UTC** — use `DateTime.UtcNow` (.NET), `datetime.now(UTC)` (Python), `new Date().toISOString()` (JS/TS)
3. **All user-facing strings via i18n** — no hardcoded display text
4. **UTF-8 without BOM** for all source files
5. **LF line endings** in source control (configure `.gitattributes`)
6. **No secrets in source** — use environment variables or secure stores
7. **No absolute paths** in source — use `Path.Combine`, `pathlib.Path`
8. **Platform-specific code behind interfaces** — never call OS APIs directly from domain logic

---

## 2. Python Standards

### Style
- **Formatter:** Ruff (`ruff format`)
- **Linter:** Ruff (`ruff check`)
- **Type checker:** Pyright (strict mode)
- **Line length:** 100 characters
- **Quotes:** Double quotes
- **Imports:** Sorted by Ruff (isort-compatible)

### Conventions
- Type hints on all public functions and methods
- Docstrings: Google style
- Pydantic for data models and validation
- `pathlib.Path` for all file operations
- `datetime.now(timezone.utc)` for timestamps — never naive datetimes
- f-strings for string formatting
- Context managers for resources
- Async where I/O-bound

### Testing
- Framework: pytest
- Fixtures for test data
- Parametrize for multi-case tests
- Coverage: pytest-cov

---

## 3. .NET / C# Standards

### Style
- Follow .NET naming conventions (PascalCase types, camelCase locals)
- Enable nullable reference types project-wide
- Treat warnings as errors in core projects
- Use `Directory.Build.props` for shared settings

### Conventions
- `DateTime.UtcNow` and `DateTimeOffset.UtcNow` — never `DateTime.Now`
- All DB columns use `timestamptz` (PostgreSQL)
- Records for DTOs and value objects
- FluentValidation for request validation
- EF Core with explicit query filters for tenant isolation
- Dependency injection for all services
- OpenTelemetry instrumentation on all public API endpoints

### Testing
- Framework: xUnit
- Mocking: NSubstitute
- Integration: `WebApplicationFactory`
- Coverage: Coverlet

---

## 4. TypeScript / JavaScript Standards

### Style
- **Strict TypeScript** (`"strict": true`)
- **Formatter:** Prettier
- **Linter:** ESLint with TypeScript plugin
- **Line length:** 100 characters

### Conventions
- Explicit return types on exported functions
- `const` by default; `let` only when mutation is needed
- No `any` — use `unknown` and narrow
- ISO 8601 UTC strings for all date/time in API payloads
- All UI strings from i18n translation keys
- Functional components (React) or standalone components (Angular)

### Testing
- Framework: Vitest (React/Vite) or Karma/Jest (Angular)
- Component tests for UI logic
- E2E: Playwright

---

## 5. Database Standards

- PostgreSQL with `timestamptz` for all datetime columns
- UTC stored; application layer converts for display
- All tables have `created_at` and `updated_at` as `timestamptz DEFAULT now()`
- Soft delete where audit requires it; hard delete with retention policy
- Audit tables are append-only (no UPDATE, no DELETE triggers)
- Migrations must be reversible
- Use snake_case for table and column names
- Foreign keys with explicit ON DELETE behaviour
- Indexes on frequently queried columns

---

## 6. API Standards

- RESTful with resource-oriented URLs
- JSON request/response bodies
- ISO 8601 UTC timestamps in all payloads
- RFC 7807 Problem Details for errors
- OpenAPI 3.x spec auto-generated
- API versioning via URL prefix (`/api/v1/`)
- Pagination via `offset`/`limit` or cursor-based
- `Accept-Language` header for i18n

---

## 7. Git Standards

- Conventional Commits: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`
- Branch naming: `phase-N/description` or `feature/description`
- PRs require: passing CI, tests, and description
- No force-push to `main`
- Squash merge to main
- Tag releases with semantic versions

---

## 8. Documentation Standards

- All public APIs documented (XML docs for .NET, docstrings for Python, JSDoc for TS)
- ADRs for significant architectural decisions
- Phase documents updated as tasks complete
- Progress tracker updated after each work session
- Changelog updated with every meaningful change
