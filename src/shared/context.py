# src/shared/context.py
from contextvars import ContextVar

_request_id_var: ContextVar[str] = ContextVar("request_id", default="UNKNOWN")


def get_request_id() -> str:
    """Получить текущий Request ID из контекста."""
    return _request_id_var.get()


def set_request_id(value: str) -> None:
    """Установить Request ID в контексте текущей корутины."""
    _request_id_var.set(value)
