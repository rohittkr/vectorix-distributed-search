import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.cache.redis_client import get_client
from app.core.config import get_settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Fixed-window rate limiting per client IP, backed by Redis INCR + EXPIRE.

    Degrades open (allows the request) if Redis is unavailable -- a broken
    cache must never take down the whole API.
    """

    async def dispatch(self, request: Request, call_next):
        settings = get_settings()
        limit = settings.RATE_LIMIT_REQUESTS_PER_MINUTE
        client_ip = request.client.host if request.client else "unknown"
        window = int(time.time() // 60)
        key = f"ratelimit:{client_ip}:{window}"

        try:
            client = get_client()
            count = await client.incr(key)
            if count == 1:
                await client.expire(key, 60)
            if count > limit:
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": {
                            "code": "RATE_LIMIT_EXCEEDED",
                            "message": "Too many requests. Please slow down.",
                        }
                    },
                )
        except Exception:  # noqa: BLE001
            pass  # degrade open

        return await call_next(request)
