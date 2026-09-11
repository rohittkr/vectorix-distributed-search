from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.search import SearchFilters, SearchRequest, SearchResponse, SortField, SortOrder, SuggestionResponse
from app.services.search_service import SearchService

router = APIRouter(tags=["search"])


def get_search_service() -> SearchService:
    return SearchService()


@router.post("/search", response_model=SearchResponse)
async def search_post(
    request: SearchRequest,
    session: AsyncSession = Depends(get_db),
    service: SearchService = Depends(get_search_service),
) -> SearchResponse:
    return await service.search(request, session=session)


@router.get("/search", response_model=SearchResponse)
async def search_get(
    q: str = Query(default=""),
    category: str | None = None,
    author: str | None = None,
    language: str | None = None,
    tags: list[str] | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    sort_by: SortField = Query(default=SortField.RELEVANCE),
    sort_order: SortOrder = Query(default=SortOrder.DESC),
    fuzzy: bool = Query(default=True),
    highlight: bool = Query(default=True),
    session: AsyncSession = Depends(get_db),
    service: SearchService = Depends(get_search_service),
) -> SearchResponse:
    """GET variant of search -- convenient for shareable/bookmarkable URLs."""
    request = SearchRequest(
        query=q,
        filters=SearchFilters(category=category, author=author, language=language, tags=tags),
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
        fuzzy=fuzzy,
        highlight=highlight,
    )
    return await service.search(request, session=session)


@router.get("/suggestions", response_model=SuggestionResponse)
async def suggestions(
    q: str = Query(default=""),
    service: SearchService = Depends(get_search_service),
) -> SuggestionResponse:
    return await service.suggest(q)
