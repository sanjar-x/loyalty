"""
Request-scoped context propagation via ContextVar.

Stores the current request ID in a coroutine-local variable so that
any layer (middleware, handler, repository) can access it without
explicit parameter threading. Part of the shared kernel.

Typical usage:
    from src.shared.context import get_request_id, set_request_id

    set_request_id("abc-123")
    current = get_request_id()  # "abc-123"
"""

from contextvars import ContextVar

_request_id_var: ContextVar[str] = ContextVar("request_id", default="UNKNOWN")


def get_request_id() -> str:
    """Return the current request ID from the coroutine-local context."""
    return _request_id_var.get()


def set_request_id(value: str) -> None:
    """Store a request ID in the coroutine-local context.

    Args:
        value: Opaque request identifier, typically from the
            ``X-Request-ID`` header or a generated UUID hex.
    """
    _request_id_var.set(value)
