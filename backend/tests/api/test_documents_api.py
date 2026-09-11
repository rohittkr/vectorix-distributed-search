import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.database import create_all_tables, init_engine
from app.main import create_app


@pytest_asyncio.fixture
async def app():
    init_engine("sqlite+aiosqlite:///:memory:")
    await create_all_tables()
    return create_app()


@pytest_asyncio.fixture
async def client(app, fake_redis, fake_es):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


pytestmark = pytest.mark.asyncio


async def test_create_document_returns_201(client):
    resp = await client.post("/api/v1/documents", json={"title": "Hello", "content": "World"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["title"] == "Hello"
    assert "id" in body


async def test_create_document_missing_content_returns_422(client):
    resp = await client.post("/api/v1/documents", json={"title": "Hello"})
    assert resp.status_code == 422
    body = resp.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"


async def test_get_document_roundtrip(client):
    created = (await client.post("/api/v1/documents", json={"title": "A", "content": "B"})).json()
    resp = await client.get(f"/api/v1/documents/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]


async def test_get_nonexistent_document_returns_structured_404(client):
    resp = await client.get("/api/v1/documents/does-not-exist")
    assert resp.status_code == 404
    body = resp.json()
    assert body["error"]["code"] == "DOCUMENT_NOT_FOUND"
    assert "request_id" in body


async def test_update_document(client):
    created = (await client.post("/api/v1/documents", json={"title": "A", "content": "B"})).json()
    resp = await client.put(f"/api/v1/documents/{created['id']}", json={"title": "Updated"})
    assert resp.status_code == 200
    assert resp.json()["title"] == "Updated"
    assert resp.json()["content"] == "B"


async def test_delete_document(client):
    created = (await client.post("/api/v1/documents", json={"title": "A", "content": "B"})).json()
    resp = await client.delete(f"/api/v1/documents/{created['id']}")
    assert resp.status_code == 204
    resp2 = await client.get(f"/api/v1/documents/{created['id']}")
    assert resp2.status_code == 404


async def test_bulk_create_returns_job_id(client):
    payload = {"documents": [{"title": f"T{i}", "content": "C"} for i in range(5)]}
    resp = await client.post("/api/v1/documents/bulk", json=payload)
    assert resp.status_code == 202
    body = resp.json()
    assert body["accepted"] == 5
    assert "job_id" in body


async def test_every_response_has_request_id_header(client):
    resp = await client.get("/api/v1/health")
    assert "x-request-id" in resp.headers
