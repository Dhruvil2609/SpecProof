# SpecProof Coding Standards

All SpecProof code must be type-safe, testable, UTC-aware, and cross-platform.

## General

- Store timestamps as UTC and format logs as ISO 8601.
- Keep user-facing text behind i18n translation keys.
- Prefer dependency injection and explicit interfaces at platform boundaries.
- Use UTF-8 with LF line endings for text files.

## .NET

- Target the SDK pinned by `global.json`.
- Enable nullable reference types and treat warnings as errors.
- Use `DateTimeOffset.UtcNow` or `DateTime.UtcNow`; never use local time.
- Keep API contracts in shared packages and validate JSON round trips with tests.

## Python

- Target Python 3.11 and manage dependencies with `uv`.
- Use `pathlib.Path`, typed models, and timezone-aware datetimes.
- Run Ruff, Pyright, and pytest before completing work.

## Frontend

- Use strict TypeScript with no `any`.
- Use `react-i18next` for display strings.
- Keep accessible labels on navigation and interactive controls.
