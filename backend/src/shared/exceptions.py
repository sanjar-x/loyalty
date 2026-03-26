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


