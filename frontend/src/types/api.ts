export interface SearchFilters {
  category?: string | null;
  tags?: string[] | null;
  author?: string | null;
  language?: string | null;
  date_from?: string | null;
  date_to?: string | null;
}

export type SortField = "relevance" | "created_at" | "popularity";
export type SortOrder = "asc" | "desc";

export interface SearchRequest {
  query: string;
  filters?: SearchFilters;
  page?: number;
  page_size?: number;
  sort_by?: SortField;
  sort_order?: SortOrder;
  fuzzy?: boolean;
  highlight?: boolean;
}

export interface SearchResultItem {
  id: string;
  title: string;
  description?: string | null;
  category?: string | null;
  author?: string | null;
  tags: string[];
  url?: string | null;
  score: number;
  popularity: number;
  created_at?: string | null;
  highlight: Record<string, string[]>;
}

export interface SearchResponse {
  query: string;
  total: number;
  page: number;
  page_size: number;
  took_ms: number;
  cache_hit: boolean;
  results: SearchResultItem[];
}

export interface DocumentRead {
  id: string;
  title: string;
  content: string;
  description?: string | null;
  category?: string | null;
  author?: string | null;
  tags: string[];
  language: string;
  source?: string | null;
  url?: string | null;
  popularity: number;
  doc_metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  indexed_at?: string | null;
}

export interface IndexingJob {
  id: string;
  job_type: string;
  status: "pending" | "running" | "succeeded" | "failed" | "partially_failed";
  total_documents: number;
  processed_documents: number;
  failed_documents: number;
  retry_count: number;
  progress_pct: number;
  error_message?: string | null;
  created_at: string;
  started_at?: string | null;
  finished_at?: string | null;
}

export interface StatsResponse {
  total_documents: number;
  indexed_documents: number;
  pending_documents: number;
  failed_documents: number;
  active_jobs: number;
  elasticsearch_status: string;
  redis_status: string;
  postgres_status: string;
  cache_hit_rate: number;
}

export interface ApiError {
  error: {
    code: string;
    message: string;
    details?: unknown;
  };
  request_id: string;
}
