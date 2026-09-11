"""
Search-result caching.

Cache keys are a deterministic hash of the *normalized* search request --
query text lowercased/trimmed, filters sorted, pagination and sort params
included -- so semantically identical requests always hit the same key,
regardless of field ordering in the incoming JSON.

Hit/miss counters are kept in Redis itself (INCR) so they survive
across app instances/restarts and can be scraped for /metrics.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

from app.cache.redis_client import get_client
from app.core.config import get_settings
from app.core.logging import get_logger
from app.schemas.search import SearchRequest

logger = get_logger(__name__)

CACHE_KEY_PREFIX = "search"
STATS_HITS_KEY = "cache:stats:hits"
STATS_MISSES_KEY = "cache:stats:misses"
INVALIDATION_VERSION_KEY = "cache:version"


def normalize_request(request: SearchRequest) -> dict[str, Any]:
    filters = request.filters
    return {
        "q": request.query.strip().lower(),
        "category": filters.category,
        "tags": sorted(filters.tags) if filters.tags else None,
        "author": filters.author,
        "language": filters.language,
        "date_from": filters.date_from,
        "date_to": filters.date_to,
        "page": request.page,
        "page_size": request.page_size,
        "sort_by": request.sort_by.value,
        "sort_order": request.sort_order.value,
        "fuzzy": request.fuzzy,
        "highlight": request.highlight,
    }


async def build_cache_key(request: SearchRequest) -> str:
    normalized = normalize_request(request)
    version = await _get_version()
    payload = json.dumps(normalized, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"{CACHE_KEY_PREFIX}:v{version}:{digest}"


async def _get_version() -> int:
    """
    Global invalidation version. Bumping it (via invalidate_all) instantly
    orphans every previously-cached key without needing to scan/delete them.
    """
    try:
        value = await get_client().get(INVALIDATION_VERSION_KEY)
        # Redis INCR on a missing key starts it at 1, so the "no version set
        # yet" default must also be 0 -- otherwise the very first
        # invalidate_all() call (0 -> 1) is indistinguishable from having
        # never invalidated at all.
        return int(value) if value else 0
    except Exception:  # noqa: BLE001
        return 0


async def get_cached_result(key: str) -> dict | None:
    settings = get_settings()
    if not settings.CACHE_ENABLED:
        return None
    try:
        raw = await get_client().get(key)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Cache read failed, degrading to no-cache: %s", exc)
        return None
    if raw is None:
        await _incr(STATS_MISSES_KEY)
        return None
    await _incr(STATS_HITS_KEY)
    return json.loads(raw)


async def set_cached_result(key: str, value: dict, ttl: int | None = None) -> None:
    settings = get_settings()
    if not settings.CACHE_ENABLED:
        return
    ttl = ttl if ttl is not None else settings.CACHE_TTL_SECONDS
    try:
        await get_client().set(key, json.dumps(value, default=str), ex=ttl)
    except Exception as exc:  # noqa: BLE001
        # Cache is best-effort: a write failure must never break search.
        logger.warning("Cache write failed, continuing without caching: %s", exc)


async def invalidate_all() -> None:
    """Bump the invalidation version -- O(1), no key scan needed."""
    try:
        await get_client().incr(INVALIDATION_VERSION_KEY)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Cache invalidation failed: %s", exc)


async def _incr(key: str) -> None:
    try:
        await get_client().incr(key)
    except Exception:  # noqa: BLE001
        pass


async def get_stats() -> dict:
    try:
        client = get_client()
        hits = int(await client.get(STATS_HITS_KEY) or 0)
        misses = int(await client.get(STATS_MISSES_KEY) or 0)
    except Exception:  # noqa: BLE001
        hits, misses = 0, 0
    total = hits + misses
    hit_rate = round(hits / total, 4) if total else 0.0
    return {"hits": hits, "misses": misses, "total": total, "hit_rate": hit_rate}
