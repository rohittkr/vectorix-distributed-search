"""
Standalone worker process.

Runs as its own container (see docker-compose.yml `worker` service),
separate from the FastAPI process, so indexing never competes with API
request handling for the event loop or DB connections.

Polls for PENDING indexing jobs and runs them one at a time, bounded by
INDEXING_MAX_CONCURRENCY concurrent jobs.
"""
from __future__ import annotations

import asyncio
import signal

from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import create_all_tables, init_engine, session_scope
from app.core.logging import configure_logging, get_logger
from app.models.jobs import IndexingJob, JobStatus
from app.services.indexing_service import IndexingService

logger = get_logger(__name__)

POLL_INTERVAL_SECONDS = 2.0
_shutdown = asyncio.Event()


async def _claim_next_job(session) -> IndexingJob | None:
    result = await session.execute(
        select(IndexingJob)
        .where(IndexingJob.status == JobStatus.PENDING.value)
        .order_by(IndexingJob.created_at)
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    return result.scalar_one_or_none()


async def worker_loop() -> None:
    settings = get_settings()
    semaphore = asyncio.Semaphore(settings.INDEXING_MAX_CONCURRENCY)

    async def run_one(job_id: str) -> None:
        async with semaphore:
            async with session_scope() as session:
                service = IndexingService(session)
                job = await service.get_job(job_id)
                logger.info("Starting indexing job %s (%s)", job.id, job.job_type)
                try:
                    await service.run_indexing_job(job)
                    logger.info(
                        "Finished job %s: status=%s processed=%s failed=%s",
                        job.id,
                        job.status,
                        job.processed_documents,
                        job.failed_documents,
                    )
                except Exception:  # noqa: BLE001
                    logger.exception("Job %s crashed", job.id)

    in_flight: set[asyncio.Task] = set()
    while not _shutdown.is_set():
        async with session_scope() as session:
            job = await _claim_next_job(session)
            if job is not None:
                job.status = JobStatus.RUNNING.value
                await session.flush()
                job_id = job.id
            else:
                job_id = None

        if job_id:
            task = asyncio.create_task(run_one(job_id))
            in_flight.add(task)
            task.add_done_callback(in_flight.discard)
        else:
            await asyncio.sleep(POLL_INTERVAL_SECONDS)

    if in_flight:
        await asyncio.gather(*in_flight, return_exceptions=True)


def _handle_signal(*_args: object) -> None:
    logger.info("Shutdown signal received, draining in-flight jobs...")
    _shutdown.set()


async def main() -> None:
    settings = get_settings()
    configure_logging(settings.LOG_LEVEL)
    init_engine()
    await create_all_tables()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, _handle_signal)

    logger.info("Indexer worker started, polling every %ss", POLL_INTERVAL_SECONDS)
    await worker_loop()


if __name__ == "__main__":
    asyncio.run(main())
