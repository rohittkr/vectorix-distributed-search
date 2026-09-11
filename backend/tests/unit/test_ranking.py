from app.services.ranking import hit_to_result_item, hits_to_results


def _hit(**overrides):
    base = {
        "_id": "doc-1",
        "_score": 4.2,
        "_source": {
            "id": "doc-1",
            "title": "Distributed Systems 101",
            "description": "An intro",
            "category": "tech",
            "author": "jane",
            "tags": ["distributed", "systems"],
            "url": "https://example.com/doc-1",
            "popularity": 12.5,
            "created_at": "2026-01-01T00:00:00Z",
        },
        "highlight": {"title": ["<mark>Distributed</mark> Systems 101"]},
    }
    base.update(overrides)
    return base


def test_hit_to_result_item_maps_all_fields():
    item = hit_to_result_item(_hit())
    assert item.id == "doc-1"
    assert item.title == "Distributed Systems 101"
    assert item.score == 4.2
    assert item.popularity == 12.5
    assert item.tags == ["distributed", "systems"]
    assert "title" in item.highlight


def test_hit_to_result_item_handles_missing_optional_fields():
    hit = _hit(_source={"id": "doc-2", "title": "Bare"})
    item = hit_to_result_item(hit)
    assert item.description is None
    assert item.tags == []
    assert item.popularity == 0.0


def test_hits_to_results_preserves_order():
    hits = [_hit(_id="a", _score=1.0), _hit(_id="b", _score=5.0)]
    results = hits_to_results(hits)
    assert [r.score for r in results] == [1.0, 5.0]
