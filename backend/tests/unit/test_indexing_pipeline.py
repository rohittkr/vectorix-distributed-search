from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.indexing.pipeline import _to_bulk_action, index_batch
from app.models.document import Document


def _doc(doc_id: str) -> Document:
    return Document(
        id=doc_id,
        title=f"Title {doc_id}",
        content="content",
        tags=[],
        popularity=0.0,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def test_bulk_action_uses_index_op_and_document_id_for_idempotency():
    doc = _doc("abc-123")
    action = _to_bulk_action(doc, "documents")
    assert action["_op_type"] == "index"
    assert action["_id"] == "abc-123"
    assert action["_index"] == "documents"


@pytest.mark.asyncio
async def test_all_succeed_on_first_attempt():
    docs = [_doc("1"), _doc("2"), _doc("3")]
    with patch("app.indexing.pipeline.async_bulk", new=AsyncMock(return_value=(3, []))):
        result = await index_batch(client=object(), documents=docs, index_name="documents", max_retries=3, base_delay=0.01)
    assert sorted(result.succeeded) == ["1", "2", "3"]
    assert result.failed == []
    assert result.attempts == 1


@pytest.mark.asyncio
async def test_partial_failure_only_retries_failed_docs():
    docs = [_doc("1"), _doc("2")]
    call_log = []

    async def fake_bulk(client, actions, **kwargs):
        ids = [a["_id"] for a in actions]
        call_log.append(ids)
        if "2" in ids and len(call_log) == 1:
            # First call: doc 2 fails, doc 1 succeeds.
            return (1, [{"index": {"_id": "2", "error": "mapper_parsing_exception"}}])
        return (len(ids), [])

    with patch("app.indexing.pipeline.async_bulk", new=fake_bulk):
        result = await index_batch(client=object(), documents=docs, index_name="documents", max_retries=3, base_delay=0.01)

    assert "1" in result.succeeded
    assert "2" in result.succeeded  # succeeded on retry
    assert call_log[0] == ["1", "2"]
    assert call_log[1] == ["2"]  # only the failed doc was retried


@pytest.mark.asyncio
async def test_exhausting_retries_dead_letters_the_document():
    docs = [_doc("1")]

    async def always_fail(client, actions, **kwargs):
        return (0, [{"index": {"_id": "1", "error": "circuit_breaking_exception"}}])

    with patch("app.indexing.pipeline.async_bulk", new=always_fail):
        result = await index_batch(client=object(), documents=docs, index_name="documents", max_retries=2, base_delay=0.01)

    assert result.succeeded == []
    failed_ids = [f[0] for f in result.failed]
    assert failed_ids.count("1") >= 1
    assert result.attempts == 2


@pytest.mark.asyncio
async def test_connection_error_triggers_backoff_and_retry():
    from elastic_transport import ConnectionError as TransportConnectionError

    docs = [_doc("1")]
    call_count = {"n": 0}

    async def flaky_bulk(client, actions, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise TransportConnectionError("connection refused")
        return (1, [])

    with patch("app.indexing.pipeline.async_bulk", new=flaky_bulk):
        result = await index_batch(client=object(), documents=docs, index_name="documents", max_retries=3, base_delay=0.01)

    assert result.succeeded == ["1"]
    assert call_count["n"] == 2
