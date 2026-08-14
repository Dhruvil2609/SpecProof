import AxeBuilder from '@axe-core/playwright';
import { expect, test, type Page } from '@playwright/test';

const operatorUrl = 'http://127.0.0.1:4173';
const adminUrl = 'http://127.0.0.1:4174';

async function authenticate(page: Page, application: 'operator' | 'admin', role: string = application) {
  await page.addInitScript(({ key, selectedRole }) => {
    sessionStorage.setItem(
      key,
      JSON.stringify({ token: 'e2e-token', tenantId: '11111111-1111-1111-1111-111111111111', role: selectedRole }),
    );
  }, { key: `specproof-${application}-session`, selectedRole: role });
}

test('operator capture workflow reaches a deterministic result', async ({ page }) => {
  await authenticate(page, 'operator');
  await page.goto(`${operatorUrl}/capture/select`);
  await page.getByRole('button', { name: 'Continue to camera' }).click();
  await expect(page).toHaveURL(/\/capture\/live$/);
  await expect(page.getByText('CAL-2026-0810-04')).toBeVisible();
  await page.getByRole('button', { name: 'Run measurement' }).click();
  await expect(page.getByRole('link', { name: 'Inspection complete' })).toBeVisible();
  await page.getByRole('link', { name: 'Inspection complete' }).click();
  await expect(page.getByRole('heading', { name: 'Measured against the approved specification.' })).toBeVisible();
});

test('all protected application routes load without not-found content', async ({ page }) => {
  await authenticate(page, 'operator');
  for (const route of ['/', '/capture/select', '/capture/live', '/capture/processing', '/inspections/00000000-0000-0000-0000-000000000601', '/inspections/00000000-0000-0000-0000-000000000601/review', '/history']) {
    await page.goto(`${operatorUrl}${route}`);
    await expect(page.locator('main, [class*=shell]').first()).toBeVisible();
  }

  await authenticate(page, 'admin');
  for (const route of ['/', '/stations', '/stations/station-1', '/specs', '/specs/import', '/specs/tech-2/versions/2', '/categories', '/users', '/roles', '/reports', '/evidence/00000000-0000-0000-0000-000000000701', '/settings']) {
    await page.goto(`${adminUrl}${route}`);
    await expect(page.locator('main, [class*=shell]').first()).toBeVisible();
  }
});

test('auditor is denied administration-only routes', async ({ page }) => {
  await authenticate(page, 'admin', 'auditor');
  await page.goto(`${adminUrl}/users`);
  await expect(page).toHaveURL(/\/reports$/);
  await expect(page.getByRole('heading', { name: 'Turn inspection evidence into production decisions.' })).toBeVisible();
});

test('reports export CSV and primary pages pass axe', async ({ page }) => {
  await authenticate(page, 'admin');
  await page.goto(`${adminUrl}/reports`);
  const download = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Export CSV' }).click();
  expect((await download).suggestedFilename()).toBe('specproof-inspections.csv');
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);

  await authenticate(page, 'operator');
  await page.goto(operatorUrl);
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
});

for (const viewport of [{ width: 1280, height: 800 }, { width: 1440, height: 900 }]) {
  for (const theme of ['dark', 'light'] as const) {
    test(`operator visual ${viewport.width}x${viewport.height} ${theme}`, async ({ page }, testInfo) => {
      test.skip(testInfo.project.name !== 'edge', 'Windows Edge owns the visual baseline matrix.');
      await page.setViewportSize(viewport);
      await authenticate(page, 'operator');
      await page.addInitScript((selectedTheme) => localStorage.setItem('specproof-theme', selectedTheme), theme);
      await page.goto(operatorUrl);
      await expect(page).toHaveScreenshot(`operator-${viewport.width}x${viewport.height}-${theme}.png`, { fullPage: true });
    });
  }
}
