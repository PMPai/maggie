const API_BASE = '/api';

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

/**
 * Build request headers, attaching the CSRF token from document.cookie
 * for state-changing requests.  Called fresh on each fetch so that a
 * rotated csrf_token (after /auth/refresh) is picked up on retry.
 */
function buildHeaders(method: string, extra?: Record<string, string>): Record<string, string> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json', ...extra };
  if (method !== 'GET' && method !== 'HEAD' && headers['Content-Type'] === 'application/json') {
    if (typeof document !== 'undefined') {
      const csrfCookie = document.cookie.split('; ').find(c => c.startsWith('csrf_token='));
      if (csrfCookie) {
        headers['X-CSRF-Token'] = csrfCookie.split('=')[1];
      }
    }
  }
  return headers;
}

/**
 * Perform a single fetch with credentials and CSRF header.
 * Does NOT handle 401 — that is the caller's responsibility.
 */
async function doFetch(path: string, options?: RequestInit): Promise<Response> {
  if (typeof fetch === 'undefined') {
    throw new ApiError(500, 'fetch not available (SSR)');
  }
  const method = options?.method || 'GET';
  const headers = buildHeaders(method, options?.headers as Record<string, string>);
  return fetch(`${API_BASE}${path}`, {
    ...options,
    credentials: 'include',
    headers,
  });
}

/** Lock so concurrent 401s share a single /auth/refresh call. */
let refreshing: Promise<boolean> | null = null;

async function tryRefresh(): Promise<boolean> {
  if (refreshing) return refreshing;
  refreshing = (async () => {
    try {
      const res = await doFetch('/auth/refresh', { method: 'POST' });
      return res.ok;
    } catch {
      return false;
    } finally {
      refreshing = null;
    }
  })();
  return refreshing;
}

/** Paths that should NOT trigger auto-refresh on 401. */
const NO_REFRESH = ['/auth/login', '/auth/refresh'];

async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  let res = await doFetch(path, options);

  // Auto-refresh on 401: try /auth/refresh once, then retry the original request.
  // Skipped for auth endpoints themselves to avoid infinite loops.
  if (res.status === 401 && !NO_REFRESH.some(p => path.startsWith(p))) {
    const refreshed = await tryRefresh();
    if (refreshed) {
      res = await doFetch(path, options); // re-reads CSRF cookie for the retry
    }
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, err.detail || 'API error');
  }
  return res.json();
}

export const api = {
  get: <T>(path: string) => fetchApi<T>(path),
  post: <T>(path: string, body?: unknown) => fetchApi<T>(path, { method: 'POST', body: body ? JSON.stringify(body) : undefined }),
  put: <T>(path: string, body?: unknown) => fetchApi<T>(path, { method: 'PUT', body: body ? JSON.stringify(body) : undefined }),
  patch: <T>(path: string, body?: unknown) => fetchApi<T>(path, { method: 'PATCH', body: body ? JSON.stringify(body) : undefined }),
  del: <T>(path: string) => fetchApi<T>(path, { method: 'DELETE' }),
  upload: <T>(path: string, formData: FormData) =>
    fetch(`${API_BASE}${path}`, { method: 'POST', body: formData, credentials: 'include' }).then(r => {
      if (!r.ok) throw new ApiError(r.status, 'Upload failed');
      return r.json() as Promise<T>;
    }),
};

import type {
  DashboardSummary,
  PendingApproval,
  MasterBudgetResponse,
} from './types';

export const apiHelpers = {
  getDashboardSummary: () => api.get<DashboardSummary>('/dashboard/summary'),
  getPendingApprovals: (params?: Record<string, string>) => {
    if (!params || Object.keys(params).length === 0) return api.get<{ items: PendingApproval[] }>('/approvals/pending');
    const qs = new URLSearchParams(params).toString();
    return api.get<{ items: PendingApproval[] }>(`/approvals/pending?${qs}`);
  },
  getMasterBudget: (projectId: string, contractId?: string) =>
    api.get<MasterBudgetResponse>(`/projects/${projectId}/master-budget${contractId ? `?contract_id=${encodeURIComponent(contractId)}` : ''}`),
  approveResource: (url: string) => api.post(url),
  rejectResource: (url: string, reason?: string) =>
    api.post(url, reason ? { reason } : undefined),
  patchContractVersion: (versionId: string, body: Record<string, unknown>) =>
    api.patch(`/contracts/contract-versions/${versionId}`, body),
};

export { ApiError };
