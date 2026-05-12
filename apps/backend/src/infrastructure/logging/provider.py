"""Dishka dependency provider for the logging infrastructure.

Supplies the ``ILogger`` port through the IoC container, allowing the
application layer to receive a logger via dependency injection rather
than importing structlog directly.
"""

from dishka import Provider, Scope, provide

from src.infrastructure.logging.adapter import StructlogAdapter
from src.shared.interfaces.logger import ILogger


class LoggingProvider(Provider):
    """Dishka provider that binds ``ILogger`` to the structlog adapter."""

    @provide(scope=Scope.REQUEST)
    def get_logger(self) -> ILogger:
        """Create a request-scoped logger instance.

        Returns:
            An ``ILogger`` implementation backed by structlog.
        """
        return StructlogAdapter("app")
