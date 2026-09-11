from app.schemas.search import SearchFilters, SearchRequest, SortField, SortOrder
from app.search.queries import build_autocomplete_body, build_search_body


def test_basic_query_uses_multi_match_with_field_boosts():
    req = SearchRequest(query="distributed systems")
    body = build_search_body(req)
    must = body["query"]["function_score"]["query"]["bool"]["must"]
    assert must[0]["multi_match"]["query"] == "distributed systems"
    assert "title^4" in must[0]["multi_match"]["fields"]
    assert must[0]["multi_match"]["fuzziness"] == "AUTO"


def test_disabling_fuzzy_removes_fuzziness_param():
    req = SearchRequest(query="test", fuzzy=False)
    body = build_search_body(req)
    must = body["query"]["function_score"]["query"]["bool"]["must"]
    assert "fuzziness" not in must[0]["multi_match"]


def test_empty_query_uses_match_all():
    req = SearchRequest(query="")
    body = build_search_body(req)
    must = body["query"]["function_score"]["query"]["bool"]["must"]
    assert must == [{"match_all": {}}]


def test_phrase_match_added_to_should_when_query_present():
    req = SearchRequest(query="hello world")
    body = build_search_body(req)
    should = body["query"]["function_score"]["query"]["bool"]["should"]
    assert should[0]["multi_match"]["type"] == "phrase"


def test_category_filter_becomes_term_filter():
    req = SearchRequest(query="x", filters=SearchFilters(category="tech"))
    body = build_search_body(req)
    filters = body["query"]["function_score"]["query"]["bool"]["filter"]
    assert {"term": {"category": "tech"}} in filters


def test_tags_filter_becomes_terms_filter():
    req = SearchRequest(query="x", filters=SearchFilters(tags=["python", "ml"]))
    body = build_search_body(req)
    filters = body["query"]["function_score"]["query"]["bool"]["filter"]
    assert {"terms": {"tags": ["python", "ml"]}} in filters


def test_date_range_filter():
    req = SearchRequest(query="x", filters=SearchFilters(date_from="2024-01-01", date_to="2024-12-31"))
    body = build_search_body(req)
    filters = body["query"]["function_score"]["query"]["bool"]["filter"]
    date_filter = next(f for f in filters if "range" in f)
    assert date_filter["range"]["created_at"] == {"gte": "2024-01-01", "lte": "2024-12-31"}


def test_pagination_computed_from_page_and_page_size():
    req = SearchRequest(query="x", page=3, page_size=10)
    body = build_search_body(req)
    assert body["from"] == 20
    assert body["size"] == 10


def test_sort_by_created_at_adds_sort_clause():
    req = SearchRequest(query="x", sort_by=SortField.CREATED_AT, sort_order=SortOrder.ASC)
    body = build_search_body(req)
    assert body["sort"][0] == {"created_at": {"order": "asc"}}


def test_relevance_sort_has_no_explicit_sort_clause():
    req = SearchRequest(query="x", sort_by=SortField.RELEVANCE)
    body = build_search_body(req)
    assert "sort" not in body


def test_highlight_included_only_when_requested_and_query_nonempty():
    req = SearchRequest(query="x", highlight=True)
    body = build_search_body(req)
    assert "highlight" in body

    req2 = SearchRequest(query="", highlight=True)
    body2 = build_search_body(req2)
    assert "highlight" not in body2

    req3 = SearchRequest(query="x", highlight=False)
    body3 = build_search_body(req3)
    assert "highlight" not in body3


def test_function_score_includes_popularity_and_freshness():
    req = SearchRequest(query="x")
    body = build_search_body(req)
    functions = body["query"]["function_score"]["functions"]
    assert any("field_value_factor" in f for f in functions)
    assert any("gauss" in f for f in functions)


def test_autocomplete_body_targets_autocomplete_subfield():
    body = build_autocomplete_body("dist", size=5)
    assert body["size"] == 5
    assert body["query"]["match"]["title.autocomplete"]["query"] == "dist"
