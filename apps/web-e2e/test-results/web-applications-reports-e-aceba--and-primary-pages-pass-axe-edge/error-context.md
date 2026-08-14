# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: web-applications.spec.ts >> reports export CSV and primary pages pass axe
- Location: tests\web-applications.spec.ts:49:1

# Error details

```
Error: expect(received).toEqual(expected) // deep equality

- Expected  -  1
+ Received  + 86

- Array []
+ Array [
+   Object {
+     "description": "Ensure each HTML document contains a non-empty <title> element",
+     "help": "Documents must have <title> element to aid in navigation",
+     "helpUrl": "https://dequeuniversity.com/rules/axe/4.13/document-title?application=playwright",
+     "id": "document-title",
+     "impact": "serious",
+     "nodes": Array [
+       Object {
+         "all": Array [],
+         "any": Array [
+           Object {
+             "data": null,
+             "id": "doc-has-title",
+             "impact": "serious",
+             "message": "Document does not have a non-empty <title> element",
+             "relatedNodes": Array [],
+           },
+         ],
+         "failureSummary": "Fix any of the following:
+   Document does not have a non-empty <title> element",
+         "html": "<html data-theme=\"dark\">",
+         "impact": "serious",
+         "none": Array [],
+         "target": Array [
+           "html",
+         ],
+       },
+     ],
+     "tags": Array [
+       "cat.text-alternatives",
+       "wcag2a",
+       "wcag242",
+       "TTv5",
+       "TT12.a",
+       "EN-301-549",
+       "EN-9.2.4.2",
+       "ACT",
+       "RGAAv4",
+       "RGAA-8.5.1",
+     ],
+   },
+   Object {
+     "description": "Ensure every HTML document has a lang attribute",
+     "help": "<html> element must have a lang attribute",
+     "helpUrl": "https://dequeuniversity.com/rules/axe/4.13/html-has-lang?application=playwright",
+     "id": "html-has-lang",
+     "impact": "serious",
+     "nodes": Array [
+       Object {
+         "all": Array [],
+         "any": Array [
+           Object {
+             "data": Object {
+               "messageKey": "noLang",
+             },
+             "id": "has-lang",
+             "impact": "serious",
+             "message": "The <html> element does not have a lang attribute",
+             "relatedNodes": Array [],
+           },
+         ],
+         "failureSummary": "Fix any of the following:
+   The <html> element does not have a lang attribute",
+         "html": "<html data-theme=\"dark\">",
+         "impact": "serious",
+         "none": Array [],
+         "target": Array [
+           "html",
+         ],
+       },
+     ],
+     "tags": Array [
+       "cat.language",
+       "wcag2a",
+       "wcag311",
+       "TTv5",
+       "TT11.a",
+       "EN-301-549",
+       "EN-9.3.1.1",
+       "ACT",
+       "RGAAv4",
+       "RGAA-8.3.1",
+     ],
+   },
+ ]
```

# Page snapshot

