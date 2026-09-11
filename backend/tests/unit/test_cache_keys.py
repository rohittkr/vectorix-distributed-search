import pytest

from app.cache import cache_service
from app.schemas.search import SearchFilters, SearchRequest


@pytest.mark.asyncio
async def test_identical_requests_produce_identical_keys(fake_redis):
    r1 = SearchRequest(query="Python", filters=SearchFilters(category="tech"))
    r2 = SearchRequest(query="python", filters=SearchFilters(category="tech"))  # different case
    k1 = await cache_service.build_cache_key(r1)
    k2 = await cache_service.build_cache_key(r2)
    assert k1 == k2


@pytest.mark.asyncio
async def test_tag_order_does_not_affect_key(fake_redis):
    r1 = SearchRequest(query="x", filters=SearchFilters(tags=["ml", "ai"]))
    r2 = SearchRequest(query="x", filters=SearchFilters(tags=["ai", "ml"]))
    assert await cache_service.build_cache_key(r1) == await cache_service.build_cache_key(r2)


@pytest.mark.asyncio
async def test_different_page_produces_different_key(fake_redis):
    r1 = SearchRequest(query="x", page=1)
    r2 = SearchRequest(query="x", page=2)
    assert await cache_service.build_cache_key(r1) != await cache_service.build_cache_key(r2)


@pytest.mark.asyncio
async def test_different_filters_produce_different_keys(fake_redis):
    r1 = SearchRequest(query="x", filters=SearchFilters(category="tech"))
    r2 = SearchRequest(query="x", filters=SearchFilters(category="sports"))
    assert await cache_service.build_cache_key(r1) != await cache_service.build_cache_key(r2)


@pytest.mark.asyncio
async def test_invalidate_all_changes_subsequent_keys(fake_redis):
    r = SearchRequest(query="x")
    k1 = await cache_service.build_cache_key(r)
    await cache_service.invalidate_all()
    k2 = await cache_service.build_cache_key(r)
    assert k1 != k2


@pytest.mark.asyncio
async def test_cache_set_and_get_roundtrip(fake_redis):
    key = "search:v1:abc"
    payload = {"query": "x", "total": 1, "page": 1, "page_size": 20, "results": []}
    await cache_service.set_cached_result(key, payload)
    result = await cache_service.get_cached_result(key)
    assert result == payload


@pytest.mark.asyncio
async def test_cache_miss_returns_none_and_increments_miss_counter(fake_redis):
    result = await cache_service.get_cached_result("search:v1:doesnotexist")
    assert result is None
    stats = await cache_service.get_stats()
    assert stats["misses"] >= 1


@pytest.mark.asyncio
async def test_hit_rate_calculation(fake_redis):
    await cache_service.set_cached_result("k1", {"a": 1})
    await cache_service.get_cached_result("k1")  # hit
    await cache_service.get_cached_result("k2")  # miss
    stats = await cache_service.get_stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 1
    assert stats["hit_rate"] == 0.5
