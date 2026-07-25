# SpecProof — Internationalisation (i18n) Strategy

**Created:** 2026-07-25T13:15:00Z  
**Last Updated:** 2026-07-25T13:15:00Z  
**Timezone:** UTC  
**Language:** en  

---

## 1. Overview

SpecProof is designed for global deployment across UK, European, and international factories. The i18n architecture must be built in from day one so that adding new languages requires only translation files, not code changes.

**Default language:** English (`en`)  
**Framework:** i18n-ready across all layers (backend, frontend, documentation)

---

## 2. Supported Languages

| Code | Language | Status | Priority |
|------|----------|--------|----------|
| `en` | English | Active (default) | P0 |
| — | (Future languages) | Planned | P1+ |

New languages will be added by creating translation files following the structure below.

---

## 3. Architecture

### 3.1 Frontend (React/Angular)

**Library:** `react-i18next` (React) or `@ngx-translate/core` (Angular)

```text
src/
  i18n/
    locales/
      en/
        common.json        # Shared strings
        capture.json        # Capture workflow
        measurement.json    # Measurement display
        admin.json          # Admin UI
        errors.json         # Error messages
      {lang}/               # Future language folders
        common.json
        ...
    i18n.ts                 # Configuration
```

**Rules:**
- All user-visible strings use translation keys
- Keys follow `namespace.section.key` format (e.g., `capture.workflow.place_garment`)
- Interpolation for dynamic values: `{{count}}`, `{{name}}`
- Pluralisation rules per language
- Date/time formatting via `Intl.DateTimeFormat` (UTC source, local display)
- Number formatting via `Intl.NumberFormat` (metric default)

### 3.2 Backend (.NET)

**Approach:** JSON-based resource files or .resx files

```text
Resources/
  Strings/
    en.json
    {lang}.json
```

**Rules:**
- API error messages localised via `Accept-Language` header
- Validation messages localised
- Report/export content localised
- Database stores canonical IDs, not display strings
- Evidence records use language-neutral keys, never translated strings

### 3.3 Backend (Python)

**Approach:** `gettext` or JSON resource files

**Rules:**
- Service log messages in English (machine-readable, not localised)
- User-facing API responses localised
- Model outputs use canonical IDs

---

## 4. Translation Key Naming Convention

```text
{namespace}.{section}.{key}

Examples:
  common.buttons.save
  common.buttons.cancel
  capture.workflow.place_garment
  capture.workflow.capture_in_progress
  capture.errors.camera_not_found
  measurement.result.pass
  measurement.result.fail
  measurement.result.review
  admin.stations.register_new
  admin.users.create_user
```

---

## 5. Date, Time, and Number Formatting

| Data Type | Storage Format | API Format | Display Format |
|-----------|---------------|------------|----------------|
| Datetime | UTC `timestamptz` | ISO 8601 with `Z` | Localised via `Intl` |
| Duration | Seconds (integer) | ISO 8601 duration | Localised |
| Distance | Millimetres (float) | Millimetres | mm / inches per locale |
| Weight | Grams (float) | Grams | g / oz per locale |
| Temperature | Celsius (float) | Celsius | °C / °F per locale |
| Currency | Pence/cents (integer) | ISO 4217 | Localised |

---

## 6. Adding a New Language

1. Create a new folder under `src/i18n/locales/{lang}/`
2. Copy all JSON files from `en/`
3. Translate all values (keys remain unchanged)
4. Add language to supported languages table
5. Run `i18n:check` to verify completeness
6. Submit PR — CI verifies all keys present

---

## 7. Testing

| Test | Description |
|------|------------|
| Key completeness | Every key in `en` exists in every other language file |
| No hardcoded strings | Static analysis detects string literals in JSX/templates |
| Date formatting | UTC dates display correctly in all locales |
| Pluralisation | Correct plural forms for test languages |
| RTL support | Layout does not break (future, if Arabic/Hebrew added) |

---

## 8. Evidence Record Language Policy

Evidence records are **language-neutral**. They store:
- Canonical POM IDs (not translated names)
- Status codes (`PASS`, `FAIL`, `REVIEW`, `INVALID`)
- Numeric values in SI units
- ISO 8601 UTC timestamps

Display layers translate these for human consumption. This ensures records are globally portable.
