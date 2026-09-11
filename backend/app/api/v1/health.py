from fastapi import APIRouter

from app.cache.redis_client import ping as redis_ping
from app.core.database import get_engine
from app.search.es_client import cluster_health, ping as es_ping

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    """Liveness-adjacent overview used by dashboards."""
    return {"status": "ok"}


@router.get("/health/live")
async def liveness() -> dict:
    """Process is up and serving -- does not check dependencies."""
    return {"status": "alive"}


@router.get("/health/ready")
async def readiness() -> dict:
    """Checks all downstream dependencies; used by orchestrators/Compose healthchecks."""
    checks = {}

    checks["elasticsearch"] = "ok" if await es_ping() else "unavailable"

    checks["redis"] = "ok" if await redis_ping() else "unavailable"

    try:
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception:  # noqa: BLE001
        checks["postgres"] = "unavailable"

    overall = "ready" if all(v == "ok" for v in checks.values()) else "degraded"
    return {"status": overall, "checks": checks}


@router.get("/health/elasticsearch")
async def elasticsearch_health() -> dict:
    return await cluster_health()
