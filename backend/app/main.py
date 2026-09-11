from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import documents, health, jobs, search, stats
from app.cache.redis_client import close_client as close_redis
from app.core.config import get_settings
from app.core.database import create_all_tables, init_engine
from app.core.logging import configure_logging, get_logger
from app.middleware.error_handler import register_exception_handlers
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.request_id import RequestContextMiddleware
from app.search.es_client import close_client as close_es

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.LOG_LEVEL)
    init_engine()
    await create_all_tables()
    logger.info("Application startup complete (%s)", settings.ENVIRONMENT)
    yield
    await close_es()
    await close_redis()
    logger.info("Application shutdown complete")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        description="A distributed search engine: FastAPI + Elasticsearch + Redis + PostgreSQL.",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(RequestContextMiddleware)

    register_exception_handlers(app)

    prefix = settings.API_V1_PREFIX
    app.include_router(health.router, prefix=prefix)
    app.include_router(documents.router, prefix=prefix)
    app.include_router(search.router, prefix=prefix)
    app.include_router(jobs.router, prefix=prefix)
    app.include_router(stats.router, prefix=prefix)

    return app


app = create_app()
