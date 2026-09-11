"""
Pure functions that build Elasticsearch Query DSL bodies.

Kept dependency-free (no ES client here) so they're trivially unit
testable: given a SearchRequest, assert on the resulting dict.
"""
from __future__ import annotations

from app.schemas.search import SearchRequest, SortField


def _build_bool_query(request: SearchRequest) -> dict:
    must: list[dict] = []
    should: list[dict] = []
    filters: list[dict] = []

    query_text = request.query.strip()
    if query_text:
        multi_match: dict = {
            "multi_match": {
                "query": query_text,
                # Field boosting: title matters most, then description,
                # then tags, then full content.
                "fields": ["title^4", "description^2", "tags^2", "content"],
                "type": "best_fields",
                "tie_breaker": 0.3,
            }
        }
        if request.fuzzy:
            multi_match["multi_match"]["fuzziness"] = "AUTO"
        must.append(multi_match)

        # Exact phrase match boosts relevance further without being
        # required (it lives in `should`).
        should.append(
            {
                "multi_match": {
                    "query": query_text,
                    "fields": ["title^6", "description^3"],
                    "type": "phrase",
                    "boost": 2.0,
                }
            }
        )
    else:
        must.append({"match_all": {}})

    f = request.filters
    if f.category:
        filters.append({"term": {"category": f.category}})
    if f.author:
        filters.append({"term": {"author": f.author}})
    if f.language:
        filters.append({"term": {"language": f.language}})
    if f.tags:
        filters.append({"terms": {"tags": f.tags}})
    if f.date_from or f.date_to:
        date_range: dict = {}
        if f.date_from:
            date_range["gte"] = f.date_from
        if f.date_to:
            date_range["lte"] = f.date_to
        filters.append({"range": {"created_at": date_range}})

    return {
        "bool": {
            "must": must,
            "should": should,
            "filter": filters,
        }
    }


def _build_function_score(base_query: dict) -> dict:
    """
    Layer popularity + freshness boosts on top of BM25 relevance.

    - popularity: log1p-scaled field_value_factor, gentle influence so it
      nudges ranking rather than overriding text relevance.
    - freshness: gaussian decay on created_at, half-life ~180 days.
    """
    return {
        "function_score": {
            "query": base_query,
            "functions": [
                {
                    "field_value_factor": {
                        "field": "popularity",
                        "factor": 1.0,
                        "modifier": "log1p",
                        "missing": 0,
                    },
                    "weight": 1.2,
                },
                {
                    "gauss": {
                        "created_at": {
                            "origin": "now",
                            "scale": "180d",
                            "decay": 0.5,
                        }
                    },
                    "weight": 0.8,
                },
            ],
            "score_mode": "sum",
            "boost_mode": "multiply",
        }
    }


_SORT_FIELD_MAP = {
    SortField.CREATED_AT: "created_at",
    SortField.POPULARITY: "popularity",
}


def build_search_body(request: SearchRequest) -> dict:
    bool_query = _build_bool_query(request)
    scored_query = _build_function_score(bool_query)

    body: dict = {
        "query": scored_query,
        "from": (request.page - 1) * request.page_size,
        "size": request.page_size,
        "track_total_hits": True,
    }

    if request.sort_by != SortField.RELEVANCE:
        field = _SORT_FIELD_MAP[request.sort_by]
        body["sort"] = [{field: {"order": request.sort_order.value}}, "_score"]

    if request.highlight and request.query.strip():
        body["highlight"] = {
            "pre_tags": ["<mark>"],
            "post_tags": ["</mark>"],
            "fields": {
                "title": {"number_of_fragments": 0},
                "content": {"fragment_size": 150, "number_of_fragments": 2},
                "description": {"number_of_fragments": 1},
            },
        }

    return body


def build_autocomplete_body(prefix: str, size: int = 8) -> dict:
    return {
        "size": size,
        "_source": ["title", "category"],
        "query": {
            "match": {
                "title.autocomplete": {
                    "query": prefix,
                }
            }
        },
    }
