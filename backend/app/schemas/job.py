from datetime import datetime

from pydantic import BaseModel, ConfigDict


class IndexingJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    job_type: str
    status: str
    total_documents: int
    processed_documents: int
    failed_documents: int
    retry_count: int
    progress_pct: float
    error_message: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None


class ReindexRequest(BaseModel):
    idempotency_key: str | None = None


class StatsResponse(BaseModel):
    total_documents: int
    indexed_documents: int
    pending_documents: int
    failed_documents: int
    active_jobs: int
    elasticsearch_status: str
    redis_status: str
    postgres_status: str
    cache_hit_rate: float
