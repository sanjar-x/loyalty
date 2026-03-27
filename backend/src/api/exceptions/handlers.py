"""Centralised exception handlers for the FastAPI application.

Every handler converts its respective exception into a uniform JSON
error envelope so that API consumers always receive a consistent
response shape regardless of the error origin.
"""

import structlog
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from structlog.stdlib import BoundLogger

from src.shared.context import get_request_id
from src.shared.exceptions import AppException

logger: BoundLogger = structlog.get_logger("api.exceptions")


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handle application-level business exceptions.

    Logs the error at the appropriate severity (error for 5xx, warning
    otherwise) and returns a structured JSON response.

    Args:
        request: The incoming HTTP request.
        exc: The application exception raised during request processing.

    Returns:
        A JSON response containing the error code, message, and details.
    """
    log_method = logger.error if exc.status_code >= 500 else logger.warning
    log_method(
        "Business error",
        error_code=exc.error_code,
        status_code=exc.status_code,
        message=exc.message,
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "details": exc.details or {},
                "request_id": get_request_id(),
            }
        },
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle Pydantic / FastAPI request validation errors (422).

    Transforms the raw validation error list into a simplified structure
    that is easier for API consumers to parse.

    Args:
        request: The incoming HTTP request.
        exc: The validation exception containing one or more field errors.

    Returns:
        A 422 JSON response with per-field error details.
    """
    details = [
        {
            "field": ".".join(map(str, error["loc"])),
            "message": error["msg"],
            "type": error["type"],
        }
        for error in exc.errors()
    ]

    logger.warning("Schema validation error (422)", validation_errors=details)

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Input validation error.",
                "details": details,
                "request_id": get_request_id(),
            }
        },
    )


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """Handle standard Starlette/FastAPI HTTP exceptions.

    Ensures that the client always receives the uniform JSON error
    envelope, even for framework-raised HTTP errors (404, 405, etc.).

    Args:
        request: The incoming HTTP request.
        exc: The HTTP exception raised by the framework or application.

    Returns:
        A JSON response with the corresponding HTTP status code.
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": f"HTTP_ERROR_{exc.status_code}",
                "message": str(exc.detail),
                "details": {},
                "request_id": get_request_id(),
            }
        },
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler for unexpected server errors (500).

    Logs the full traceback at error level so that crashes are always
    observable, and returns a generic internal-error response to the
    client without leaking implementation details.

    Args:
        request: The incoming HTTP request.
        exc: The unhandled exception.

    Returns:
        A 500 JSON response with a generic error message.
    """
    logger.error(
        "Unhandled server exception (500)",
        exc_info=exc,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "Internal server error.",
                "details": {},
                "request_id": get_request_id(),
            }
        },
    )


def setup_exception_handlers(app: FastAPI) -> None:
    """Register all custom exception handlers on the FastAPI application.

    Args:
        app: The FastAPI application instance to configure.
    """
    app.add_exception_handler(AppException, app_exception_handler)  # ty:ignore[invalid-argument-type]
    app.add_exception_handler(
        RequestValidationError,
        validation_exception_handler,  # ty:ignore[invalid-argument-type]
    )
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)  # ty:ignore[invalid-argument-type]
    app.add_exception_handler(Exception, unhandled_exception_handler)
