const API_BASE = '/api';

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function doFetch(path: string, options?: RequestInit): Promise<Response> {
  if (typeof fetch === 'undefined') {
    throw new ApiError(500, 'fetch not available (SSR)');
  }
  return fetch(`${API_BASE}${path}`, {
    ...options,
    credentials: 'include',
  });
}

async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await doFetch(path, options);

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    const detail = err.detail;
    let message: string;
    if (typeof detail === 'string') {
      message = detail;
    } else if (Array.isArray(detail)) {
      message = detail.map((item: any) => {
        if (typeof item === 'string') return item;
        if (item && typeof item === 'object') {
          const loc = item.loc ? item.loc.join('.') : '';
          const msg = item.msg || JSON.stringify(item);
          return loc ? `${loc}: ${msg}` : msg;
        }
        return JSON.stringify(item);
      }).join('; ');
    } else if (detail && typeof detail === 'object') {
      message = detail.message || detail.error || JSON.stringify(detail);
    } else {
      message = res.statusText || 'API error';
    }
    throw new ApiError(res.status, message);
  }
  return res.json();
}

export const api = {
  get: <T>(path: string) => fetchApi<T>(path),
  post: <T>(path: string, body?: unknown) => fetchApi<T>(path, { method: 'POST', headers: body ? { 'Content-Type': 'application/json' } : undefined, body: body ? JSON.stringify(body) : undefined }),
  put: <T>(path: string, body?: unknown) => fetchApi<T>(path, { method: 'PUT', headers: body ? { 'Content-Type': 'application/json' } : undefined, body: body ? JSON.stringify(body) : undefined }),
  patch: <T>(path: string, body?: unknown) => fetchApi<T>(path, { method: 'PATCH', headers: body ? { 'Content-Type': 'application/json' } : undefined, body: body ? JSON.stringify(body) : undefined }),
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
