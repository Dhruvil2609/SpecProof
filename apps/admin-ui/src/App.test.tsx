import { ThemeProvider } from '@specproof/web-ui';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { App } from './App';
import './i18n';

function renderApp(path: string, authenticated: boolean) {
  if (authenticated) {
    window.sessionStorage.setItem(
      'specproof-admin-session',
      JSON.stringify({ token: 'test-token', tenantId: 'test-tenant', role: 'admin' }),
    );
  }
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <MemoryRouter initialEntries={[path]}>
      <QueryClientProvider client={queryClient}>
        <ThemeProvider>
          <App />
        </ThemeProvider>
      </QueryClientProvider>
    </MemoryRouter>,
  );
}

describe('Admin application', () => {
  beforeEach(() => {
    window.sessionStorage.clear();
    window.localStorage.clear();
  });

  it('should protect administration routes', async () => {
    renderApp('/stations', false);
    expect(await screen.findByRole('heading', { name: 'The control plane behind every measurement.' })).toBeDefined();
  });

  it('should render station health management', async () => {
    renderApp('/stations', true);
    expect(await screen.findByRole('heading', { name: 'Capture infrastructure across the factory floor.' })).toBeDefined();
    expect(screen.getByText('STN-LON-01')).toBeDefined();
    expect(screen.getAllByText('ONLINE').length).toBeGreaterThan(0);
  });

  it('should render canonical tech-pack mappings', async () => {
    renderApp('/specs/tech-2/versions/2', true);
    expect(await screen.findByRole('heading', { name: 'Common Form / CORE-02' })).toBeDefined();
    expect(screen.getByText('Across Front')).toBeDefined();
    expect(screen.getByText('sleeve_opening')).toBeDefined();
  });

  it('should render permission matrix roles', async () => {
    renderApp('/roles', true);
    expect(await screen.findByRole('heading', { name: 'Roles translate policy into enforceable permissions.' })).toBeDefined();
    expect(screen.getByText('specs.manage')).toBeDefined();
    expect(screen.getByText('users.manage')).toBeDefined();
  });

  it('should render reporting and evidence navigation', async () => {
    renderApp('/reports', true);
    expect(await screen.findByRole('heading', { name: 'Turn inspection evidence into production decisions.' })).toBeDefined();
    expect(screen.getByText('Defect Pareto')).toBeDefined();
    expect(screen.getAllByRole('link').some((link) => link.getAttribute('href')?.startsWith('/evidence/'))).toBe(true);
  });

  it.each([
    ['/specs', 'Approved definitions become executable proof.'],
    ['/specs/import', 'Import a structured tech pack.'],
    ['/categories', 'Manage measurable garment categories.'],
    ['/users', 'Give each person only the access they need.'],
    ['/settings', 'Tenant and display preferences.'],
    ['/evidence/00000000-0000-0000-0000-000000000701', 'Verify the record behind the decision.'],
  ])('should render the administration route %s', async (path, heading) => {
    renderApp(path, true);
    expect(await screen.findByRole('heading', { name: heading })).toBeDefined();
  });

  it('should append interactive category, user, and tenant state', async () => {
    const categories = renderApp('/categories', true);
    fireEvent.change(await screen.findByLabelText('Category name'), { target: { value: 'Sweatshirt' } });
    fireEvent.click(screen.getByRole('button', { name: 'Add category' }));
    expect(screen.getByText('Sweatshirt')).toBeDefined();
    categories.unmount();

    const users = renderApp('/users', true);
    const deactivate = await screen.findAllByRole('button', { name: 'Deactivate' });
    const firstDeactivate = deactivate.at(0);
    if (firstDeactivate === undefined) throw new Error('Expected an active user');
    fireEvent.click(firstDeactivate);
    expect(screen.getAllByText('Inactive').length).toBeGreaterThan(0);
    users.unmount();

    renderApp('/settings', true);
    fireEvent.click(await screen.findByRole('button', { name: 'Switch tenant' }));
    expect((await screen.findByRole('status')).textContent).toContain('Tenant context updated');
  });
});
