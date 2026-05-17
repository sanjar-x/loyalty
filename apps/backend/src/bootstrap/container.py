"""Dependency injection container assembly.

Constructs the Dishka ``AsyncContainer`` by composing all module-level
providers.  This is the single composition root for the entire
application -- both the web process and the background worker import
``create_container()`` from here.

Module providers are iterated from :data:`src.bootstrap.modules.MODULES`
so that adding a bounded context is a one-line change in
``src/bootstrap/modules.py`` -- nothing in this file needs to be
touched (REFACT-001 PR-5 / Rule 11).
"""

import structlog
from dishka import AsyncContainer, Provider, Scope, make_async_container, provide
from structlog import BoundLogger

from src.bootstrap.config import Settings, settings
from src.bootstrap.modules import MODULES
from src.infrastructure.cache.provider import CacheProvider
from src.infrastructure.database.provider import DatabaseProvider
from src.infrastructure.elasticsearch.provider import ElasticsearchProvider
from src.infrastructure.idempotency.provider import IdempotencyProvider
from src.infrastructure.logging.provider import LoggingProvider
from src.infrastructure.security.provider import SecurityProvider
from src.infrastructure.streams.provider import StreamsProvider
from src.infrastructure.tracking.provider import TrackingProvider

logger: BoundLogger = structlog.get_logger(__name__)


class ConfigProvider(Provider):
    """Dishka provider that exposes application configuration objects."""

    @provide(scope=Scope.APP)
    def get_settings(self) -> Settings:
        """Provide the global ``Settings`` singleton."""
        return settings


def _framework_providers() -> tuple[Provider, ...]:
    """Application-wide infrastructure providers (no module ownership).

    These wire cross-cutting concerns (config, logging, database, cache,
    idempotency kernel, observability, security) that every module
    depends on. Order matters where downstream providers reuse upstream
    bindings (LoggingProvider before everything; DatabaseProvider before
    repos; IdempotencyProvider before any module that consumes
    IIdempotencyStore / IInboxStore).
    """
    return (
        ConfigProvider(),
        LoggingProvider(),
        DatabaseProvider(),
        CacheProvider(),
        StreamsProvider(),
        IdempotencyProvider(),
        TrackingProvider(),
        SecurityProvider(),
        ElasticsearchProvider(),
    )


def create_container() -> AsyncContainer:
    """Assemble and return the fully-configured Dishka IoC container."""
    logger.info("Initialising Dishka IoC container...")
    framework = _framework_providers()
    module_providers = tuple(p for manifest in MODULES for p in manifest.providers)
    return make_async_container(*framework, *module_providers)
