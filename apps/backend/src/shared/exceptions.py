"""
Application-level exception hierarchy.

Every expected (non-500) error in the system is represented by a subclass
of ``AppException``. The presentation layer catches these and maps them
to the appropriate HTTP status codes via the global exception handler.
Part of the shared kernel.

Typical usage:
    from src.shared.exceptions import NotFoundError

    raise NotFoundError(
        message="Order not found",
        error_code="ORDER_NOT_FOUND",
        details={"order_id": str(order_id)},
    )
"""

from typing import Any


class AppException(Exception):
    """Base class for all expected application errors.

    Attributes:
        message: Human-readable error description.
        status_code: HTTP status code mapped to this error category.
        error_code: Machine-readable error identifier for API consumers.
        details: Arbitrary context attached to the error response body.
    """

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: str = "INTERNAL_ERROR",
        details: dict[str, Any] | None = None,
    ):
        self.message: str = message
        self.status_code: int = status_code
        self.error_code: str = error_code
        self.details: dict[str, Any] = details or {}
        super().__init__(self.message)


class NotFoundError(AppException):
    """Raised when a requested resource does not exist (HTTP 404)."""

    def __init__(
        self,
        message: str = "Resource not found",
        error_code: str = "NOT_FOUND",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message,
            status_code=404,
            error_code=error_code,
            details=details,
        )


class UnauthorizedError(AppException):
    """Raised when authentication is required but missing or invalid (HTTP 401)."""

    def __init__(
        self,
        message: str = "Authentication required",
        error_code: str = "UNAUTHORIZED",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message,
            status_code=401,
            error_code=error_code,
            details=details,
        )


class ForbiddenError(AppException):
    """Raised when the caller lacks required permissions (HTTP 403)."""

    def __init__(
        self,
        message: str = "Access denied. Insufficient permissions.",
        error_code: str = "FORBIDDEN",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message,
            status_code=403,
            error_code=error_code,
            details=details,
        )


class ConflictError(AppException):
    """Raised on a state conflict, e.g. duplicate slug or version mismatch (HTTP 409)."""

    def __init__(
        self,
        message: str = "Resource state conflict",
        error_code: str = "CONFLICT",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message,
            status_code=409,
            error_code=error_code,
            details=details,
        )


class ValidationError(AppException):
    """Raised when input data fails domain or business-rule validation (HTTP 400)."""

    def __init__(
        self,
        message: str = "Data validation error",
        error_code: str = "VALIDATION_ERROR",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message,
            status_code=400,
            error_code=error_code,
            details=details,
        )


class UnprocessableEntityError(AppException):
    """Raised when valid syntax cannot be processed due to business logic (HTTP 422)."""

    def __init__(
        self,
        message: str = "Cannot process entity (business logic violation)",
        error_code: str = "UNPROCESSABLE_ENTITY",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message, 422, error_code, details)


class OptimisticLockError(ConflictError):
    """Raised on aggregate version mismatch during optimistic locking (HTTP 409).

    Catches the ``sqlalchemy.orm.exc.StaleDataError`` that surfaces when a
    flushed UPDATE finds the row's ``version`` column has moved. Replaces a
    fan-out of 7+ near-identical ``*VersionConflictError`` classes that lived
    in catalog / cart / pricing domains (REC-031 D5 consolidation).

    Args:
        entity_type: Human-readable label, e.g. ``"Product"`` / ``"Cart"`` /
            ``"FormulaVersion"``.
        entity_id: The UUID of the contested aggregate.
        expected_version: Version the caller observed at the start of the
            transaction.
        actual_version: Version observed at flush time, or ``None`` when the
            row vanished between read and write.
    """

    def __init__(
        self,
        *,
        entity_type: str,
        entity_id: Any,
        expected_version: int,
        actual_version: int | None,
        error_code: str = "OPTIMISTIC_LOCK_CONFLICT",
    ) -> None:
        super().__init__(
            message=(
                f"Concurrent modification detected for {entity_type} {entity_id}."
            ),
            error_code=error_code,
            details={
                "entity_type": entity_type,
                "entity_id": str(entity_id),
                "expected_version": expected_version,
                "actual_version": actual_version,
            },
        )


