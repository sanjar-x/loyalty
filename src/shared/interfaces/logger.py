# src/shared/interfaces/logger.py
"""
Порт логирования (Hexagonal Architecture).

Application Layer зависит ТОЛЬКО от этого протокола.
Конкретная реализация (structlog, loguru, stdlib) — деталь инфраструктуры,
инжектируемая через Dishka IoC-контейнер.
"""

from __future__ import annotations

from typing import Any, Protocol


class ILogger(Protocol):
    """Абстракция логгера для Application и Presentation слоёв."""

    def bind(self, **kwargs: Any) -> ILogger:
        """Возвращает новый экземпляр логгера с привязанным контекстом."""
        ...

    def debug(self, event: str, **kwargs: Any) -> None: ...
    def info(self, event: str, **kwargs: Any) -> None: ...
    def warning(self, event: str, **kwargs: Any) -> None: ...
    def error(self, event: str, **kwargs: Any) -> None: ...
    def exception(self, event: str, **kwargs: Any) -> None: ...