```yaml
- generic [ref=e1]:
  - generic [ref=e3]:
    - complementary [ref=e4]:
      - generic [ref=e5]:
        - generic [ref=e6]: S
        - generic [ref=e7]:
          - strong [ref=e8]: SpecProof
          - generic [ref=e9]: Administration
      - navigation "Administration" [ref=e10]:
        - link "Control room" [ref=e11] [cursor=pointer]:
          - /url: /
        - link "Stations" [ref=e20] [cursor=pointer]:
          - /url: /stations
        - link "Specs & brands" [ref=e27] [cursor=pointer]:
          - /url: /specs
        - link "Categories" [ref=e35] [cursor=pointer]:
          - /url: /categories
        - link "Users" [ref=e41] [cursor=pointer]:
          - /url: /users
        - link "Roles & permissions" [ref=e50] [cursor=pointer]:
          - /url: /roles
        - link "Reporting" [ref=e57] [cursor=pointer]:
          - /url: /reports
        - link "Settings" [ref=e63] [cursor=pointer]:
          - /url: /settings
      - generic [ref=e72]:
        - generic [ref=e73]:
          - generic [ref=e78]: Language
          - combobox "Language" [ref=e79]:
            - option "EN" [selected]
            - option "QA"
        - button "Use light theme" [ref=e80] [cursor=pointer]
    - generic [ref=e87]:
      - banner [ref=e88]:
        - button "Administration" [ref=e89] [cursor=pointer]
        - generic [ref=e91]: SPEC / PROOF
        - generic [ref=e92]:
          - generic [ref=e93]:
            - generic [ref=e98]: Language
            - combobox "Language" [ref=e99]:
              - option "EN" [selected]
              - option "QA"
          - button "Use light theme" [ref=e100] [cursor=pointer]
      - main [ref=e107]:
        - generic [ref=e108]:
          - generic [ref=e109]:
            - paragraph [ref=e110]: Quality intelligence
            - heading "Turn inspection evidence into production decisions." [level=1] [ref=e111]
            - paragraph [ref=e112]: Defect concentration and trends by supplier, style, and size.
          - generic [ref=e113]:
            - button "Export CSV" [active] [ref=e114] [cursor=pointer]
            - button "Export PDF" [ref=e115] [cursor=pointer]
        - generic [ref=e116]:
          - generic [ref=e117]:
            - heading "Defect Pareto" [level=2] [ref=e118]
            - application [ref=e121]:
              - generic [ref=e149]:
                - generic [ref=e150]:
                  - generic [ref=e151]: Shoulder
                  - generic [ref=e153]: Body length
                  - generic [ref=e155]: Sleeve
                  - generic [ref=e157]: Chest
                - generic [ref=e159]:
                  - generic [ref=e160]: "0"
                  - generic [ref=e162]: "5"
                  - generic [ref=e164]: "10"
                  - generic [ref=e166]: "15"
                  - generic [ref=e168]: "20"
          - generic [ref=e170]:
            - heading "Pass-rate trend" [level=2] [ref=e171]
            - application [ref=e174]:
              - generic [ref=e197]:
                - generic [ref=e198]:
                  - generic [ref=e199]: Mon
                  - generic [ref=e201]: Tue
                  - generic [ref=e203]: Wed
                  - generic [ref=e205]: Thu
                  - generic [ref=e207]: Fri
                - generic [ref=e209]:
                  - generic [ref=e210]: "80"
                  - generic [ref=e212]: "85"
                  - generic [ref=e214]: "90"
                  - generic [ref=e216]: "95"
                  - generic [ref=e218]: "100"
        - generic [ref=e220]:
          - heading "Batch summary" [level=2] [ref=e221]
          - generic [ref=e222]:
            - link "00000000-0000-0000-0000-000000000601" [ref=e223] [cursor=pointer]:
              - /url: /evidence/evidence-1
            - link "00000000-0000-0000-0000-000000000602" [ref=e227] [cursor=pointer]:
              - /url: /evidence/evidence-2
            - link "00000000-0000-0000-0000-000000000603" [ref=e231] [cursor=pointer]:
              - /url: /evidence/evidence-3
  - generic [ref=e235]: "80"
```

# Test source

