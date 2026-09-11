from __future__ import annotations

import redis.asyncio as redis_async

from app.core.config import get_settings

_client: redis_async.Redis | None = None


def get_client() -> redis_async.Redis:
    global _client
    if _client is None:
        settings = get_settings()
        _client = redis_async.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
            max_connections=50,
        )
    return _client


def set_client(client: redis_async.Redis) -> None:
    """Test hook: inject a fake client (e.g. fakeredis.aioredis)."""
    global _client
    _client = client


async def close_client() -> None:
    global _client
    if _client is not None:
        aclose = getattr(_client, "aclose", None)
        if aclose is not None:
            await aclose()
        else:
            await _client.close()
        _client = None


async def ping() -> bool:
    try:
        return bool(await get_client().ping())
    except Exception:  # noqa: BLE001
        return False
