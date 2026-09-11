import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.logging import request_id_ctx
from app.monitoring.metrics import http_request_duration_seconds, http_requests_total


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Attaches a request ID to every request/response and records HTTP metrics."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        token = request_id_ctx.set(request_id)
        start = time.perf_counter()

        try:
            response = await call_next(request)
        finally:
            request_id_ctx.reset(token)

        duration = time.perf_counter() - start
        route_path = request.scope.get("route").path if request.scope.get("route") else request.url.path
        http_requests_total.labels(
            method=request.method, path=route_path, status_code=response.status_code
        ).inc()
        http_request_duration_seconds.labels(method=request.method, path=route_path).observe(duration)

        response.headers["X-Request-ID"] = request_id
        return response
