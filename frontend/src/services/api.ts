import type {
  ApiError,
  DocumentRead,
  IndexingJob,
  SearchRequest,
  SearchResponse,
  StatsResponse,
} from "../types/api";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

export class ApiRequestError extends Error {
  code: string;
  requestId: string;
  status: number;

  constructor(status: number, body: ApiError) {
    super(body.error.message);
    this.code = body.error.code;
    this.requestId = body.request_id;
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });

  if (!resp.ok) {
    let body: ApiError;
    try {
      body = await resp.json();
    } catch {
      throw new Error(`Request failed with status ${resp.status}`);
    }
    throw new ApiRequestError(resp.status, body);
  }

  if (resp.status === 204) {
    return undefined as T;
  }
  return resp.json() as Promise<T>;
}

export const api = {
  search(payload: SearchRequest, signal?: AbortSignal): Promise<SearchResponse> {
    return request<SearchResponse>("/search", {
      method: "POST",
      body: JSON.stringify(payload),
      signal,
    });
  },

  suggestions(query: string, signal?: AbortSignal): Promise<{ query: string; suggestions: string[] }> {
    const params = new URLSearchParams({ q: query });
    return request(`/suggestions?${params.toString()}`, { signal });
  },

  getDocument(id: string): Promise<DocumentRead> {
    return request<DocumentRead>(`/documents/${id}`);
  },

  createDocument(payload: Partial<DocumentRead>): Promise<DocumentRead> {
    return request<DocumentRead>("/documents", { method: "POST", body: JSON.stringify(payload) });
  },

  updateDocument(id: string, payload: Partial<DocumentRead>): Promise<DocumentRead> {
    return request<DocumentRead>(`/documents/${id}`, { method: "PUT", body: JSON.stringify(payload) });
  },

  deleteDocument(id: string): Promise<void> {
    return request<void>(`/documents/${id}`, { method: "DELETE" });
  },

  stats(): Promise<StatsResponse> {
    return request<StatsResponse>("/stats");
  },

  listJobs(): Promise<IndexingJob[]> {
    return request<IndexingJob[]>("/jobs");
  },

  getJob(id: string): Promise<IndexingJob> {
    return request<IndexingJob>(`/jobs/${id}`);
  },

  rebuildIndex(idempotencyKey?: string): Promise<IndexingJob> {
    return request<IndexingJob>("/index/rebuild", {
      method: "POST",
      body: JSON.stringify({ idempotency_key: idempotencyKey ?? null }),
    });
  },

  reindex(idempotencyKey?: string): Promise<IndexingJob> {
    return request<IndexingJob>("/index/reindex", {
      method: "POST",
      body: JSON.stringify({ idempotency_key: idempotencyKey ?? null }),
    });
  },

  health(): Promise<{ status: string; checks: Record<string, string> }> {
    return request("/health/ready");
  },
};
