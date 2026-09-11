# Indexing Pipeline

## Overview

Documents are never indexed into Elasticsearch synchronously inside an
API request. The flow is always:

```
API write -> Postgres (indexed_at = NULL) -> indexing_jobs row -> worker picks it up
```

The worker (`app/workers/indexer_worker.py`) is a separate container
polling for `pending` jobs every 2 seconds, running up to
`INDEXING_MAX_CONCURRENCY` jobs at once (default 4).

## Batching

Documents are fetched and indexed in batches of `INDEXING_BATCH_SIZE`
(default 500), using the Elasticsearch **Bulk API** rather than one
request per document -- at 1M+ documents, per-document requests would
be dominated by network round-trip overhead rather than actual
indexing work.

## Idempotency

Every document is indexed with `_id = document.id` and `_op_type =
index` (an upsert, not a create). Re-running the same batch -- whether
due to a retry, a worker restart, or a manual re-trigger -- can never
create a duplicate document in the index.

## Retries and dead-lettering

`app/indexing/pipeline.py::index_batch` retries only the documents that
actually failed in a given attempt (not the whole batch), with
exponential backoff (`base_delay * 2^attempt`, default base 0.5s) up to
`INDEXING_MAX_RETRIES` (default 5) attempts.

A document that still fails after exhausting retries is recorded in the
`indexing_failures` table with its error reason and attempt count, and
is excluded from further fetches *within that job run* -- without this
exclusion, a permanently-failing document (e.g. a mapping conflict)
would be re-fetched forever, since it never gets `indexed_at` set. This
was caught by `tests/integration/test_indexing_service.py` during
development (see the test's docstring) and is exactly the kind of bug
this batching design has to guard against at scale.

## Job statuses

| Status | Meaning |
|---|---|
| `pending` | Queued, not yet picked up by a worker |
| `running` | A worker is actively processing it |
| `succeeded` | Every document indexed successfully |
| `partially_failed` | Some documents succeeded, some were dead-lettered |
| `failed` | No documents were successfully indexed |

## Generating a large dataset

```bash
# Small dev dataset
python scripts/seed_data.py --count 10000

# Full 1M+ dataset, deterministic
python scripts/seed_data.py --count 1000000 --seed 42
```

The generator streams rows into Postgres in configurable batches
(`--batch-size`, default 2000) so memory stays flat regardless of
`--count` -- it never builds the full dataset in memory before
inserting. It reports live throughput (docs/sec) as it runs. Once
seeding finishes, the script automatically queues a `reindex` job;
the worker container's poll loop picks it up within a couple of
seconds and starts indexing into Elasticsearch.
