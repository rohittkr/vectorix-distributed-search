from enum import Enum

from pydantic import BaseModel, Field, model_validator


class SortField(str, Enum):
    RELEVANCE = "relevance"
    CREATED_AT = "created_at"
    POPULARITY = "popularity"


class SortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"


class SearchFilters(BaseModel):
    category: str | None = None
    tags: list[str] | None = None
    author: str | None = None
    language: str | None = None
    date_from: str | None = Field(default=None, description="ISO-8601 date, inclusive")
    date_to: str | None = Field(default=None, description="ISO-8601 date, inclusive")


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=0, max_length=1024)
    filters: SearchFilters = Field(default_factory=SearchFilters)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    sort_by: SortField = Field(default=SortField.RELEVANCE)
    sort_order: SortOrder = Field(default=SortOrder.DESC)
    fuzzy: bool = Field(default=True)
    highlight: bool = Field(default=True)

    @model_validator(mode="after")
    def _validate_query_or_filters(self) -> "SearchRequest":
        if not self.query.strip() and not any(
            [self.filters.category, self.filters.tags, self.filters.author]
        ):
            # An empty query with no filters is a "browse all" -- allowed,
            # but normalize the query to empty string explicitly.
            self.query = ""
        return self


class SearchResultItem(BaseModel):
    id: str
    title: str
    description: str | None = None
    category: str | None = None
    author: str | None = None
    tags: list[str] = Field(default_factory=list)
    url: str | None = None
    score: float
    popularity: float = 0.0
    created_at: str | None = None
    highlight: dict[str, list[str]] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    query: str
    total: int
    page: int
    page_size: int
    took_ms: float
    cache_hit: bool
    results: list[SearchResultItem]


class SuggestionResponse(BaseModel):
    query: str
    suggestions: list[str]
