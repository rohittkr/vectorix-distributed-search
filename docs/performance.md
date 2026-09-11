# Performance

## Honest disclosure

The numbers in this file are **not measured** -- the sandbox this
project was built in has no Docker daemon and no access to Docker
Hub/Elastic's registry (both return `403` on outbound requests), so the
Elasticsearch cluster, Redis, and Postgres described in
`docker-compose.yml` were never actually started or load-tested there.
The backend's *logic* was verified for real (73 automated tests, see
`docs/testing.md` if present, or the root README's Test Results
section) using SQLite/mocks/fakeredis as stand-ins -- but SQLite-backed
unit tests tell you nothing about Elasticsearch query latency at 1M
documents, and no number here should be treated as a real benchmark
until you've run `scripts/benchmark.py` yourself.

## How to get real numbers

```bash
docker compose up --build
python scripts/create_index.py
python scripts/seed_data.py --count 1000000 --seed 42
# wait for the worker to finish indexing -- check progress:
docker compose exec backend python scripts/health_check.py
curl http://localhost:8000/api/v1/stats

python scripts/benchmark.py --requests 500 --concurrency 50
```

`scripts/benchmark.py` reports real p50/p95/p99 latency, throughput,
error rate, and cache hit rate against whatever is actually running --
it has no fallback path that fabricates numbers if the backend is
unreachable; it prints a connection error and exits instead.

## Design-time performance decisions (reasoning, not measurements)

- **3 shards / 1 replica** on the `documents` index -- spreads indexing
  and query load across all 3 nodes; survives one node failure. At
  larger scale, shard count should track index size (rule of thumb:
  target 20-40GB per shard), not document count directly.
- **Bulk API with 500-doc batches** for indexing -- amortizes network
  round-trip overhead. Larger batches trade memory and per-batch
  failure blast-radius for throughput; 500 is a reasonable starting
  point to tune from once you have real numbers.
- **Redis cache, keyed on normalized request, versioned invalidation**
  -- turns repeat identical queries into O(1) Redis lookups instead of
  re-running BM25 scoring. Cache invalidation is O(1) (a version-counter
  bump), not an O(n) key scan, so index updates don't cause a latency
  spike from cache-clearing itself.
- **`field_value_factor` + gaussian decay for ranking**, not pure BM25
  -- popularity and freshness are blended in with modest weights (1.2
  and 0.8) so they nudge relevance rather than override text matching.
  The right weights are a product decision that should be tuned against
  a real relevance evaluation set (see `docs/architecture.md`), not
  guessed once and left alone.

## What to watch under load

- `search_duration_seconds` and `indexing_batch_duration_seconds`
  (Prometheus, via `/api/v1/metrics`) -- p95/p99 latency over time.
- `search_cache_hits_total` / `search_cache_misses_total` -- cache
  effectiveness; a low hit rate on a read-heavy workload suggests the
  TTL (`CACHE_TTL_SECONDS`) may be too short, or query traffic is too
  long-tail to benefit much from caching.
- Elasticsearch cluster health (`GET /api/v1/health/elasticsearch`) --
  watch for `yellow` (a replica shard unassigned, often transient) vs.
  `red` (a primary shard missing -- data loss risk, investigate
  immediately).
