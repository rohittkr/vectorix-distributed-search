"""
Thin wrapper around the official Elasticsearch async client.

Centralizing client creation gives us one place to configure connection
pooling, retries, and timeouts, and one place to swap in a fake client
for unit tests.
"""
from __future__ import annotations

from typing import Any

from elasticsearch import AsyncElasticsearch, ConnectionError as ESConnectionError, TransportError

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_client: AsyncElasticsearch | None = None


def build_client() -> AsyncElasticsearch:
    settings = get_settings()
    kwargs: dict[str, Any] = {
        "hosts": settings.ELASTICSEARCH_HOSTS,
        "request_timeout": settings.ELASTICSEARCH_TIMEOUT,
        "max_retries": settings.ELASTICSEARCH_MAX_RETRIES,
        "retry_on_timeout": True,
        # Connection pooling: one pool per host, bounded by the client lib.
        "sniff_on_start": False,
    }
    if settings.ELASTICSEARCH_USERNAME and settings.ELASTICSEARCH_PASSWORD:
        kwargs["basic_auth"] = (settings.ELASTICSEARCH_USERNAME, settings.ELASTICSEARCH_PASSWORD)
    return AsyncElasticsearch(**kwargs)


def get_client() -> AsyncElasticsearch:
    global _client
    if _client is None:
        _client = build_client()
    return _client


def set_client(client: AsyncElasticsearch) -> None:
    """Test hook: inject a fake/mock client."""
    global _client
    _client = client


async def close_client() -> None:
    global _client
    if _client is not None:
        await _client.close()
        _client = None


async def ping() -> bool:
    try:
        return await get_client().ping()
    except (ESConnectionError, TransportError, Exception) as exc:  # noqa: BLE001
        logger.warning("Elasticsearch ping failed: %s", exc)
        return False


async def cluster_health() -> dict[str, Any]:
    try:
        return await get_client().cluster.health()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Elasticsearch health check failed: %s", exc)
        return {"status": "unreachable", "error": str(exc)}
