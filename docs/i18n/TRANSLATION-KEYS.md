# Translation Key Naming

SpecProof translation keys use lowercase dot-separated namespaces.

## Format

- Use `{domain}.{name}` for shared labels, for example `navigation.dashboard`.
- Use `{domain}.{section}.{name}` for workflow-specific strings, for example `capture.workflow.ready`.
- Use lowercase ASCII letters, numbers, and underscores inside each segment.
- Keep English values non-empty in every `locales/en/translation.json` file.

## Validation

Frontend i18n key tests run with `pnpm test` and verify that each English key is namespaced and non-empty.
