"""
Async SQLAlchemy engine/session setup.

DATABASE_URL points at Postgres (postgresql+asyncpg://...) in every real
deployment. Tests may point it at sqlite+aiosqlite:///:memory: instead --
the ORM layer is written against portable SQLAlchemy types so both work.
"""
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


def _make_engine(url: str):
    connect_args: dict = {}
    kwargs: dict = {}
    if url.startswith("sqlite"):
        # sqlite needs a StaticPool to share the same in-memory DB across
        # connections during tests.
        from sqlalchemy.pool import StaticPool

        connect_args = {"check_same_thread": False}
        kwargs = {"poolclass": StaticPool}
    else:
        kwargs = {
            "pool_size": get_settings().DATABASE_POOL_SIZE,
            "max_overflow": get_settings().DATABASE_MAX_OVERFLOW,
            "pool_pre_ping": True,
        }
    return create_async_engine(url, connect_args=connect_args, **kwargs)


_engine = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def init_engine(database_url: str | None = None):
    global _engine, _session_factory
    url = database_url or get_settings().DATABASE_URL
    _engine = _make_engine(url)
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False, class_=AsyncSession)
    return _engine


def get_engine():
    if _engine is None:
        init_engine()
    return _engine


async def create_all_tables() -> None:
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@asynccontextmanager
async def session_scope() -> AsyncGenerator[AsyncSession, None]:
    if _session_factory is None:
        init_engine()
    assert _session_factory is not None
    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding a request-scoped session."""
    async with session_scope() as session:
        yield session
