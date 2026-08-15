import { ThemeProvider } from '@specproof/web-ui';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { App } from './App';
import './i18n';

function renderApp(path: string, authenticated: boolean) {
  if (authenticated) {
    window.sessionStorage.setItem(
      'specproof-operator-session',
      JSON.stringify({ token: 'test-token', tenantId: 'test-tenant', role: 'operator' }),
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

describe('Operator application', () => {
  beforeEach(() => {
    window.sessionStorage.clear();
    window.localStorage.clear();
  });

  it('should redirect unauthenticated users to the login page', async () => {
    renderApp('/', false);
    expect(await screen.findByRole('heading', { name: 'Measure every unit. Record both sides.' })).toBeDefined();
  });

  it('should render the authenticated production dashboard', async () => {
    renderApp('/', true);
    expect(await screen.findByRole('heading', { name: 'The factory floor, measured in real time.' })).toBeDefined();
    expect(screen.getByText('Recent inspections')).toBeDefined();
  });

  it('should render the order and size capture selection', async () => {
    renderApp('/capture/select', true);
    expect(await screen.findByRole('heading', { name: 'Choose the garment to inspect.' })).toBeDefined();
    expect(screen.getByLabelText('Production order')).toBeDefined();
    expect(screen.getByLabelText('Size')).toBeDefined();
  });

  it('should render measurement deviations and status details', async () => {
    renderApp('/inspections/00000000-0000-0000-0000-000000000601', true);
    expect(await screen.findByRole('heading', { name: 'Measured against the approved specification.' })).toBeDefined();
    expect(screen.getAllByText('Shoulder width').length).toBeGreaterThan(0);
    expect(screen.getAllByText('FAIL').length).toBeGreaterThan(0);
  });

  it('should render the simulated station preview and trigger processing', async () => {
    window.sessionStorage.setItem(
      'specproof-capture-context',
      JSON.stringify({
        orderCode: 'PO-24081',
        styleCode: 'SP-TEE-01',
        sizeCode: 'M',
        batchId: '44444444-4444-4444-4444-444444444441',
        batchCode: 'B-0810-A',
        techPackId: '55555555-5555-5555-5555-555555555555',
        techPackVersion: 1,
      }),
    );
    renderApp('/capture/live', true);

    expect(await screen.findByRole('heading', { name: 'Place the garment inside the calibrated zone.' })).toBeDefined();
    expect(await screen.findByText('CAL-2026-0810-04')).toBeDefined();
    fireEvent.click(screen.getByRole('button', { name: 'Run measurement' }));

    expect(await screen.findByRole('heading', { name: 'Turning pixels into proof.' })).toBeDefined();
  });

  it('should render processing, review, and searchable history routes', async () => {
    window.sessionStorage.setItem(
      'specproof-capture-receipt',
      JSON.stringify({
        captureId: '00000000-0000-0000-0000-000000000601',
        checksumSha256: 'a'.repeat(64),
        calibrationId: 'CAL-2026-0810-04',
        capturedAtUtc: '2026-08-12T10:00:05.000Z',
        inspectionId: '00000000-0000-0000-0000-000000000601',
        processingStatus: 'Completed',
      }),
    );
    const processing = renderApp('/capture/processing', true);
    expect(await screen.findByText('Capture synchronized')).toBeDefined();
    processing.unmount();

    const review = renderApp('/inspections/00000000-0000-0000-0000-000000000601/review', true);
    expect(await screen.findByRole('heading', { name: 'Resolve the uncertain measurement.' })).toBeDefined();
    fireEvent.change(screen.getByLabelText('Review note'), { target: { value: 'Visible seam distortion.' } });
    fireEvent.click(screen.getByRole('button', { name: 'Confirm fail' }));
    expect((await screen.findByRole('status')).textContent).toContain('Review action recorded');
    review.unmount();

    renderApp('/history', true);
    const search = await screen.findByPlaceholderText('Search order, style, or station');
    fireEvent.change(search, { target: { value: 'missing-order' } });
    await waitFor(() => expect(screen.queryByText('PO-24081')).toBeNull());
  });
});
