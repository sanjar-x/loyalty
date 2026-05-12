"""
Logging port (Hexagonal Architecture).

Application and presentation layers depend **only** on this protocol.
The concrete implementation (structlog, loguru, stdlib) is an
infrastructure detail injected via the Dishka IoC container.

Typical usage:
    class CreateOrderHandler:
        def __init__(self, logger: ILogger) -> None:
            self._log = logger.bind(handler="CreateOrderHandler")
"""

from __future__ import annotations

from typing import Any, Protocol


class ILogger(Protocol):
    """Abstract logger for application and presentation layers."""

    def bind(self, **kwargs: Any) -> ILogger:
        """Return a new logger instance with additional bound context.

        Args:
            **kwargs: Key-value pairs added to every subsequent log entry.

        Returns:
            A new ``ILogger`` instance carrying the merged context.
        """
        ...

    def debug(self, event: str, **kwargs: Any) -> None:
        """Emit a DEBUG-level log entry.

        Args:
            event: Human-readable event description.
            **kwargs: Structured fields attached to the entry.
        """
        ...

    def info(self, event: str, **kwargs: Any) -> None:
        """Emit an INFO-level log entry.

        Args:
            event: Human-readable event description.
            **kwargs: Structured fields attached to the entry.
        """
        ...

    def warning(self, event: str, **kwargs: Any) -> None:
        """Emit a WARNING-level log entry.

        Args:
            event: Human-readable event description.
            **kwargs: Structured fields attached to the entry.
        """
        ...

    def error(self, event: str, **kwargs: Any) -> None:
        """Emit an ERROR-level log entry.

        Args:
            event: Human-readable event description.
            **kwargs: Structured fields attached to the entry.
        """
        ...

    def critical(self, event: str, **kwargs: Any) -> None:
        """Emit a CRITICAL-level log entry.

        Args:
            event: Human-readable event description.
            **kwargs: Structured fields attached to the entry.
        """
        ...

    def exception(self, event: str, **kwargs: Any) -> None:
        """Emit an ERROR-level log entry with the current exception traceback.

        Args:
            event: Human-readable event description.
            **kwargs: Structured fields attached to the entry.
        """
        ...
