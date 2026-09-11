import uuid
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    PARTIALLY_FAILED = "partially_failed"


class JobType(str, Enum):
    INDEX_DOCUMENT = "index_document"
    BULK_INDEX = "bulk_index"
    REINDEX = "reindex"
    REBUILD = "rebuild"


class IndexingJob(Base):
    __tablename__ = "indexing_jobs"
    __table_args__ = (
        Index("ix_indexing_jobs_status", "status"),
        Index("ix_indexing_jobs_idempotency_key", "idempotency_key", unique=True),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    job_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default=JobStatus.PENDING.value)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True, unique=True)

    total_documents: Mapped[int] = mapped_column(Integer, default=0)
    processed_documents: Mapped[int] = mapped_column(Integer, default=0)
    failed_documents: Mapped[int] = mapped_column(Integer, default=0)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    @property
    def progress_pct(self) -> float:
        if self.total_documents == 0:
            return 0.0
        return round(100.0 * self.processed_documents / self.total_documents, 2)


class IndexingFailure(Base):
    __tablename__ = "indexing_failures"
    __table_args__ = (Index("ix_indexing_failures_job_id", "job_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("indexing_jobs.id"), nullable=False)
    document_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    attempt: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class SearchQueryLog(Base):
    """Search analytics: one row per executed search, for the dashboard."""

    __tablename__ = "search_queries"
    __table_args__ = (Index("ix_search_queries_created_at", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    filters_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_results: Mapped[int] = mapped_column(Integer, default=0)
    took_ms: Mapped[float] = mapped_column(Float, default=0.0)
    cache_hit: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class SystemEvent(Base):
    """Coarse-grained event log: node failures, worker restarts, recoveries."""

    __tablename__ = "system_events"
    __table_args__ = (Index("ix_system_events_created_at", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), default="info")
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
