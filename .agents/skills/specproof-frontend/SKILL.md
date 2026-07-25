---
name: specproof-frontend
description: Frontend development skill for SpecProof web applications. ALWAYS ACTIVE for any React, Angular, TypeScript, JavaScript, UI, component, page, dashboard, operator, admin, web, browser, CSS, i18n, translation, Vite, routing, or design system task. Covers strict TypeScript, react-i18next, API client generation, accessibility, and Vitest/Playwright testing.
---

# SpecProof Frontend Development Skill

## When to Use
Activate this skill when writing TypeScript/JavaScript code for the SpecProof operator UI or admin UI.

## Environment
- React with TypeScript and Vite (preferred) OR Angular with TypeScript
- Package manager: pnpm
- Strict TypeScript enabled
- ESLint + Prettier

## Code Standards

### TypeScript Strict Mode
```json
{
  "compilerOptions": {
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "exactOptionalPropertyTypes": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true
  }
}
```

### i18n — All Strings via Translation Keys
```tsx
// CORRECT
import { useTranslation } from 'react-i18next';

function CaptureButton() {
  const { t } = useTranslation('capture');
  return <button>{t('workflow.start_capture')}</button>;
}

// WRONG — never hardcode user-facing text
function CaptureButton() {
  return <button>Start Capture</button>;
}
```

### Date/Time Display (UTC → Local)
```tsx
function formatTimestamp(utcIso: string, locale: string = 'en-GB'): string {
  return new Intl.DateTimeFormat(locale, {
    dateStyle: 'medium',
    timeStyle: 'medium',
    timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone,
  }).format(new Date(utcIso));
}

// API always sends UTC ISO 8601: "2026-07-25T13:15:00Z"
// Display converts to user's local time
```

### Component Pattern
```tsx
interface InspectionResultProps {
  readonly inspectionId: string;
  readonly status: InspectionStatus;
  readonly measurements: readonly MeasurementDto[];
  readonly capturedAtUtc: string;
}

export function InspectionResult({ 
  inspectionId, 
  status, 
  measurements,
  capturedAtUtc,
}: InspectionResultProps) {
  const { t } = useTranslation('measurement');
  
  return (
    <div id={`inspection-${inspectionId}`} role="article">
      <h2>{t('result.title')}</h2>
      <StatusBadge status={status} />
      <time dateTime={capturedAtUtc}>
        {formatTimestamp(capturedAtUtc)}
      </time>
      <MeasurementTable measurements={measurements} />
    </div>
  );
}
```

### API Client (Auto-generated from OpenAPI)
```tsx
// Generated client from OpenAPI spec — never handwrite API calls
import { InspectionsApi } from '@specproof/api-client';

const api = new InspectionsApi({ basePath: '/api/v1' });
const result = await api.getInspection({ id: inspectionId });
```

### No `any` — Use `unknown` and Narrow
```tsx
// CORRECT
function parseApiResponse(data: unknown): InspectionDto {
  if (!isInspectionDto(data)) {
    throw new ApiParseError('Invalid inspection response');
  }
  return data;
}

// WRONG
function parseApiResponse(data: any): InspectionDto {
  return data;
}
```

## Design System Tokens
```css
:root {
  /* Colours */
  --color-pass: hsl(142, 71%, 45%);
  --color-fail: hsl(0, 84%, 60%);
  --color-review: hsl(45, 93%, 47%);
  --color-invalid: hsl(0, 0%, 60%);
  
  /* Typography */
  --font-family: 'Inter', system-ui, sans-serif;
  --font-size-base: 1rem;
  
  /* Spacing */
  --spacing-xs: 0.25rem;
  --spacing-sm: 0.5rem;
  --spacing-md: 1rem;
  --spacing-lg: 1.5rem;
  --spacing-xl: 2rem;
}
```

## Accessibility
- All interactive elements have unique, descriptive IDs
- ARIA labels on non-text elements
- Keyboard navigation support
- Colour is not the only indicator (icons + text)
- WCAG 2.1 AA basic compliance

## Testing
```tsx
import { render, screen } from '@testing-library/react';
import { InspectionResult } from './InspectionResult';

describe('InspectionResult', () => {
  it('should display PASS status with green badge', () => {
    render(
      <InspectionResult
        inspectionId="test-1"
        status="PASS"
        measurements={mockMeasurements}
        capturedAtUtc="2026-07-25T13:15:00Z"
      />
    );
    
    expect(screen.getByText(/pass/i)).toBeInTheDocument();
  });
});
```

## Browser Support
- Chrome (current)
- Edge (current)
- Firefox (where commercially required)
- No IE, no ActiveX, no COM
