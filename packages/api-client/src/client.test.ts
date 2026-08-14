import { afterEach, describe, expect, it, vi } from 'vitest';

import { ApiError, HttpSpecProofClient } from './client';

describe('HttpSpecProofClient', () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it('retries idempotent reads on 503 and preserves authorization', async () => {
    vi.useFakeTimers();
    const fetchMock = vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(new Response(JSON.stringify({ status: 503 }), { status: 503 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ status: 503 }), { status: 503 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ inspections: [], stations: [], techPacks: [], users: [], evidence: [] }), { status: 200 }));
    const client = new HttpSpecProofClient('https://platform.test', () => 'jwt-token');

    const promise = client.getDashboard();
    await vi.runAllTimersAsync();
    const result = await promise;

    expect(result.inspections).toEqual([]);
    expect(fetchMock).toHaveBeenCalledTimes(3);
    const firstRequest = fetchMock.mock.calls[0];
    const headers = new Headers(firstRequest?.[1]?.headers);
    expect(headers.get('authorization')).toBe('Bearer jwt-token');
  });

  it('does not retry mutations and returns RFC 7807 details', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(
        JSON.stringify({ status: 422, title: 'Validation failed', detail: 'Outcome is required' }),
        { status: 422, headers: { 'content-type': 'application/problem+json' } },
      ),
    );
    const client = new HttpSpecProofClient('https://platform.test', () => null);

    await expect(client.reviewInspection('inspection-1', '', '')).rejects.toMatchObject<ApiError>({
      problem: { status: 422, title: 'Validation failed', detail: 'Outcome is required' },
    });
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});
