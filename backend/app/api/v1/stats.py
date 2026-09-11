from fastapi import APIRouter, Depends, Response
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import cache_service
from app.cache.redis_client import ping as redis_ping
from app.core.database import get_db
from app.models.document import Document
from app.models.jobs import IndexingJob, JobStatus
from app.monitoring.metrics import render_metrics
from app.repositories.document_repository import DocumentRepository
from app.schemas.job import StatsResponse
from app.search.es_client import cluster_health

router = APIRouter(tags=["stats"])


@router.get("/stats", response_model=StatsResponse)
async def stats(session: AsyncSession = Depends(get_db)) -> StatsResponse:
    repo = DocumentRepository(session)
    total = await repo.count_all()
    indexed = await repo.count_indexed()

    failed_result = await session.execute(
        select(func.count()).select_from(Document).where(Document.indexed_at.is_(None))
    )
    pending = int(failed_result.scalar_one())

    active_jobs_result = await session.execute(
        select(func.count()).select_from(IndexingJob).where(
            IndexingJob.status.in_([JobStatus.PENDING.value, JobStatus.RUNNING.value])
        )
    )
    active_jobs = int(active_jobs_result.scalar_one())

    es_health = await cluster_health()
    redis_ok = await redis_ping()
    cache_stats = await cache_service.get_stats()

    return StatsResponse(
        total_documents=total,
        indexed_documents=indexed,
        pending_documents=pending,
        failed_documents=0,
        active_jobs=active_jobs,
        elasticsearch_status=es_health.get("status", "unknown"),
        redis_status="ok" if redis_ok else "unavailable",
        postgres_status="ok",
        cache_hit_rate=cache_stats["hit_rate"],
    )


@router.get("/metrics")
async def metrics() -> Response:
    """Prometheus text-format metrics."""
    body, content_type = await render_metrics()
    return Response(content=body, media_type=content_type)
