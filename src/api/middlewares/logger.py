# src/api/middlewares/logger.py
import time
import uuid
from typing import Any

import structlog
from fastapi import Request
from starlette.datastructures import State
from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger: Any = structlog.get_logger("api.access")


class AccessLoggerMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        structlog.contextvars.clear_contextvars()

        request: Request[State] = Request(scope, receive=receive)
        await self.dispatch(request, receive, send)

    async def dispatch(self, request: Request, receive: Receive, send: Send) -> None:
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        ip: str = request.headers.get("X-Forwarded-For", "")
        if not ip:
            ip: str = request.client.host if request.client else "unknown"
        else:
            ip: str = ip.split(",")[0].strip()

        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            correlation_id=request_id,
            ip=ip,
            method=request.method,
            path=request.url.path,
        )

        start_time = time.perf_counter()
        status_code = 500
        duration_ms = 0.0

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code, duration_ms

            if message["type"] == "http.response.start":
                status_code = message.get("status", 500)
                duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

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

        except Exception as e:
            status_code = 500
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.exception("Unhandled exception during request processing")
            raise e

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
