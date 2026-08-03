const API_BASE = '/api';

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  const method = options?.method || 'GET';
  const headers: Record<string, string> = { 'Content-Type': 'application/json', ...(options?.headers as Record<string, string>) };

  // Attach CSRF token for state-changing requests (skip multipart — upload uses raw fetch)
  if (method !== 'GET' && method !== 'HEAD' && headers['Content-Type'] === 'application/json') {
    const csrfCookie = document.cookie.split('; ').find(c => c.startsWith('csrf_token='));
    if (csrfCookie) {
      headers['X-CSRF-Token'] = csrfCookie.split('=')[1];
    }
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    credentials: 'include',
    headers,
  });
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
