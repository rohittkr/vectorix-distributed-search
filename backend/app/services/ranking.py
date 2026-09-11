"""
Post-processing of raw Elasticsearch hits into API-shaped search results.

The actual ranking (BM25 + popularity/freshness boosting) happens inside
Elasticsearch via the function_score query built in app.search.queries.
This module is responsible for translating a raw ES hit into our
SearchResultItem shape, including highlight fragments.
"""
from __future__ import annotations

from app.schemas.search import SearchResultItem


def hit_to_result_item(hit: dict) -> SearchResultItem:
    source = hit.get("_source", {})
    highlight = hit.get("highlight", {})
    return SearchResultItem(
        id=source.get("id", hit.get("_id")),
        title=source.get("title", ""),
        description=source.get("description"),
        category=source.get("category"),
        author=source.get("author"),
        tags=source.get("tags", []) or [],
        url=source.get("url"),
        score=float(hit.get("_score") or 0.0),
        popularity=float(source.get("popularity") or 0.0),
        created_at=source.get("created_at"),
        highlight=highlight,
    )


def hits_to_results(hits: list[dict]) -> list[SearchResultItem]:
    return [hit_to_result_item(h) for h in hits]
