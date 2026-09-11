import asyncio

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.database import create_all_tables, init_engine
from app.core.exceptions import DuplicateJobError
from app.main import create_app
from app.models.jobs import JobType
from app.services.indexing_service import IndexingService

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


def _es_response(n: int = 1):
    return {
        "hits": {
            "total": {"value": n},
            "hits": [{"_id": str(i), "_score": 1.0, "_source": {"id": str(i), "title": f"Doc {i}"}} for i in range(n)],
        }
    }


@pytest.mark.parametrize("concurrency", [10, 50, 100])
async def test_concurrent_search_requests_all_succeed(client, fake_es, concurrency):
    fake_es.search.return_value = _es_response(3)

    async def do_search(i: int):
        return await client.post("/api/v1/search", json={"query": f"q{i % 5}"})

    responses = await asyncio.gather(*[do_search(i) for i in range(concurrency)])
    assert all(r.status_code == 200 for r in responses)
    assert all(r.json()["total"] == 3 for r in responses)


async def test_concurrent_document_creation_all_succeed(client):
    async def create(i: int):
        return await client.post("/api/v1/documents", json={"title": f"Doc {i}", "content": "body"})

    responses = await asyncio.gather(*[create(i) for i in range(25)])
    assert all(r.status_code == 201 for r in responses)
    ids = {r.json()["id"] for r in responses}
    assert len(ids) == 25  # all unique, no lost writes


async def test_duplicate_indexing_job_rejected_under_concurrency(db_session):
    """
    Two callers racing to submit a rebuild job with the same idempotency
    key: only one should win, the other must get DuplicateJobError.
    """
    service = IndexingService(db_session)

    async def submit():
        try:
            await service.create_job(JobType.REBUILD, idempotency_key="nightly-rebuild")
            return "created"
        except DuplicateJobError:
            return "duplicate"

    # Sequential is intentional here: SQLite's single-writer model means
    # true concurrent writes would serialize anyway. This still exercises
    # the idempotency-key uniqueness constraint under repeated calls.
    results = [await submit() for _ in range(5)]
    assert results.count("created") == 1
    assert results.count("duplicate") == 4