```ts
  1  | import AxeBuilder from '@axe-core/playwright';
  2  | import { expect, test, type Page } from '@playwright/test';
  3  | 
  4  | const operatorUrl = 'http://127.0.0.1:4173';
  5  | const adminUrl = 'http://127.0.0.1:4174';
  6  | 
  7  | async function authenticate(page: Page, application: 'operator' | 'admin', role: string = application) {
  8  |   await page.addInitScript(({ key, selectedRole }) => {
  9  |     sessionStorage.setItem(
  10 |       key,
  11 |       JSON.stringify({ token: 'e2e-token', tenantId: '11111111-1111-1111-1111-111111111111', role: selectedRole }),
  12 |     );
  13 |   }, { key: `specproof-${application}-session`, selectedRole: role });
  14 | }
  15 | 
  16 | test('operator capture workflow reaches a deterministic result', async ({ page }) => {
  17 |   await authenticate(page, 'operator');
  18 |   await page.goto(`${operatorUrl}/capture/select`);
  19 |   await page.getByRole('button', { name: 'Continue to camera' }).click();
  20 |   await expect(page).toHaveURL(/\/capture\/live$/);
  21 |   await expect(page.getByText('CAL-2026-0810-04')).toBeVisible();
  22 |   await page.getByRole('button', { name: 'Run measurement' }).click();
  23 |   await expect(page.getByRole('link', { name: 'Inspection complete' })).toBeVisible();
  24 |   await page.getByRole('link', { name: 'Inspection complete' }).click();
  25 |   await expect(page.getByRole('heading', { name: 'Measured against the approved specification.' })).toBeVisible();
  26 | });
  27 | 
  28 | test('all protected application routes load without not-found content', async ({ page }) => {
  29 |   await authenticate(page, 'operator');
  30 |   for (const route of ['/', '/capture/select', '/capture/live', '/capture/processing', '/inspections/00000000-0000-0000-0000-000000000601', '/inspections/00000000-0000-0000-0000-000000000601/review', '/history']) {
  31 |     await page.goto(`${operatorUrl}${route}`);
  32 |     await expect(page.locator('main, [class*=shell]').first()).toBeVisible();
  33 |   }
  34 | 
  35 |   await authenticate(page, 'admin');
  36 |   for (const route of ['/', '/stations', '/stations/station-1', '/specs', '/specs/import', '/specs/tech-2/versions/2', '/categories', '/users', '/roles', '/reports', '/evidence/00000000-0000-0000-0000-000000000701', '/settings']) {
  37 |     await page.goto(`${adminUrl}${route}`);
  38 |     await expect(page.locator('main, [class*=shell]').first()).toBeVisible();
  39 |   }
  40 | });
  41 | 
  42 | test('auditor is denied administration-only routes', async ({ page }) => {
  43 |   await authenticate(page, 'admin', 'auditor');
  44 |   await page.goto(`${adminUrl}/users`);
  45 |   await expect(page).toHaveURL(/\/reports$/);
  46 |   await expect(page.getByRole('heading', { name: 'Turn inspection evidence into production decisions.' })).toBeVisible();
  47 | });
  48 | 
  49 | test('reports export CSV and primary pages pass axe', async ({ page }) => {
  50 |   await authenticate(page, 'admin');
  51 |   await page.goto(`${adminUrl}/reports`);
  52 |   const download = page.waitForEvent('download');
  53 |   await page.getByRole('button', { name: 'Export CSV' }).click();
  54 |   expect((await download).suggestedFilename()).toBe('specproof-inspections.csv');
> 55 |   expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
     |                                                                 ^ Error: expect(received).toEqual(expected) // deep equality
  56 | 
  57 |   await authenticate(page, 'operator');
  58 |   await page.goto(operatorUrl);
  59 |   expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
  60 | });
  61 | 
  62 | for (const viewport of [{ width: 1280, height: 800 }, { width: 1440, height: 900 }]) {
  63 |   for (const theme of ['dark', 'light'] as const) {
  64 |     test(`operator visual ${viewport.width}x${viewport.height} ${theme}`, async ({ page }) => {
  65 |       await page.setViewportSize(viewport);
  66 |       await authenticate(page, 'operator');
  67 |       await page.addInitScript((selectedTheme) => localStorage.setItem('specproof-theme', selectedTheme), theme);
  68 |       await page.goto(operatorUrl);
  69 |       await expect(page).toHaveScreenshot(`operator-${viewport.width}x${viewport.height}-${theme}.png`, { fullPage: true });
  70 |     });
  71 |   }
  72 | }
  73 | 
```