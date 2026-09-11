from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.jobs import JobType
from app.schemas.job import IndexingJobRead, ReindexRequest
from app.services.indexing_service import IndexingService

router = APIRouter(tags=["indexing"])


@router.post("/index/rebuild", response_model=IndexingJobRead, status_code=status.HTTP_202_ACCEPTED)
async def rebuild_index(payload: ReindexRequest, session: AsyncSession = Depends(get_db)) -> IndexingJobRead:
    """
    Queue a full rebuild: every document is re-sent to Elasticsearch,
    regardless of its current `indexed_at` state. The worker process picks
    this job up asynchronously.
    """
    service = IndexingService(session)
    job = await service.create_job(JobType.REBUILD, idempotency_key=payload.idempotency_key)
    return IndexingJobRead.model_validate(job)


@router.post("/index/reindex", response_model=IndexingJobRead, status_code=status.HTTP_202_ACCEPTED)
async def reindex(payload: ReindexRequest, session: AsyncSession = Depends(get_db)) -> IndexingJobRead:
    """Queue indexing of only currently-unindexed documents."""
    service = IndexingService(session)
    job = await service.create_job(JobType.REINDEX, idempotency_key=payload.idempotency_key)
    return IndexingJobRead.model_validate(job)


@router.get("/jobs", response_model=list[IndexingJobRead])
async def list_jobs(session: AsyncSession = Depends(get_db)) -> list[IndexingJobRead]:
    service = IndexingService(session)
    jobs = await service.list_jobs()
    return [IndexingJobRead.model_validate(j) for j in jobs]


@router.get("/jobs/{job_id}", response_model=IndexingJobRead)
async def get_job(job_id: str, session: AsyncSession = Depends(get_db)) -> IndexingJobRead:
    service = IndexingService(session)
    job = await service.get_job(job_id)
    return IndexingJobRead.model_validate(job)
