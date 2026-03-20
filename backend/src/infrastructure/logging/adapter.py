"""Structlog adapter implementing the ILogger port.

Wraps ``structlog.BoundLogger`` behind the ``ILogger`` protocol so that
the application layer depends only on the abstract interface, not on
structlog directly.
"""

from __future__ import annotations

from typing import Any

import structlog

from src.shared.interfaces.logger import ILogger


class StructlogAdapter(ILogger):
    """Adapter that bridges ``structlog.BoundLogger`` to the ``ILogger`` protocol."""

    __slots__ = ("_logger",)

    def __init__(self, name: str) -> None:
        """Create an adapter wrapping a new structlog logger.

        Args:
            name: The logger name passed to ``structlog.get_logger``.
        """
        self._logger: structlog.stdlib.BoundLogger = structlog.get_logger(name)

    @classmethod
    def _from_bound(cls, bound_logger: structlog.stdlib.BoundLogger) -> StructlogAdapter:
        """Create an adapter from an already-bound logger (used by ``bind``).

        Args:
            bound_logger: A pre-configured bound logger instance.

        Returns:
            A new ``StructlogAdapter`` wrapping the given bound logger.
        """
        instance = cls.__new__(cls)
        instance._logger = bound_logger
        return instance

    def bind(self, **kwargs: Any) -> StructlogAdapter:
        """Return a new adapter with additional context variables bound.

        Args:
            **kwargs: Key-value pairs to bind to the logger context.

        Returns:
            A new ``StructlogAdapter`` with the bound context.
        """
        return StructlogAdapter._from_bound(self._logger.bind(**kwargs))

    def debug(self, event: str, **kwargs: Any) -> None:
        """Log a message at DEBUG level.

        Args:
            event: The log event message.
            **kwargs: Additional structured context.
        """
        self._logger.debug(event, **kwargs)

    def info(self, event: str, **kwargs: Any) -> None:
        """Log a message at INFO level.

        Args:
            event: The log event message.
            **kwargs: Additional structured context.
        """
        self._logger.info(event, **kwargs)

    def warning(self, event: str, **kwargs: Any) -> None:
        """Log a message at WARNING level.

        Args:
            event: The log event message.
            **kwargs: Additional structured context.
        """
        self._logger.warning(event, **kwargs)

    def error(self, event: str, **kwargs: Any) -> None:
        """Log a message at ERROR level.

        Args:
            event: The log event message.
            **kwargs: Additional structured context.
        """
        self._logger.error(event, **kwargs)

    def critical(self, event: str, **kwargs: Any) -> None:
        """Log a message at CRITICAL level.

        Args:
            event: The log event message.
            **kwargs: Additional structured context.
        """
        self._logger.critical(event, **kwargs)

    def exception(self, event: str, **kwargs: Any) -> None:
        """Log a message at ERROR level with exception info.

        Args:
            event: The log event message.
            **kwargs: Additional structured context.
        """
        self._logger.exception(event, **kwargs)
