from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import cache_service
from app.core.config import get_settings
from app.core.exceptions import DuplicateJobError, IndexingJobNotFoundError
from app.core.logging import get_logger
from app.indexing.pipeline import index_batch
from app.models.jobs import IndexingFailure, IndexingJob, JobStatus, JobType
from app.repositories.document_repository import DocumentRepository
from app.search.es_client import get_client

logger = get_logger(__name__)


class IndexingService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = DocumentRepository(session)

    async def create_job(self, job_type: JobType, idempotency_key: str | None = None) -> IndexingJob:
        if idempotency_key:
            existing = await self.session.execute(
                select(IndexingJob).where(
                    IndexingJob.idempotency_key == idempotency_key,
                    IndexingJob.status.in_([JobStatus.PENDING.value, JobStatus.RUNNING.value]),
                )
            )
            if existing.scalar_one_or_none() is not None:
                raise DuplicateJobError()

        job = IndexingJob(job_type=job_type.value, status=JobStatus.PENDING.value, idempotency_key=idempotency_key)
        self.session.add(job)
        await self.session.flush()
        return job

    async def get_job(self, job_id: str) -> IndexingJob:
        job = await self.session.get(IndexingJob, job_id)
        if job is None:
            raise IndexingJobNotFoundError()
        return job

    async def list_jobs(self, limit: int = 50) -> list[IndexingJob]:
        result = await self.session.execute(
            select(IndexingJob).order_by(IndexingJob.created_at.desc()).limit(limit)
        )
        return list(result.scalars().all())

    async def run_indexing_job(self, job: IndexingJob) -> IndexingJob:
        """
        Drain unindexed documents in batches, bulk-indexing each batch with
        retry, recording per-document failures, and updating job progress.
        """
        settings = get_settings()
        job.status = JobStatus.RUNNING.value
        job.started_at = datetime.now(timezone.utc)
        await self.session.flush()

        client = get_client()
        batch_size = settings.INDEXING_BATCH_SIZE
        total_processed = 0
        total_failed = 0
        # Documents that permanently failed *this run* -- excluded from
        # subsequent fetches so a stuck document can't spin the loop
        # forever (it remains indexed_at IS NULL after exhausting retries).
        permanently_failed_ids: set[str] = set()

        while True:
            batch = await self.repo.get_unindexed_batch(batch_size, exclude_ids=permanently_failed_ids)
            if not batch:
                break

            job.total_documents += len(batch)
            result = await index_batch(client, batch)

            if result.succeeded:
                await self.repo.mark_indexed(result.succeeded)
                total_processed += len(result.succeeded)

            for doc_id, reason in result.failed:
                total_failed += 1
                permanently_failed_ids.add(doc_id)
                self.session.add(
                    IndexingFailure(job_id=job.id, document_id=doc_id, reason=reason, attempt=result.attempts)
                )

            job.processed_documents = total_processed
            job.failed_documents = total_failed
            job.retry_count = max(job.retry_count, result.attempts - 1)
            await self.session.flush()

            if len(batch) < batch_size:
                # Fewer than a full batch came back -- we've drained
                # everything currently eligible (accounting for exclusions).
                break

        job.finished_at = datetime.now(timezone.utc)
        if total_failed == 0:
            job.status = JobStatus.SUCCEEDED.value
        elif total_processed == 0:
            job.status = JobStatus.FAILED.value
        else:
            job.status = JobStatus.PARTIALLY_FAILED.value

        await self.session.flush()

        # Any change to the index invalidates cached search results.
        await cache_service.invalidate_all()

        return job
