import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.database import create_all_tables, init_engine
from app.main import create_app

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def app():
    init_engine("sqlite+aiosqlite:///:memory:")
    await create_all_tables()
    return create_app()


@pytest_asyncio.fixture
async def client(app, fake_redis, fake_es):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


def _es_search_response(hits: list[dict], total: int | None = None) -> dict:
    return {
        "hits": {
            "total": {"value": total if total is not None else len(hits), "relation": "eq"},
            "hits": hits,
        }
    }


def _hit(doc_id: str, title: str, score: float = 1.0) -> dict:
    return {
        "_id": doc_id,
        "_score": score,
        "_source": {"id": doc_id, "title": title, "tags": [], "popularity": 0.0},
    }


async def test_search_post_returns_results_from_es(client, fake_es):
    fake_es.search.return_value = _es_search_response([_hit("1", "Distributed Systems")])
    resp = await client.post("/api/v1/search", json={"query": "distributed"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["results"][0]["title"] == "Distributed Systems"
    assert body["cache_hit"] is False


async def test_search_is_cached_on_second_identical_request(client, fake_es):
    fake_es.search.return_value = _es_search_response([_hit("1", "Cached Doc")])
    r1 = await client.post("/api/v1/search", json={"query": "cached"})
    assert r1.json()["cache_hit"] is False

    r2 = await client.post("/api/v1/search", json={"query": "cached"})
    assert r2.json()["cache_hit"] is True
    # ES should only have been hit once -- the second request was served
    # from cache.
    assert fake_es.search.call_count == 1


async def test_search_get_variant_matches_post(client, fake_es):
    fake_es.search.return_value = _es_search_response([_hit("1", "Query Param Doc")])
    resp = await client.get("/api/v1/search", params={"q": "test"})
    assert resp.status_code == 200
    assert resp.json()["results"][0]["title"] == "Query Param Doc"


async def test_search_returns_503_when_elasticsearch_unavailable(client, fake_es):
    from elasticsearch import ConnectionError as ESConnectionError

    fake_es.search.side_effect = ESConnectionError("connection refused")
    resp = await client.post("/api/v1/search", json={"query": "anything"})
    assert resp.status_code == 503
    assert resp.json()["error"]["code"] == "SEARCH_SERVICE_UNAVAILABLE"


async def test_invalid_page_size_rejected(client):
    resp = await client.post("/api/v1/search", json={"query": "x", "page_size": 9999})
    assert resp.status_code == 422


async def test_suggestions_endpoint(client, fake_es):
    fake_es.search.return_value = {
        "hits": {"hits": [{"_source": {"title": "Distributed Systems"}}, {"_source": {"title": "Distributed DBs"}}]}
    }
    resp = await client.get("/api/v1/suggestions", params={"q": "dist"})
    assert resp.status_code == 200
    assert "Distributed Systems" in resp.json()["suggestions"]


async def test_suggestions_degrade_gracefully_on_es_failure(client, fake_es):
    from elasticsearch import ConnectionError as ESConnectionError

    fake_es.search.side_effect = ESConnectionError("down")
    resp = await client.get("/api/v1/suggestions", params={"q": "dist"})
    assert resp.status_code == 200
    assert resp.json()["suggestions"] == []
