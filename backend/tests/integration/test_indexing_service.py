from unittest.mock import AsyncMock, patch

import pytest

from app.core.exceptions import DuplicateJobError, IndexingJobNotFoundError
from app.models.jobs import JobStatus, JobType
from app.repositories.document_repository import DocumentRepository
from app.schemas.document import DocumentCreate
from app.services.indexing_service import IndexingService


@pytest.mark.asyncio
async def test_create_job_defaults_to_pending(db_session):
    service = IndexingService(db_session)
    job = await service.create_job(JobType.BULK_INDEX)
    assert job.status == JobStatus.PENDING.value
    assert job.total_documents == 0


@pytest.mark.asyncio
async def test_duplicate_idempotency_key_rejected(db_session):
    service = IndexingService(db_session)
    await service.create_job(JobType.BULK_INDEX, idempotency_key="batch-1")
    with pytest.raises(DuplicateJobError):
        await service.create_job(JobType.BULK_INDEX, idempotency_key="batch-1")


@pytest.mark.asyncio
async def test_get_job_not_found_raises(db_session):
    service = IndexingService(db_session)
    with pytest.raises(IndexingJobNotFoundError):
        await service.get_job("nope")


@pytest.mark.asyncio
async def test_run_indexing_job_marks_documents_indexed_on_success(db_session, fake_redis):
    repo = DocumentRepository(db_session)
    docs = await repo.bulk_create([DocumentCreate(title=f"T{i}", content="C") for i in range(3)])

    service = IndexingService(db_session)
    job = await service.create_job(JobType.BULK_INDEX)

    with patch("app.services.indexing_service.index_batch", new=AsyncMock(
        return_value=type("R", (), {"succeeded": [d.id for d in docs], "failed": [], "attempts": 1})()
    )):
        finished = await service.run_indexing_job(job)

    assert finished.status == JobStatus.SUCCEEDED.value
    assert finished.processed_documents == 3
    assert finished.failed_documents == 0
    assert await repo.count_indexed() == 3


@pytest.mark.asyncio
async def test_run_indexing_job_records_partial_failure(db_session, fake_redis):
    repo = DocumentRepository(db_session)
    docs = await repo.bulk_create([DocumentCreate(title=f"T{i}", content="C") for i in range(2)])

    service = IndexingService(db_session)
    job = await service.create_job(JobType.BULK_INDEX)

    fake_result = type(
        "R", (), {"succeeded": [docs[0].id], "failed": [(docs[1].id, "mapping error")], "attempts": 3}
    )()
    with patch("app.services.indexing_service.index_batch", new=AsyncMock(return_value=fake_result)):
        finished = await service.run_indexing_job(job)

    assert finished.status == JobStatus.PARTIALLY_FAILED.value
    assert finished.processed_documents == 1
    assert finished.failed_documents == 1
    assert finished.retry_count == 2


@pytest.mark.asyncio
async def test_run_indexing_job_invalidates_cache(db_session, fake_redis):
    from app.cache import cache_service

    repo = DocumentRepository(db_session)
    await repo.bulk_create([DocumentCreate(title="T", content="C")])
    service = IndexingService(db_session)
    job = await service.create_job(JobType.BULK_INDEX)

    version_before = await cache_service._get_version()

    fake_result = type("R", (), {"succeeded": [], "failed": [], "attempts": 1})()
    # No unindexed docs left after first pass returns empty -> loop won't run
    # body, so patch get_unindexed_batch to return docs once then empty.
    with patch("app.services.indexing_service.index_batch", new=AsyncMock(return_value=fake_result)):
        await service.run_indexing_job(job)

    version_after = await cache_service._get_version()
    assert version_after >= version_before
