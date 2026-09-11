"""
Failure-recovery tests.

These simulate each dependency being unavailable and assert the system
degrades gracefully rather than crashing -- per docs/architecture.md's
failure-handling contract.
"""

import pytest
from elasticsearch import ConnectionError as ESConnectionError

from app.cache import cache_service
from app.cache.redis_client import ping as redis_ping
from app.schemas.search import SearchRequest
from app.services.search_service import SearchService

pytestmark = pytest.mark.asyncio


async def test_search_works_when_redis_is_down(fake_es):
    """
    If Redis is unreachable, cache reads/writes must fail *silently* and
    search must still succeed by going straight to Elasticsearch.
    """
    from app.cache import redis_client

    class DeadRedis:
        async def get(self, *a, **k):
            raise ConnectionError("redis down")

        async def set(self, *a, **k):
            raise ConnectionError("redis down")

        async def incr(self, *a, **k):
            raise ConnectionError("redis down")

    redis_client.set_client(DeadRedis())

    fake_es.search.return_value = {
        "hits": {"total": {"value": 1}, "hits": [{"_id": "1", "_score": 1.0, "_source": {"id": "1", "title": "X"}}]}
    }

    service = SearchService()
    response = await service.search(SearchRequest(query="x"))
    assert response.total == 1
    assert response.cache_hit is False  # cache was unreachable, not consulted successfully


async def test_redis_ping_returns_false_when_unreachable():
    from app.cache import redis_client

    class DeadRedis:
        async def ping(self):
            raise ConnectionError("down")

    redis_client.set_client(DeadRedis())
    assert await redis_ping() is False


async def test_search_raises_structured_error_when_elasticsearch_down(fake_es, fake_redis):
    from app.core.exceptions import SearchServiceUnavailableError

    fake_es.search.side_effect = ESConnectionError("es down")
    service = SearchService()
    with pytest.raises(SearchServiceUnavailableError):
        await service.search(SearchRequest(query="anything"))


async def test_cache_write_failure_does_not_raise(fake_redis, monkeypatch):
    """A broken cache write must never bubble up and break the caller."""

    async def broken_set(*a, **k):
        raise ConnectionError("write failed")

    monkeypatch.setattr(fake_redis, "set", broken_set)
    # Should not raise.
    await cache_service.set_cached_result("some-key", {"a": 1})


async def test_indexing_pipeline_survives_transient_es_outage():
    """
    A transient connection error during bulk indexing should be retried,
    not treated as a permanent per-document failure.
    """
    from datetime import datetime, timezone
    from unittest.mock import patch

    from elastic_transport import ConnectionError as TransportConnectionError

    from app.indexing.pipeline import index_batch
    from app.models.document import Document

    doc = Document(
        id="1", title="T", content="C", tags=[], popularity=0.0,
        created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc),
    )

    calls = {"n": 0}

    async def flaky(client, actions, **kwargs):
        calls["n"] += 1
        if calls["n"] < 3:
            raise TransportConnectionError("node unreachable")
        return (1, [])

    with patch("app.indexing.pipeline.async_bulk", new=flaky):
        result = await index_batch(client=object(), documents=[doc], max_retries=5, base_delay=0.01)

    assert result.succeeded == ["1"]
    assert calls["n"] == 3  # two failures, then success -- pipeline recovered
