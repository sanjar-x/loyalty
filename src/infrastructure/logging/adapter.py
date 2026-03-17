# src/infrastructure/logging/adapter.py
"""
Адаптер structlog → ILogger (Инфраструктурная деталь).

Реализует порт ILogger, оборачивая structlog.BoundLogger.
Application Layer не знает о structlog — только о Protocol ILogger.
"""

from __future__ import annotations

from typing import Any

import structlog

from src.shared.interfaces.logger import ILogger


class StructlogAdapter(ILogger):
    """Адаптер: structlog.BoundLogger → ILogger Protocol."""

    __slots__ = ("_logger",)

    def __init__(self, name: str) -> None:
        self._logger: structlog.stdlib.BoundLogger = structlog.get_logger(name)

    @classmethod
    def _from_bound(cls, bound_logger: structlog.stdlib.BoundLogger) -> StructlogAdapter:
        """Создаёт адаптер из уже привязанного логгера (для .bind())."""
        instance = cls.__new__(cls)
        instance._logger = bound_logger
        return instance

    def bind(self, **kwargs: Any) -> StructlogAdapter:
        return StructlogAdapter._from_bound(self._logger.bind(**kwargs))

    def debug(self, event: str, **kwargs: Any) -> None:
        self._logger.debug(event, **kwargs)

    def info(self, event: str, **kwargs: Any) -> None:
        self._logger.info(event, **kwargs)

    def warning(self, event: str, **kwargs: Any) -> None:
        self._logger.warning(event, **kwargs)

    def error(self, event: str, **kwargs: Any) -> None:
        self._logger.error(event, **kwargs)

    def exception(self, event: str, **kwargs: Any) -> None:
        self._logger.exception(event, **kwargs)
