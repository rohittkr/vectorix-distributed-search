# Distributed Search Engine

A search engine over 1M+ documents: FastAPI + Elasticsearch (BM25) +
Redis caching + PostgreSQL + an async indexing pipeline, with a React
dashboard for search, analytics, indexing control, document management,
and system health.

> **Honest disclosure up front**: this codebase was written in a sandbox
> with no Docker daemon and no network access to Docker Hub or Elastic's
> registry. Every line of backend logic was written for real and
> exercised by 73 real, passing automated tests (SQLite standing in for
> Postgres, mocks/fakeredis standing in for Elasticsearch/Redis) -- but
> the full stack itself (`docker compose up`) has **not** been started
> or load-tested end-to-end. Treat this as a complete, carefully-tested
> codebase that needs its first real run on your machine, not as a
> deployed, benchmarked system. See "Known limitations" below for the
> full list of what that does and doesn't mean.

## Architecture

```
Frontend (React/TS) -> FastAPI -> Redis (cache) -> Elasticsearch (BM25, 3 nodes)
                              \-> PostgreSQL (system of record) -> Worker -> Elasticsearch
```

Full diagrams and request-flow walkthroughs: [`docs/architecture.md`](docs/architecture.md).

## Technology stack

| Layer | Choice |
|---|---|
| Frontend | React 18, TypeScript, React Router, Vite |
| Backend | FastAPI, async SQLAlchemy 2.0, Pydantic v2 |
| Search | Elasticsearch 8.15 (3-node cluster), BM25 + function_score |
| Cache | Redis 7 |
| Database | PostgreSQL 16, Alembic migrations |
| Worker | Standalone Python async process (own container) |
| Monitoring | `prometheus-client`, structured JSON logs |
| Testing | pytest, pytest-asyncio, fakeredis, httpx, Playwright (E2E) |

## Features

- Full-text search: BM25 relevance, field boosting (title/description/tags/content),
  phrase-match boosting, fuzzy matching, popularity + freshness ranking boosts
- Filtering (category, author, language, tags, date range), sorting, pagination, highlighting
- Autocomplete via an edge-ngram analyzer
- Redis-backed result caching with deterministic keys and O(1) invalidation
- Async bulk indexing with batching, exponential-backoff retry, and dead-lettering
- Idempotent indexing jobs (safe to retry, duplicate-protected via idempotency keys)
- Structured error responses, request-ID tracing, rate limiting
- Prometheus metrics; JSON structured logs
- React dashboard: Search, Analytics, Indexing control, Document Explorer, System Health

## Repository structure

```
backend/          FastAPI app, tests, Alembic migrations
frontend/         React + TypeScript SPA
infrastructure/   Elasticsearch/Postgres/Redis/Prometheus config
scripts/          seed_data.py, benchmark.py, create_index.py, health_check.py
docs/             architecture, API, indexing, performance, troubleshooting
docker-compose.yml / docker-compose.dev.yml
```

## Local setup

**Requirements**: Docker + Docker Compose. That's it -- everything else
runs in containers.

```bash
cp .env.example .env
docker compose up --build
```

This starts: 3-node Elasticsearch cluster, PostgreSQL, Redis, the
FastAPI backend, the indexing worker, the React frontend, and
Prometheus.

- Frontend: http://localhost:5173
- API docs: http://localhost:8000/docs
- Prometheus: http://localhost:9090

For hot-reload during development:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

## Running migrations

```bash
docker compose exec backend alembic upgrade head
# or: make migrate
```

## Generating 1M documents

```bash
python scripts/create_index.py
docker compose exec backend python scripts/seed_data.py --count 1000000 --seed 42
```

Streams inserts in batches (flat memory usage regardless of `--count`),
reports live throughput, and automatically queues an indexing job when
done -- the worker picks it up within a couple of seconds. Full details:
[`docs/indexing.md`](docs/indexing.md).

## Running tests

Everything below runs without Docker or any external service --
Postgres is stood in for by SQLite, Elasticsearch/Redis by
mocks/fakeredis:

```bash
cd backend
pip install -r requirements.txt
python -m pytest tests/unit tests/integration tests/api -v
```

