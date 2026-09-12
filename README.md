# VECTORIX — Distributed Search & Retrieval Platform

A production-style distributed search and retrieval platform built with **FastAPI, Elasticsearch, Redis, PostgreSQL, and React**.

VECTORIX provides full-text search, relevance ranking, filtering, autocomplete, asynchronous indexing, result caching, observability, and failure-handling capabilities through a scalable service-oriented architecture.

---

## Architecture

```text
                         ┌─────────────────────┐
                         │   React Dashboard   │
                         │ React + TypeScript   │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │     FastAPI API     │
                         │   Async REST Layer  │
                         └──────┬────────┬─────┘
                                │        │
                       ┌────────┘        └─────────┐
                       ▼                           ▼
              ┌─────────────────┐         ┌─────────────────┐
              │      Redis      │         │   PostgreSQL    │
              │   Result Cache  │         │ Source of Truth │
              └─────────────────┘         └────────┬────────┘
                                                   │
                                                   ▼
                                          ┌─────────────────┐
                                          │ Async Indexing  │
                                          │     Worker      │
                                          └────────┬────────┘
                                                   │
                                                   ▼
                         ┌────────────────────────────────────┐
                         │       Elasticsearch Cluster        │
                         │                                    │
                         │ Node 1      Node 2      Node 3    │
                         │ 3 Primary Shards + 1 Replica      │
                         └────────────────────────────────────┘
```

PostgreSQL acts as the system of record, while Elasticsearch serves as the optimized search index. Asynchronous indexing decouples document writes from search-index updates.

---

## Technology Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, TypeScript, React Router, Vite |
| Backend | FastAPI, async SQLAlchemy 2.0, Pydantic v2 |
| Search | Elasticsearch 8.15, BM25, function scoring |
| Cache | Redis 7 |
| Database | PostgreSQL 16, Alembic |
| Worker | Python async indexing worker |
| Monitoring | Prometheus, structured JSON logging |
| Testing | pytest, pytest-asyncio, fakeredis, httpx, Playwright |
| Infrastructure | Docker, Docker Compose |

---

## Core Features

### Search & Retrieval

- Full-text search powered by Elasticsearch
- BM25 relevance ranking
- Field-level boosting across title, description, tags, and content
- Phrase-match boosting
- Fuzzy matching
- Popularity and freshness ranking signals
- Filtering by category, author, language, tags, and date range
- Sorting and pagination
- Search-result highlighting
- Autocomplete using edge-ngram analysis

### Distributed Elasticsearch

- 3-node Elasticsearch cluster
- 3 primary shards
- 1 replica per shard
- Health and readiness monitoring
- Elasticsearch-backed search with PostgreSQL as the source of truth

### Asynchronous Indexing

- PostgreSQL-backed indexing jobs
- Batch document indexing
- Parallel processing
- Exponential-backoff retries
- Backpressure controls
- Dead-letter handling
- Idempotent document indexing
- Incremental document updates
- Automatic reconciliation of documents missing from the search index

### Caching

- Redis-backed search-result caching
- Deterministic cache keys
- Cache invalidation on document changes
- Cache hit-rate metrics

### Reliability & Failure Handling

- Elasticsearch health monitoring
- Redis health monitoring
- PostgreSQL health monitoring
- Readiness checks
- Degraded-mode handling when Elasticsearch is unavailable
- PostgreSQL fallback for search when Elasticsearch is unavailable
- Recovery and reconciliation after Elasticsearch becomes available again
- Retry-safe indexing operations
- Structured error responses

### Observability

- Prometheus metrics
- Structured JSON logs
- Request-ID tracing
- API latency and throughput metrics
- Indexing-job statistics
- Search cache hit-rate monitoring

### React Dashboard

The frontend provides:

- Search interface
- Search-result visualization
- Autocomplete
- Analytics
- Indexing controls
- Document explorer
- System health
- Operational statistics

---

## Repository Structure

```text
.
├── backend/
│   ├── app/
│   │   ├── api/             # REST API routes
│   │   ├── core/            # Configuration and shared utilities
│   │   ├── embeddings/      # Embedding generation
│   │   ├── indexing/        # Async indexing pipeline
│   │   ├── models/          # Database models
│   │   ├── repositories/    # Data-access layer
│   │   ├── search/          # Elasticsearch and retrieval logic
│   │   └── services/        # Application services
│   └── tests/
│       ├── unit/
│       ├── integration/
│       └── api/
├── frontend/
│   ├── src/
│   └── e2e/
├── infrastructure/
│   ├── elasticsearch/
│   └── monitoring/
├── scripts/
│   ├── seed_data.py
│   ├── benchmark.py
│   ├── create_index.py
│   └── health_check.py
├── docs/
│   ├── architecture.md
│   ├── api.md
│   ├── indexing.md
│   ├── performance.md
│   └── troubleshooting.md
├── docker-compose.yml
├── docker-compose.dev.yml
└── README.md
```

---

## Local Setup

### Requirements

- Docker
- Docker Compose
- Git

All application services run inside containers.

### 1. Clone the repository

