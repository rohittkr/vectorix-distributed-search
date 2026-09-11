"""
Prometheus metrics via prometheus_client, exposed at GET /api/v1/metrics.

Metric names follow Prometheus naming conventions (unit suffixes,
snake_case). These are registered once at import time; instrument calls
elsewhere in the app increment/observe them directly.
"""
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

http_requests_total = Counter(
    "http_requests_total", "Total HTTP requests", ["method", "path", "status_code"]
)
http_request_duration_seconds = Histogram(
    "http_request_duration_seconds", "HTTP request latency", ["method", "path"]
)

search_requests_total = Counter("search_requests_total", "Total search requests")
search_duration_seconds = Histogram("search_duration_seconds", "Search request latency")
search_cache_hits_total = Counter("search_cache_hits_total", "Search cache hits")
search_cache_misses_total = Counter("search_cache_misses_total", "Search cache misses")

indexing_documents_total = Counter(
    "indexing_documents_total", "Documents processed by the indexer", ["result"]
)
indexing_jobs_total = Counter("indexing_jobs_total", "Indexing jobs completed", ["status"])
indexing_batch_duration_seconds = Histogram("indexing_batch_duration_seconds", "Bulk-index batch latency")

worker_jobs_in_flight = Counter("worker_jobs_in_flight_total", "Worker jobs started")


async def render_metrics() -> tuple[bytes, str]:
    return generate_latest(), CONTENT_TYPE_LATEST
