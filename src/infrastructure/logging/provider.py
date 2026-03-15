# src/infrastructure/logging/provider.py
"""
Dishka Provider для логгера.

Предоставляет ILogger через IoC-контейнер, позволяя Application Layer
получать логгер через DI вместо глобального import structlog.
"""

from dishka import Provider, Scope, provide

from src.infrastructure.logging.adapter import StructlogAdapter
from src.shared.interfaces.logger import ILogger


class LoggingProvider(Provider):
    @provide(scope=Scope.REQUEST)
    def get_logger(self) -> ILogger:
        return StructlogAdapter("app")