```bash
git clone https://github.com/rohittkr/vectorix-distributed-search.git
cd vectorix-distributed-search
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Adjust values in `.env` if required.

### 3. Start the platform

```bash
docker compose up --build -d
```

This starts the Elasticsearch cluster, PostgreSQL, Redis, FastAPI backend, indexing worker, React frontend, and Prometheus.

### Service Endpoints

| Service | URL |
|---|---|
| Frontend | http://localhost:5173 |
| FastAPI API | http://localhost:8000 |
| Swagger / OpenAPI | http://localhost:8000/docs |
| Prometheus | http://localhost:9090 |

---

## Database Migrations

```bash
docker compose exec backend alembic upgrade head
```

---

## Creating the Elasticsearch Index

```bash
docker compose exec backend python -m app.search.recreate_index
```

To recreate the index:

```bash
docker compose exec backend python -m app.search.recreate_index --recreate
```

---

## Generating Test Data

The project includes a configurable data generator.

Example:

```bash
docker compose exec backend python /app/scripts/seed_data.py --count 10000 --seed 42
```

For larger-scale testing:

```bash
docker compose exec backend python /app/scripts/seed_data.py --count 1000000 --seed 42
```

The generator inserts documents into PostgreSQL and queues an asynchronous indexing job for Elasticsearch.

> Large-scale runs depend on available CPU, RAM, disk capacity, and Elasticsearch resources. Benchmark results should be measured on the actual environment rather than assumed from the document count.

---

## Hybrid Retrieval

VECTORIX supports a hybrid retrieval architecture combining lexical and semantic retrieval:

```text
                    Search Query
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
       Lexical Retrieval      Vector Retrieval
          BM25                  kNN / Cosine
              │                     │
              └──────────┬──────────┘
                         ▼
                  Result Fusion
                         │
                         ▼
                  Final Results
```

The semantic retrieval pipeline uses dense document embeddings together with Elasticsearch vector search.

Hybrid retrieval combines lexical relevance with semantic similarity to improve retrieval when exact keyword matching is insufficient.

---

## Indexing Pipeline

```text
Document Write
      │
      ▼
 PostgreSQL
      │
      ▼
 Indexing Job
      │
      ▼
 Batch Processing
      │
      ├── Embedding Generation
      ├── Retry / Backoff
      ├── Backpressure
      └── Idempotency
      │
      ▼
 Elasticsearch
```

The asynchronous worker keeps document writes decoupled from Elasticsearch operations and supports retry-safe processing.

---

## Failure Recovery

VECTORIX treats PostgreSQL as the source of truth and Elasticsearch as a derived search index.

When Elasticsearch becomes unavailable:

```text
API
 │
 ├── Redis cache
 │
 ├── Elasticsearch
 │       X unavailable
 │
 └── PostgreSQL fallback
```

The API can enter a degraded operating mode rather than depending exclusively on Elasticsearch.

Once Elasticsearch recovers, the worker can reconcile documents that still require indexing.

Health status:

```bash
curl http://localhost:8000/api/v1/health/ready
```

---

## Health & Statistics

System statistics:

```bash
curl http://localhost:8000/api/v1/stats
```

Elasticsearch health:

```bash
curl http://localhost:8000/api/v1/health/elasticsearch
```

Readiness:

```bash
curl http://localhost:8000/api/v1/health/ready
```

Prometheus metrics:

```text
GET /api/v1/metrics
```

---

## Running Tests

Backend tests:

```bash
cd backend
python -m pytest tests/unit tests/integration tests/api -v
```

The test suite covers:

- Search query construction
- Ranking
- Cache behavior
- Schema validation
- Indexing lifecycle
- Retry and backoff behavior
- Failure recovery
- Concurrency behavior
- Document CRUD
- Search API behavior
- Hybrid retrieval logic

### End-to-End Tests

With the full Docker stack running:

```bash
cd frontend
npm install
npx playwright test
```

---

## Benchmarking

Start the stack:

```bash
docker compose up --build -d
```

Run:

```bash
python scripts/benchmark.py --requests 500 --concurrency 50
```

The benchmark reports:

- p50 latency
- p95 latency
- p99 latency
- throughput
- error rate
- cache hit rate

Performance results are environment-dependent and should be reported together with the hardware, dataset size, concurrency, and workload used for the benchmark.

---

## Test Results

The backend test suite currently contains **73 automated tests** covering unit, integration, and API behavior.

```text
73 tests passed

35 unit tests
23 integration tests
15 API tests
```

The project also includes Playwright end-to-end tests covering the primary user journey.

---

## Engineering Decisions

### PostgreSQL as Source of Truth

PostgreSQL stores the authoritative document state. Elasticsearch is treated as a derived search index.

This allows the system to recover from Elasticsearch failures without losing the underlying document data.

### Elasticsearch Sharding & Replication

The cluster uses 3 primary shards with 1 replica to distribute search and indexing workloads while providing redundancy.

### Separate Indexing Worker

Indexing is asynchronous so API requests are not blocked by potentially expensive Elasticsearch operations.

### Redis Caching

Frequently repeated search queries can be served from Redis, reducing repeated Elasticsearch work and improving response latency.

### Hybrid Retrieval

Lexical BM25 retrieval provides strong exact-term relevance, while vector retrieval adds semantic similarity. Combining the two improves robustness across different query types.

---

## Performance Notes

Performance depends on:

- Dataset size
- Elasticsearch shard distribution
- Query complexity
- Hybrid vs. lexical retrieval
- Cache state
- Request concurrency
- CPU and memory resources
- Docker resource limits

Run the included benchmark to obtain measurements for your environment rather than relying on fixed numbers.

---

## Project Status

VECTORIX is an engineering-focused distributed search platform demonstrating:

- Distributed Elasticsearch architecture
- Async backend services
- Search relevance engineering
- Hybrid retrieval
- Vector embeddings
- Redis caching
- PostgreSQL persistence
- Asynchronous indexing
- Retry and backpressure mechanisms
- Failure recovery
- Observability
- Automated testing
- React-based operational tooling

The repository is intended to demonstrate the design and implementation of a production-style search system while keeping performance claims tied to reproducible measurements.

---

## License

This project is for educational and portfolio purposes.
