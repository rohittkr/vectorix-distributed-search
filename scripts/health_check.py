#!/usr/bin/env python3
"""
Standalone health check for all dependencies, independent of the API
process. Useful for CI smoke tests or manual verification after
`docker compose up`.

Exits non-zero if any dependency is unreachable, so it composes with
shell scripts / CI (`python scripts/health_check.py && echo ready`).
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.cache.redis_client import ping as redis_ping  # noqa: E402
from app.core.database import get_engine, init_engine  # noqa: E402
from app.search.es_client import build_client  # noqa: E402


async def check_postgres() -> tuple[str, bool]:
    try:
        init_engine()
        engine = get_engine()
        async with engine.connect() as conn:
            from sqlalchemy import text

            await conn.execute(text("SELECT 1"))
        return "postgres: ok", True
    except Exception as exc:  # noqa: BLE001
        return f"postgres: FAILED ({exc})", False


async def check_redis() -> tuple[str, bool]:
    ok = await redis_ping()
    return ("redis: ok" if ok else "redis: FAILED (unreachable)"), ok


async def check_elasticsearch() -> tuple[str, bool]:
    client = build_client()
    try:
        health = await client.cluster.health()
        status = health.get("status")
        ok = status in ("green", "yellow")
        return f"elasticsearch: {status}", ok
    except Exception as exc:  # noqa: BLE001
        return f"elasticsearch: FAILED ({exc})", False
    finally:
        await client.close()


async def main() -> int:
    results = await asyncio.gather(check_postgres(), check_redis(), check_elasticsearch())
    all_ok = True
    for message, ok in results:
        print(message)
        all_ok = all_ok and ok
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