class PreconditionFailedError(AppException):
    """Raised when ``If-Match`` header version doesn't match current state (HTTP 412).

    C4.1 — distinct from :class:`ConflictError` (409) so the front-end
    interceptor can distinguish "you read stale data, refetch and try
    again" from "the action you tried conflicts with current state for
    a different reason" (e.g. duplicate slug, duplicate idempotency key).

    The exception envelope carries ``expected_version`` /
    ``current_version`` so the UI can render a useful "version 5 → 7"
    diagnostic without an extra round-trip.
    """

    def __init__(
        self,
        *,
        entity_type: str,
        entity_id: Any,
        expected_version: int,
        current_version: int | None,
        error_code: str = "PRECONDITION_FAILED",
    ) -> None:
        super().__init__(
            message="Resource version has changed since you read it",
            status_code=412,
            error_code=error_code,
            details={
                "entity_type": entity_type,
                "entity_id": str(entity_id),
                "expected_version": expected_version,
                "current_version": current_version,
            },
        )


class ServiceUnavailableError(AppException):
    """Raised when an external service or dependency is unavailable (HTTP 503).

    Use for downstream failures we cannot remedy locally — S3/MinIO
    outages, payment-provider timeouts, third-party APIs returning
    unexpected errors. The presentation layer maps it to a 503 response
    so callers can retry with backoff.
    """

    def __init__(
        self,
        message: str = "Service temporarily unavailable",
        error_code: str = "SERVICE_UNAVAILABLE",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message, 503, error_code, details)


class SearchBackendError(ServiceUnavailableError):
    """Raised when the Elasticsearch backend is unreachable or returns 5xx (HTTP 503).

    Subclasses ``ServiceUnavailableError`` so the global error handler
    maps it to 503 with the standard envelope. Use for transient
    failures (connection refused, 502/503/504, cluster red, timeout) —
    the customer-facing search endpoint should retry or degrade
    gracefully (empty results + warning) rather than 500.
    """

    def __init__(
        self,
        message: str = "Search backend is temporarily unavailable",
        error_code: str = "SEARCH_BACKEND_UNAVAILABLE",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message=message, error_code=error_code, details=details)


class SearchIndexNotFoundError(NotFoundError):
    """Raised when a referenced Elasticsearch index does not exist (HTTP 404).

    Distinct from :class:`SearchBackendError` because the cluster is
    reachable — the index name is wrong (typo, missing alias, dropped
    by mistake). Surfaces to admin tooling so the operator can rebuild
    or re-attach the alias rather than treating it as a generic outage.
    """

    def __init__(
        self,
        *,
        index: str,
        message: str | None = None,
    ):
        super().__init__(
            message=message or f"Search index '{index}' not found",
            error_code="SEARCH_INDEX_NOT_FOUND",
            details={"index": index},
        )


class SearchConflictError(ConflictError):
    """Raised on Elasticsearch version conflict (409).

    Surfaces optimistic-concurrency failures from ES (``_version`` /
    ``if_seq_no`` mismatches) during single-doc updates. Typically the
    indexer should retry the operation by re-hydrating the source doc.
    """

    def __init__(
        self,
        *,
        index: str,
        doc_id: str,
        message: str | None = None,
    ):
        super().__init__(
            message=message or f"Search doc {doc_id!r} version conflict in {index!r}",
            error_code="SEARCH_DOC_CONFLICT",
            details={"index": index, "doc_id": doc_id},
        )


class SearchClientError(ValidationError):
    """Raised when ES returns a 4xx other than 404/409 (HTTP 400).

    Distinct from :class:`SearchBackendError` (which is 503 — *retryable
    transient outage*) because this is a **client-side bug**: malformed
    query, mapping mismatch, illegal field type, etc. Operator retry
    cannot help — the request itself needs developer attention. Mapping
    it to 400 makes the on-call alert ("4xx surge") meaningful and stops
    the indexer from looping the same broken document through TaskIQ
    retries.
    """

    def __init__(
        self,
        *,
        message: str,
        status: int,
        index: str | None = None,
    ):
        details: dict[str, Any] = {"status": status}
        if index is not None:
            details["index"] = index
        super().__init__(
            message=message,
            error_code="SEARCH_CLIENT_ERROR",
            details=details,
        )
