# src\shared\context.py
from typing import Any

import structlog


def get_request_id() -> str:
    """Получить текущий Request ID из контекста structlog."""
    context: dict[str, Any] = structlog.contextvars.get_contextvars()
    return context.get("request_id", "UNKNOWN")
