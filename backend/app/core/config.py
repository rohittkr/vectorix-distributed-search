"""
Centralized application configuration.

All configuration is sourced from environment variables (see .env.example).
Never hardcode secrets or connection strings here.
"""
from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- General ---
    ENVIRONMENT: str = Field(default="development")
    LOG_LEVEL: str = Field(default="INFO")
    APP_NAME: str = Field(default="distributed-search-engine")
    API_V1_PREFIX: str = Field(default="/api/v1")

    # --- CORS ---
    CORS_ORIGINS: List[str] = Field(default_factory=lambda: ["http://localhost:5173", "http://localhost:3000"])

    # --- PostgreSQL ---
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://search:search@postgres:5432/search_engine"
    )
    DATABASE_POOL_SIZE: int = Field(default=10)
    DATABASE_MAX_OVERFLOW: int = Field(default=20)

    # --- Redis ---
    REDIS_URL: str = Field(default="redis://redis:6379/0")
    CACHE_TTL_SECONDS: int = Field(default=300)
    CACHE_ENABLED: bool = Field(default=True)

    # --- Elasticsearch ---
    ELASTICSEARCH_URL: str = Field(default="http://elasticsearch-node-1:9200")
    ELASTICSEARCH_HOSTS: List[str] = Field(
        default_factory=lambda: [
            "http://elasticsearch-node-1:9200",
            "http://elasticsearch-node-2:9200",
            "http://elasticsearch-node-3:9200",
        ]
    )
    ELASTICSEARCH_INDEX: str = Field(default="documents")
    ELASTICSEARCH_USERNAME: str | None = Field(default=None)
    ELASTICSEARCH_PASSWORD: str | None = Field(default=None)
    ELASTICSEARCH_TIMEOUT: int = Field(default=10)
    ELASTICSEARCH_MAX_RETRIES: int = Field(default=3)

    # --- Indexing ---
    INDEXING_BATCH_SIZE: int = Field(default=500)
    INDEXING_MAX_CONCURRENCY: int = Field(default=4)
    INDEXING_MAX_RETRIES: int = Field(default=5)
    INDEXING_RETRY_BASE_DELAY_SECONDS: float = Field(default=0.5)

    # --- Search ---
    SEARCH_DEFAULT_PAGE_SIZE: int = Field(default=20)
    SEARCH_MAX_PAGE_SIZE: int = Field(default=100)
    SEARCH_REQUEST_TIMEOUT_SECONDS: float = Field(default=5.0)

    # --- Rate limiting ---
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = Field(default=300)


@lru_cache
def get_settings() -> Settings:
    return Settings()
