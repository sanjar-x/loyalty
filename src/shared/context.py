# src\shared\context.py
import structlog


def get_request_id() -> str:
    """Получить текущий Request ID из контекста structlog."""
    context = structlog.contextvars.get_contextvars()
    return context.get("request_id", "UNKNOWN")
