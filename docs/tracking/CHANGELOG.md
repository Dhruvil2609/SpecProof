# SpecProof ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Changelog

**Timezone:** UTC
**Format:** [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
**Versioning:** [Semantic Versioning](https://semver.org/spec/v2.0.0.html)

---

## [Unreleased]

### Added
- 2026-07-26T13:09:09Z â€” Added Phase 1 database migration foundation, append-only audit trigger migration SQL, frontend routing shells, and i18n key validation tests (TASK-1.2.4.6, TASK-1.2.5.2, TASK-1.2.5.3, TASK-1.2.5.4, TASK-1.2.5.5, TASK-1.2.5.6, TASK-1.2.5.7, TASK-1.2.6.5, TASK-1.2.6.6)
- 2026-07-26T10:17:24Z Ã¢â‚¬â€ Added Phase 1 project foundation scaffold with .NET solution, contracts, camera abstractions, API/station apps, Python service packages, frontend shells, CI workflows, and standards enforcement (TASK-1.2.1.2, TASK-1.2.2.1, TASK-1.2.3.4, TASK-1.2.4.1, TASK-1.2.7.1)
- 2026-07-26T10:17:24Z Ã¢â‚¬â€ Added Phase 1 tests for contract serialization, EF Core model configuration, Python geometry/capture utilities, and frontend i18n shell rendering (TASK-1.2.2.8, TASK-1.2.3.7, TASK-1.2.4.7)
- 2026-07-25T14:32:40Z ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Added 17 unit test cases for `specproof-doctor` version parsing, command failures, result aggregation, formatting, and optional hardware behavior (TASK-0.3.11.4)
- 2026-07-25T14:27:34Z ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Added Phase 0 repository scaffolding, local compose stack, Windows setup guide, and `specproof-doctor` diagnostics (TASK-0.3.7.1, TASK-0.3.10.2, TASK-0.3.10.5, TASK-0.3.11.1)
- 2026-07-25T13:15:00Z ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Project documentation structure created
- 2026-07-25T13:15:00Z ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Development phase documents (Phase 0ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Å“8) created
- 2026-07-25T13:15:00Z ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Progress tracking system initialised
- 2026-07-25T13:15:00Z ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â AI agent skill files created
- 2026-07-25T13:15:00Z ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Test strategy document created
- 2026-07-25T13:15:00Z ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Coding standards document created
- 2026-07-25T13:15:00Z ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â i18n strategy document created

### Changed
- 2026-07-26T13:13:08Z — Updated PostgreSQL development credentials to the requested local-dev username/password across Docker compose, setup docs, CI service env, and EF test connection strings (TASK-0.3.7.1)
- (none)

### Fixed
- (none)

### Removed
- (none)

---

## Template for new entries

```markdown
## [X.Y.Z] ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â YYYY-MM-DDTHH:MM:SSZ

### Added
- 2026-07-26T13:09:09Z â€” Added Phase 1 database migration foundation, append-only audit trigger migration SQL, frontend routing shells, and i18n key validation tests (TASK-1.2.4.6, TASK-1.2.5.2, TASK-1.2.5.3, TASK-1.2.5.4, TASK-1.2.5.5, TASK-1.2.5.6, TASK-1.2.5.7, TASK-1.2.6.5, TASK-1.2.6.6)
- 2026-07-26T10:17:24Z Ã¢â‚¬â€ Added Phase 1 project foundation scaffold with .NET solution, contracts, camera abstractions, API/station apps, Python service packages, frontend shells, CI workflows, and standards enforcement (TASK-1.2.1.2, TASK-1.2.2.1, TASK-1.2.3.4, TASK-1.2.4.1, TASK-1.2.7.1)
- 2026-07-26T10:17:24Z Ã¢â‚¬â€ Added Phase 1 tests for contract serialization, EF Core model configuration, Python geometry/capture utilities, and frontend i18n shell rendering (TASK-1.2.2.8, TASK-1.2.3.7, TASK-1.2.4.7)
- Description of new feature

### Changed
- 2026-07-26T13:13:08Z — Updated PostgreSQL development credentials to the requested local-dev username/password across Docker compose, setup docs, CI service env, and EF test connection strings (TASK-0.3.7.1)
- Description of change to existing functionality

### Fixed
- Description of bug fix

### Removed
- Description of removed feature

### Security
- Description of security-related change
```
