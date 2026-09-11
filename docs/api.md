# API Documentation

Full interactive docs (OpenAPI/Swagger) are always available at
`http://localhost:8000/docs` once the backend is running, and the raw
schema at `/openapi.json`. This file summarizes the endpoints and the
conventions shared across all of them.

## Conventions

- **Base path**: `/api/v1`
- **Errors**: every non-2xx response has the shape
  ```json
  {
    "error": { "code": "DOCUMENT_NOT_FOUND", "message": "..." },
    "request_id": "..."
  }
  ```
  `request_id` matches the `X-Request-ID` response header, and is also
  attached to that request's server-side structured logs -- quote it
  when reporting a bug.
- **Pagination**: `page` (1-indexed), `page_size` (max 100).
- **Idempotency**: destructive/duplicable operations (`/index/rebuild`,
  `/index/reindex`) accept an optional `idempotency_key`; a second call
  with the same key while the first is still pending/running returns
  `409 DUPLICATE_INDEXING_JOB`.

## Health

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Basic liveness for dashboards |
| GET | `/health/live` | Process is up (no dependency checks) |
| GET | `/health/ready` | Checks Postgres + Redis + Elasticsearch; used by Compose healthchecks |
| GET | `/health/elasticsearch` | Raw ES cluster health |

## Documents

| Method | Path | Purpose |
|---|---|---|
| POST | `/documents` | Create a single document |
| POST | `/documents/bulk` | Create up to 10,000 documents; returns an indexing `job_id` |
| GET | `/documents/{id}` | Fetch a document |
| PUT | `/documents/{id}` | Partial update |
| DELETE | `/documents/{id}` | Delete |

Document fields: `title`, `content`, `description`, `category`, `author`,
`tags[]`, `language`, `source`, `url`, `popularity`, `doc_metadata`.
`tags` are normalized (lowercased, deduped, sorted) on write.

## Search

| Method | Path | Purpose |
|---|---|---|
| POST | `/search` | Full search request body (filters, sort, pagination) |
| GET | `/search` | Same, as query params -- shareable/bookmarkable URLs |
| GET | `/suggestions?q=` | Autocomplete suggestions from indexed titles |

Example request:

```json
POST /api/v1/search
{
  "query": "distributed systems",
  "filters": { "category": "technology", "tags": ["python"] },
  "page": 1,
  "page_size": 20,
  "sort_by": "relevance",
  "fuzzy": true,
  "highlight": true
}
```

Example response:

```json
{
  "query": "distributed systems",
  "total": 1234,
  "page": 1,
  "page_size": 20,
  "took_ms": 18.4,
  "cache_hit": false,
  "results": [
    {
      "id": "...",
      "title": "...",
      "score": 8.21,
      "highlight": { "content": ["...<mark>distributed</mark> systems..."] }
    }
  ]
}
```

Ranking is BM25 relevance combined with a popularity boost
(`log1p(popularity)`) and a freshness boost (gaussian decay, 180-day
half-life) -- see `app/search/queries.py` for the exact `function_score`
definition and `docs/architecture.md` for the reasoning.

## Indexing jobs

| Method | Path | Purpose |
|---|---|---|
| POST | `/index/rebuild` | Queue re-indexing of every document |
| POST | `/index/reindex` | Queue indexing of only unindexed documents |
| GET | `/jobs` | List recent jobs |
| GET | `/jobs/{id}` | Job detail incl. progress, failures, retry count |

## Stats & metrics

| Method | Path | Purpose |
|---|---|---|
| GET | `/stats` | Document/job counts, cache hit rate, dependency status |
| GET | `/metrics` | Prometheus text-format metrics |
