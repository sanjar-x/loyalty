"""Dependency injection container assembly.

Constructs the Dishka ``AsyncContainer`` by composing the framework-
level providers (``ConfigProvider``, ``DatabaseProvider``, ...) with
every bounded-context module's providers. The list of business
modules and their providers lives in :mod:`src.bootstrap.modules` —
this file is the single composition root that walks it.
"""

import structlog
from dishka import AsyncContainer, Provider, Scope, make_async_container, provide
from structlog import BoundLogger

from src.bootstrap.config import Settings, settings
from src.bootstrap.modules import MODULES
from src.infrastructure.cache.provider import CacheProvider
from src.infrastructure.database.provider import DatabaseProvider
from src.infrastructure.idempotency.provider import IdempotencyProvider
from src.infrastructure.logging.provider import LoggingProvider
from src.infrastructure.security.provider import SecurityProvider
from src.infrastructure.tracking.provider import TrackingProvider

logger: BoundLogger = structlog.get_logger(__name__)


class ConfigProvider(Provider):
    """Dishka provider that exposes application configuration objects."""

    @provide(scope=Scope.APP)
    def get_settings(self) -> Settings:
        """Provide the global ``Settings`` singleton."""
        return settings


def _framework_providers() -> tuple[Provider, ...]:
    """Cross-cutting infrastructure providers, in dependency order."""
    return (
        ConfigProvider(),
        LoggingProvider(),
        DatabaseProvider(),
        IdempotencyProvider(),
        CacheProvider(),
        TrackingProvider(),
        SecurityProvider(),
    )


def create_container() -> AsyncContainer:
    """Assemble and return the fully-configured Dishka IoC container."""
    logger.info("Initialising Dishka IoC container...")
    module_providers = tuple(p for m in MODULES for p in m.providers)
    return make_async_container(*_framework_providers(), *module_providers)
