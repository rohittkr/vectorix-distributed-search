# Architecture

## System overview

```
                         ┌────────────┐
                         │  Frontend  │  React + TypeScript, served by nginx
                         └─────┬──────┘
                               │ REST (JSON)
                         ┌─────▼──────┐
                         │  FastAPI   │  async request handlers
                         └──┬───┬─────┘
                            │   │
              ┌─────────────┘   └───────────────┐
              │                                  │
        ┌─────▼─────┐                     ┌──────▼──────┐
        │   Redis   │  search-result      │ PostgreSQL   │  system of record:
        │   cache   │  cache              │              │  documents, jobs,
        └───────────┘                     └──────┬───────┘  analytics
                                                  │
                                          ┌───────▼────────┐
                                          │  Async Worker  │  polls indexing_jobs
                                          └───────┬────────┘
                                                  │ bulk index
                                    ┌─────────────▼─────────────┐
                                    │  Elasticsearch (3 nodes)   │
                                    │  BM25 + function_score     │
                                    └────────────────────────────┘
```

## Why each component exists

**FastAPI (async)** -- I/O-bound workload (network calls to ES/Redis/Postgres
dominate CPU time), so async request handlers let one process serve many
concurrent requests without a thread per connection. Sync frameworks would
need far more worker processes to hit the same concurrency.

**PostgreSQL as system of record, Elasticsearch as a derived index** --
Elasticsearch is excellent at full-text search and terrible as a
transactional store (no ACID transactions, eventually-consistent
replication, mapping changes require reindexing). Postgres holds the
durable, authoritative document data; Elasticsearch holds a
purpose-built, rebuildable search index derived from it. If the ES
cluster were lost entirely, `POST /api/v1/index/rebuild` regenerates it
from Postgres with zero data loss.

**Redis cache in front of Elasticsearch** -- Popular queries (trending
searches, common autocomplete prefixes) would otherwise re-execute the
same BM25 scoring work repeatedly. A cache keyed on the *normalized*
request (see `docs/api.md`) turns repeat traffic into O(1) lookups and
takes load off the ES cluster. Failure of the cache degrades search
latency, never correctness -- a cache miss or Redis outage falls through
to Elasticsearch transparently (see `app/services/search_service.py`).

**Separate worker process for indexing** -- Bulk indexing is
CPU/network-heavy and bursty (a rebuild of 1M documents can run for
minutes). Running it inside the API process would compete with search
requests for the event loop and DB connection pool. A dedicated worker
container means indexing load never causes search latency spikes.

**3-node Elasticsearch cluster with 3 shards / 1 replica** -- Shards
parallelize both indexing and search across nodes; replicas provide
availability if one node fails. Three nodes is the minimum useful
cluster size for demonstrating real distributed behavior (quorum,
shard rebalancing, node-failure tolerance) without requiring
production-scale hardware -- see `infrastructure/elasticsearch/README.md`
for the exact resource tradeoffs made for a laptop-sized default.

## Request flow: search

```
Client
  │ POST /api/v1/search {query, filters, page, sort}
  ▼
FastAPI handler (app/api/v1/search.py)
  │
  ▼
SearchService.search (app/services/search_service.py)
  │
  ├─ 1. Normalize request -> deterministic cache key (app/cache/cache_service.py)
  │
  ├─ 2. Redis GET cache_key
  │       │
  │       ├─ HIT  -> return cached SearchResponse (cache_hit=true)
  │       │
  │       └─ MISS │
  ▼               ▼
  build_search_body (app/search/queries.py)
      -> multi_match (title^4, description^2, tags^2, content)
      -> function_score (popularity + freshness boost)
      -> filters (category/author/language/tags/date range)
      -> highlighting
  │
  ▼
Elasticsearch _search
  │
  ▼
hits_to_results (app/services/ranking.py) -> SearchResultItem[]
  │
  ├─ Redis SET cache_key (TTL from CACHE_TTL_SECONDS)
  ├─ Log to search_queries table (analytics, best-effort)
  ▼
SearchResponse -> client
```

## Request flow: indexing

```
POST /api/v1/documents/bulk
  │
  ▼
DocumentRepository.bulk_create -> Postgres INSERT (indexed_at = NULL)
  │
  ▼
IndexingService.create_job(BULK_INDEX) -> indexing_jobs row (status=pending)
  │
  ▼ (async, picked up by the worker container)
IndexingService.run_indexing_job
  │
  ├─ loop: DocumentRepository.get_unindexed_batch(500, exclude=permanently_failed)
  │
  ▼
index_batch (app/indexing/pipeline.py)
  │
  ├─ Elasticsearch Bulk API (_op_type=index, _id=document.id -> idempotent upsert)
  │
  ├─ on partial failure: retry only the failed subset, exponential backoff
  ├─ on exhausted retries: dead-letter to indexing_failures, exclude from
  │                        further fetches in this run (prevents infinite loop)
  │
  ▼
mark_indexed(succeeded_ids) -> Postgres UPDATE indexed_at = now()
  │
  ▼
cache_service.invalidate_all() -- bumps a version counter so every
                                   previously-cached search result is
                                   instantly orphaned (O(1), no key scan)
```

## Failure handling summary

| Failure                          | Behavior                                                        |
|-----------------------------------|-------------------------------------------------------------------|
| Redis unavailable                 | Cache reads/writes fail silently; search still works, uncached.  |
| Elasticsearch unavailable         | Search returns `503 SEARCH_SERVICE_UNAVAILABLE` (structured JSON).|
| Elasticsearch node failure        | Cluster stays available if replicas/shards allow (1 replica = 1 node can fail). |
| Postgres unavailable               | All write paths fail with a 500; read-through cache still serves cached search results. |
| Bulk indexing partial failure     | Only failed documents retry (bounded by `INDEXING_MAX_RETRIES`); permanent failures are dead-lettered to `indexing_failures` and excluded from further attempts in that job run. |
| Duplicate indexing job             | Rejected with `409 DUPLICATE_INDEXING_JOB` when the same `idempotency_key` is already pending/running. |
| Worker restart                     | In-flight job rows remain `status=running`; on restart the worker's polling loop picks up new `pending` jobs (a crashed `running` job requires manual re-queue -- see `docs/troubleshooting.md`). |

## Engineering tradeoffs

See `docs/performance.md` for the tradeoffs behind shard count, cache
TTL, and batch size specifically, and `docs/troubleshooting.md` for
what to check when something's broken.
