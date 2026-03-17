"""ASGI middleware that produces structured access logs for every HTTP request.

Responsibilities:
- Generates or propagates a unique ``request_id`` for distributed tracing.
- Extracts the real client IP from ``X-Forwarded-For`` when behind a proxy.
- Binds contextual fields (request_id, IP, method, path) to structlog so
  that all downstream log entries include them automatically.
- Injects ``X-Process-Time-Ms`` and ``X-Request-ID`` response headers.
- Emits a single access-log line at the appropriate severity based on
  the final HTTP status code.
"""

import re
import time
import uuid

import structlog
from fastapi import Request
from starlette.datastructures import State
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from src.shared.context import set_request_id

logger: structlog.BoundLogger = structlog.get_logger("api.access")


class AccessLoggerMiddleware:
    """ASGI middleware that logs every HTTP request with timing and context."""

    def __init__(self, app: ASGIApp) -> None:
        """Initialise the middleware.

        Args:
            app: The next ASGI application in the middleware stack.
        """
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """ASGI entry point.

        Non-HTTP scopes (e.g. ``lifespan``, ``websocket``) are passed
        through without any logging.

        Args:
            scope: The ASGI connection scope.
            receive: The ASGI receive callable.
            send: The ASGI send callable.
        """
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        structlog.contextvars.clear_contextvars()

        request: Request[State] = Request(scope, receive=receive)
        await self.dispatch(request, receive, send)

    async def dispatch(self, request: Request, receive: Receive, send: Send) -> None:
        """Process a single HTTP request with logging and timing.

        The method resolves the request ID and client IP, binds them to
        the structlog context, wraps the ``send`` callable to capture the
        response status code and inject custom headers, and finally emits
        a single access-log entry.

        Args:
            request: The parsed Starlette ``Request`` object.
            receive: The ASGI receive callable.
            send: The ASGI send callable.
        """
        raw_request_id = request.headers.get("X-Request-ID", "")
        if raw_request_id and re.match(r"^[a-zA-Z0-9\-]{1,64}$", raw_request_id):
            request_id = raw_request_id
        else:
            request_id = uuid.uuid4().hex

        forwarded = request.headers.get("X-Forwarded-For", "")
        ip: str
        if forwarded:
            ip = forwarded.split(",")[0].strip()
        else:
            ip = request.client.host if request.client else "unknown"

        set_request_id(request_id)

        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            correlation_id=request_id,
            ip=ip,
            method=request.method,
            path=request.url.path,
        )

        start_time: int | float = time.perf_counter()
        status_code = 500
        duration_ms = 0.0

        async def send_wrapper(message: Message) -> None:
            """Intercept the response start message to capture status."""
            nonlocal status_code, duration_ms

            if message["type"] == "http.response.start":
                status_code = message.get("status", 500)
                duration_ms = round(number=(time.perf_counter() - start_time) * 1000, ndigits=2)

                existing_headers = list(message.get("headers", []))
                existing_headers.extend(
                    [
                        (b"x-process-time-ms", str(duration_ms).encode("latin1")),
                        (b"x-request-id", request_id.encode("latin1")),
                    ]
                )
                message["headers"] = existing_headers

            await send(message)

        try:
            await self.app(request.scope, receive, send_wrapper)

        except Exception:
            status_code = 500
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.exception("Unhandled exception during request processing")
            raise

        finally:
            if not duration_ms:
                duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

            if status_code >= 500:
                log_method = logger.error
            elif status_code >= 400:
                log_method = logger.warning
            else:
                log_method = logger.info

            log_method(
                "HTTP Request Handled",
                status=status_code,
                duration_ms=duration_ms,
            )
