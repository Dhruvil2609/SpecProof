import { defineConfig, devices } from '@playwright/test';

const projects: Array<{ name: string; use: Record<string, unknown> }> = [
  { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
];

if (process.platform === 'win32') {
  projects.push({ name: 'edge', use: { ...devices['Desktop Edge'], channel: 'msedge' } });
}

export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  workers: process.env.CI ? 2 : 1,
  retries: process.env.CI ? 2 : 0,
  reporter: process.env.CI ? [['html', { open: 'never' }], ['list']] : 'list',
  projects,
  use: {
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  webServer: [
    {
      command: 'pnpm --filter @specproof/operator-ui exec vite preview --host 127.0.0.1 --port 4173',
      port: 4173,
      reuseExistingServer: !process.env.CI,
    },
    {
      command: 'pnpm --filter @specproof/admin-ui exec vite preview --host 127.0.0.1 --port 4174',
      port: 4174,
      reuseExistingServer: !process.env.CI,
    },
  ],
});
