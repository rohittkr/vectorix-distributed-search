"""
Search orchestration: normalize -> cache lookup -> Elasticsearch -> rank
-> cache write -> analytics log.

This is the one place that ties caching and search together, so the
request flow described in docs/architecture.md lives in exactly one
function: `SearchService.search`.
"""
from __future__ import annotations

import time

from elasticsearch import ApiError, ConnectionError as ESConnectionError

from app.cache import cache_service
from app.core.config import get_settings
from app.core.exceptions import SearchServiceUnavailableError
from app.core.logging import get_logger
from app.models.jobs import SearchQueryLog
from app.schemas.search import SearchRequest, SearchResponse, SuggestionResponse
from app.search import queries as query_builder
from app.search.es_client import get_client
from app.services.ranking import hits_to_results

logger = get_logger(__name__)


class SearchService:
    def __init__(self, index_name: str | None = None) -> None:
        self.index_name = index_name or get_settings().ELASTICSEARCH_INDEX

    async def search(self, request: SearchRequest, session=None) -> SearchResponse:
        start = time.perf_counter()
        cache_key = await cache_service.build_cache_key(request)

        cached = await cache_service.get_cached_result(cache_key)
        if cached is not None:
            took_ms = round((time.perf_counter() - start) * 1000, 2)
            response = SearchResponse(**{**cached, "cache_hit": True, "took_ms": took_ms})
            if session is not None:
                await self._log_query(session, request, response)
            return response

        body = query_builder.build_search_body(request)
        try:
            raw = await get_client().search(index=self.index_name, body=body)
        except (ESConnectionError, ApiError) as exc:
            logger.error("Elasticsearch search failed: %s", exc)
            raise SearchServiceUnavailableError() from exc

        total = raw["hits"]["total"]["value"] if isinstance(raw["hits"]["total"], dict) else raw["hits"]["total"]
        results = hits_to_results(raw["hits"]["hits"])
        took_ms = round((time.perf_counter() - start) * 1000, 2)

        response = SearchResponse(
            query=request.query,
            total=total,
            page=request.page,
            page_size=request.page_size,
            took_ms=took_ms,
            cache_hit=False,
            results=results,
        )

        # Cache the response body minus the volatile took_ms/cache_hit fields
        # (those are recomputed on every read).
        cache_payload = response.model_dump()
        cache_payload.pop("took_ms", None)
        cache_payload.pop("cache_hit", None)
        await cache_service.set_cached_result(cache_key, cache_payload)

        if session is not None:
            await self._log_query(session, request, response)

        return response

    async def suggest(self, prefix: str) -> SuggestionResponse:
        prefix = prefix.strip()
        if not prefix:
            return SuggestionResponse(query=prefix, suggestions=[])
        body = query_builder.build_autocomplete_body(prefix)
        try:
            raw = await get_client().search(index=self.index_name, body=body)
        except (ESConnectionError, ApiError) as exc:
            logger.warning("Autocomplete failed, degrading to empty suggestions: %s", exc)
            return SuggestionResponse(query=prefix, suggestions=[])
        suggestions = []
        for hit in raw["hits"]["hits"]:
            title = hit["_source"].get("title")
            if title and title not in suggestions:
                suggestions.append(title)
        return SuggestionResponse(query=prefix, suggestions=suggestions)

    @staticmethod
    async def _log_query(session, request: SearchRequest, response: SearchResponse) -> None:
        try:
            log = SearchQueryLog(
                query_text=request.query,
                filters_json=request.filters.model_dump_json(),
                total_results=response.total,
                took_ms=response.took_ms,
                cache_hit=response.cache_hit,
            )
            session.add(log)
            await session.flush()
        except Exception as exc:  # noqa: BLE001
            # Analytics logging must never break the search response.
            logger.warning("Failed to log search analytics: %s", exc)
