"""Application-level exceptions mapped to structured API error responses."""


class AppError(Exception):
    """Base class for all application errors that carry a stable error code."""

    code: str = "INTERNAL_ERROR"
    status_code: int = 500
    message: str = "An unexpected error occurred."

    def __init__(self, message: str | None = None, **details: object) -> None:
        self.message = message or self.message
        self.details = details
        super().__init__(self.message)


class DocumentNotFoundError(AppError):
    code = "DOCUMENT_NOT_FOUND"
    status_code = 404
    message = "The requested document was not found."


class InvalidDocumentError(AppError):
    code = "INVALID_DOCUMENT"
    status_code = 422
    message = "The document payload is invalid."


class SearchServiceUnavailableError(AppError):
    code = "SEARCH_SERVICE_UNAVAILABLE"
    status_code = 503
    message = "Search service is temporarily unavailable."


class CacheUnavailableError(AppError):
    code = "CACHE_UNAVAILABLE"
    status_code = 503
    message = "Cache service is temporarily unavailable."


class IndexingJobNotFoundError(AppError):
    code = "INDEXING_JOB_NOT_FOUND"
    status_code = 404
    message = "The requested indexing job was not found."


class DuplicateJobError(AppError):
    code = "DUPLICATE_INDEXING_JOB"
    status_code = 409
    message = "An identical indexing job is already running."


class RateLimitExceededError(AppError):
    code = "RATE_LIMIT_EXCEEDED"
    status_code = 429
    message = "Too many requests. Please slow down."
