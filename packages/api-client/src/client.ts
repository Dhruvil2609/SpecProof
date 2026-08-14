import type { ApiProblem, DashboardData, Inspection } from './models';

export class ApiError extends Error {
  public constructor(public readonly problem: ApiProblem) {
    super(problem.title ?? `HTTP ${problem.status}`);
  }
}

export interface SpecProofClient {
  getDashboard(signal?: AbortSignal): Promise<DashboardData>;
  getInspection(id: string, signal?: AbortSignal): Promise<Inspection>;
  reviewInspection(id: string, outcome: string, note: string, signal?: AbortSignal): Promise<void>;
}

async function readProblem(response: Response): Promise<ApiProblem> {
  const payload: unknown = await response.json().catch(() => null);
  if (
    typeof payload === 'object' &&
    payload !== null &&
    'status' in payload &&
    typeof payload.status === 'number'
  ) {
    return payload as ApiProblem;
  }
  return { status: response.status, title: response.statusText };
}

export class HttpSpecProofClient implements SpecProofClient {
  public constructor(
    private readonly baseUrl: string,
    private readonly token: () => string | null,
  ) {}

  public async getDashboard(signal?: AbortSignal): Promise<DashboardData> {
    return this.request<DashboardData>('/api/v1/web/dashboard', { method: 'GET', signal: signal ?? null }, true);
  }

  public async getInspection(id: string, signal?: AbortSignal): Promise<Inspection> {
    return this.request<Inspection>(
      `/api/v1/web/inspections/${encodeURIComponent(id)}`,
      { method: 'GET', signal: signal ?? null },
      true,
    );
  }

  public async reviewInspection(
    id: string,
    outcome: string,
    note: string,
    signal?: AbortSignal,
  ): Promise<void> {
    await this.request(
      `/api/v1/web/inspections/${encodeURIComponent(id)}/reviews`,
      {
        method: 'POST',
        signal: signal ?? null,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ outcome, note }),
      },
      false,
    );
  }

  private async request<T>(path: string, init: RequestInit, retryable: boolean): Promise<T> {
    const attempts = retryable ? 3 : 1;
    for (let attempt = 0; attempt < attempts; attempt += 1) {
      const token = this.token();
      const headers = new Headers(init.headers);
      if (token !== null) headers.set('Authorization', `Bearer ${token}`);
      try {
        const response = await fetch(`${this.baseUrl}${path}`, { ...init, headers });
        if (response.ok) {
          return response.status === 204 ? (undefined as T) : ((await response.json()) as T);
        }
        if (
          !retryable ||
          (response.status !== 429 && response.status !== 503) ||
          attempt === attempts - 1
        ) {
          throw new ApiError(await readProblem(response));
        }
      } catch (error: unknown) {
        if (error instanceof ApiError || !retryable || attempt === attempts - 1) throw error;
      }
      await new Promise((resolve) => globalThis.setTimeout(resolve, 150 * 2 ** attempt));
    }
    throw new Error('Unreachable retry state');
  }
}
