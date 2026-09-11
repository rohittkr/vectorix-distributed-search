"""
Index settings and mapping for the `documents` index.

Design notes:
- `title`/`content`/`description` use the custom `text_analyzer` (standard
  tokenizer + lowercase + stop + a shingle-free english stemmer) for good
  recall, plus a `.keyword` and `.autocomplete` sub-field for exact
  matching and prefix suggestions respectively.
- `tags` and `category` are `keyword` fields -- exact filtering, not
  full-text.
- `created_at`/`updated_at` are `date` for range filtering and freshness
  boosting. `popularity` is a `float` used for score boosting.
"""

INDEX_SETTINGS = {
    "number_of_shards": 3,
    "number_of_replicas": 1,
    "analysis": {
        "filter": {
            "english_stemmer": {"type": "stemmer", "language": "english"},
            "english_stop": {"type": "stop", "stopwords": "_english_"},
        },
        "analyzer": {
            "text_analyzer": {
                "type": "custom",
                "tokenizer": "standard",
                "filter": ["lowercase", "english_stop", "english_stemmer"],
            },
            "autocomplete_analyzer": {
                "type": "custom",
                "tokenizer": "autocomplete_tokenizer",
                "filter": ["lowercase"],
            },
            "autocomplete_search_analyzer": {
                "type": "custom",
                "tokenizer": "lowercase",
            },
        },
        "tokenizer": {
            "autocomplete_tokenizer": {
                "type": "edge_ngram",
                "min_gram": 2,
                "max_gram": 15,
                "token_chars": ["letter", "digit"],
            }
        },
    },
}

INDEX_MAPPING = {
    "properties": {
        "id": {"type": "keyword"},
        "title": {
            "type": "text",
            "analyzer": "text_analyzer",
            "fields": {
                "keyword": {"type": "keyword", "ignore_above": 512},
                "autocomplete": {
                    "type": "text",
                    "analyzer": "autocomplete_analyzer",
                    "search_analyzer": "autocomplete_search_analyzer",
                },
            },
        },
        "content": {"type": "text", "analyzer": "text_analyzer"},
        "description": {"type": "text", "analyzer": "text_analyzer"},
        "category": {"type": "keyword"},
        "author": {"type": "keyword"},
        "tags": {"type": "keyword"},
        "language": {"type": "keyword"},
        "source": {"type": "keyword"},
        "url": {"type": "keyword"},
        "popularity": {"type": "float"},
        "created_at": {"type": "date"},
        "updated_at": {"type": "date"},
    }
}


def build_index_body() -> dict:
    return {"settings": INDEX_SETTINGS, "mappings": INDEX_MAPPING}
