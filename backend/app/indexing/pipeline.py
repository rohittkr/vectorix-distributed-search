r"""
Async indexing pipeline.

Flow:
  Postgres (unindexed rows) -> batch -> Elasticsearch Bulk API -> verify
                                    \-> retry w/ exponential backoff
                                    \-> dead-letter to indexing_failures

Idempotency: documents are indexed with `_id = document.id`, so re-running
a batch (e.g. after a retry) is safe -- it's an upsert, never a duplicate.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from elastic_transport import ConnectionError as TransportConnectionError
from elasticsearch import AsyncElasticsearch
from elasticsearch.helpers import async_bulk

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.document import Document

logger = get_logger(__name__)


@dataclass
class BatchResult:
    succeeded: list[str] = field(default_factory=list)
    failed: list[tuple[str, str]] = field(default_factory=list)  # (document_id, reason)
    attempts: int = 0


def _to_bulk_action(doc: Document, index_name: str) -> dict:
    return {
        "_op_type": "index",  # index == upsert-by-id, satisfies idempotency
        "_index": index_name,
        "_id": doc.id,
        "_source": doc.to_search_document(),
    }


async def index_batch(
    client: AsyncElasticsearch,
    documents: list[Document],
    index_name: str | None = None,
    max_retries: int | None = None,
    base_delay: float | None = None,
) -> BatchResult:
    """
    Bulk-index a batch of documents with exponential-backoff retry.

    Only documents that failed in a given attempt are retried in the next
    attempt -- successes are never re-sent.
    """
    settings = get_settings()
    index_name = index_name or settings.ELASTICSEARCH_INDEX
    max_retries = max_retries if max_retries is not None else settings.INDEXING_MAX_RETRIES
    base_delay = base_delay if base_delay is not None else settings.INDEXING_RETRY_BASE_DELAY_SECONDS

    result = BatchResult()
    remaining = {doc.id: doc for doc in documents}

    for attempt in range(1, max_retries + 1):
        result.attempts = attempt
        if not remaining:
            break

        actions = [_to_bulk_action(doc, index_name) for doc in remaining.values()]
        try:
            success_count, errors = await async_bulk(
                client, actions, raise_on_error=False, stats_only=False
            )
        except TransportConnectionError as exc:
            logger.warning("ES unavailable on attempt %s: %s", attempt, exc)
            await asyncio.sleep(base_delay * (2 ** (attempt - 1)))
            continue

        # async_bulk with stats_only=False returns (success_count, error_items)
        failed_ids: set[str] = set()
        for err_item in errors:
            action_type = next(iter(err_item))
            doc_id = err_item[action_type].get("_id")
            reason = err_item[action_type].get("error", "unknown error")
            if doc_id:
                failed_ids.add(doc_id)
                result.failed.append((doc_id, str(reason)))

        succeeded_ids = [doc_id for doc_id in remaining if doc_id not in failed_ids]
        result.succeeded.extend(succeeded_ids)

        if not failed_ids:
            remaining = {}
            break

        # Only retry the documents that failed; drop the rest.
        remaining = {doc_id: remaining[doc_id] for doc_id in failed_ids}
        if attempt < max_retries:
            await asyncio.sleep(base_delay * (2 ** (attempt - 1)))

    # Whatever's still in `remaining` after the last attempt is a permanent
    # failure for this run -> dead-letter.
    for doc_id in remaining:
        if doc_id not in [f[0] for f in result.failed]:
            result.failed.append((doc_id, "exhausted retries"))

    return result


async def verify_indexed(client: AsyncElasticsearch, index_name: str, document_ids: list[str]) -> list[str]:
    """Return the subset of document_ids that are confirmed present in ES."""
    if not document_ids:
        return []
    resp = await client.mget(index=index_name, body={"ids": document_ids})
    return [doc["_id"] for doc in resp["docs"] if doc.get("found")]
