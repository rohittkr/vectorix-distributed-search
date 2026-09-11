import fakeredis.aioredis
import pytest
import pytest_asyncio

from app.cache import redis_client
from app.core.database import Base, create_all_tables, init_engine, session_scope
from app.search import es_client


@pytest_asyncio.fixture
async def db_session():
    """Fresh in-memory SQLite database per test, using the real ORM models."""
    engine = init_engine("sqlite+aiosqlite:///:memory:")
    await create_all_tables()
    async with session_scope() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def fake_redis():
    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    redis_client.set_client(client)
    yield client
    await client.flushall()
    await redis_client.close_client()


@pytest.fixture
def fake_es(mocker):
    """A MagicMock standing in for AsyncElasticsearch, with async methods."""
    from unittest.mock import AsyncMock, MagicMock

    client = MagicMock()
    client.search = AsyncMock()
    client.ping = AsyncMock(return_value=True)
    client.cluster = MagicMock()
    client.cluster.health = AsyncMock(return_value={"status": "green"})
    es_client.set_client(client)
    yield client