End-to-end tests need the full stack running:

```bash
docker compose up --build -d
cd frontend && npm install && npx playwright test
```

## Running benchmarks

```bash
docker compose up --build -d
python scripts/benchmark.py --requests 500 --concurrency 50
```

Reports real p50/p95/p99 latency, throughput, error rate, and cache hit
rate against whatever's actually running -- see
[`docs/performance.md`](docs/performance.md) for why no numbers are
published in this README (they'd be fabricated, since this environment
couldn't run the stack).

## Failure recovery

Redis, Elasticsearch, and Postgres outages are all handled without
crashing the API -- see the failure-handling table in
[`docs/architecture.md`](docs/architecture.md#failure-handling-summary).
This is backed by real tests in
`backend/tests/integration/test_failure_recovery.py` (simulated outages,
not mocked-away assumptions).

## API documentation

Interactive: http://localhost:8000/docs (once running). Written summary:
[`docs/api.md`](docs/api.md).

## Monitoring

Prometheus metrics at `GET /api/v1/metrics`; scrape config in
`infrastructure/monitoring/prometheus.yml`. Structured JSON logs on
stdout, one line per event, each tagged with a `request_id` that also
appears in the `X-Request-ID` response header and in every API error
body -- quote it when reporting a bug.

## Engineering decisions

The "why" behind Postgres-as-source-of-truth vs. Elasticsearch-as-index,
the 3-shard/1-replica choice, the separate worker process, and the
cache invalidation strategy are all written up in
[`docs/architecture.md`](docs/architecture.md#why-each-component-exists).

## Test results

Real, measured, run in this environment (SQLite/mocks standing in for
Postgres/ES/Redis -- see disclosure above):

```
73 passed in ~2s
  - 35 unit tests        (query builder, cache keys, schema validation,
                          ranking, indexing pipeline retry/backoff)
  - 23 integration tests (repository, indexing service lifecycle,
                          failure recovery, concurrency)
  - 15 API tests         (document CRUD, search incl. real cache-hit
                          verification and ES-down -> 503 path)
```
Backend lints clean (`ruff check app tests` -- 0 errors after 4 autofixes
during development). Frontend builds clean (`tsc -b && vite build`,
0 errors) and lints clean (`eslint src`, 0 errors/warnings). Two real
bugs were found and fixed by this test suite during development -- an
infinite retry loop on permanently-failing documents, and a cache
invalidation-version off-by-one -- both documented in
`docs/troubleshooting.md` and in the relevant test files.

Playwright E2E tests are written (`frontend/e2e/full-user-journey.spec.ts`,
covering the full 10-step flow from the spec) but **not run** -- they
require the full Docker stack, which this environment cannot start.

## Known limitations

Being direct about what could and couldn't be validated here:

- **The full Docker stack has never been started.** No 3-node ES
  cluster, no Redis, no Postgres container has actually run. Every
  Elasticsearch query DSL body, mapping, and cache interaction was
  verified via unit/integration tests against mocks and SQLite, which
  catches logic bugs (and did -- twice) but cannot catch: ES mapping
  rejections, actual cluster formation issues, Docker networking
  problems, or resource-limit misconfigurations.
- **No performance numbers are real.** See `docs/performance.md`.
  Run `scripts/benchmark.py` yourself for real p50/p95/p99 figures.
- **1M-document generation is untested at scale.** The generator logic
  was smoke-tested for correctness (3 rows, deterministic seed) but
  never run to completion at 1M rows against a real Postgres instance.
- **E2E tests are written but unexecuted** -- see above.
- **No job-lease/timeout mechanism.** A worker that crashes mid-job
  leaves that job stuck in `status=running` forever; see
  `docs/troubleshooting.md` for the manual recovery step. A production
  system should add a lease timestamp and reclaim logic.
- **mypy reports a handful of typing-only warnings** against the
  Elasticsearch client's loose third-party types (e.g. `mget` response
  shape) -- not runtime bugs, but not cleaned up either.
- **Authentication/authorization is out of scope**, per the original
  spec ("do not introduce unnecessary authentication complexity unless
  required") -- there is no login, no per-user permissions. Every
  endpoint is open once you can reach the API.
