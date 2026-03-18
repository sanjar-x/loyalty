"""Dependency injection container assembly.

Constructs the Dishka ``AsyncContainer`` by composing all module-level
providers.  This is the single composition root for the entire
application -- both the web process and the background worker import
``create_container()`` from here.
"""

import structlog
from dishka import AsyncContainer, Provider, Scope, make_async_container, provide
from structlog import BoundLogger

from src.bootstrap.config import Settings, settings
from src.infrastructure.cache.provider import CacheProvider
from src.infrastructure.database.provider import DatabaseProvider
from src.infrastructure.logging.provider import LoggingProvider
from src.infrastructure.security.provider import SecurityProvider
from src.modules.catalog.presentation.dependencies import (
    AttributeGroupProvider,
    BrandProvider,
    CategoryProvider,
)
from src.modules.identity.infrastructure.provider import IdentityProvider
from src.modules.storage.presentation.dependencies import StorageProvider
from src.modules.user.infrastructure.provider import UserProvider
from src.shared.interfaces.config import IStorageConfig

logger: BoundLogger = structlog.get_logger(__name__)


class ConfigProvider(Provider):
    """Dishka provider that exposes application configuration objects."""

    @provide(scope=Scope.APP)
    def get_settings(self) -> Settings:
        """Provide the global ``Settings`` singleton.

        Returns:
            The application settings instance.
        """
        return settings

    @provide(scope=Scope.APP)
    def get_storage_config(self, s: Settings) -> IStorageConfig:
        """Provide the storage configuration interface.

        Args:
            s: The application settings (implements ``IStorageConfig``).

        Returns:
            The storage configuration, backed by the same settings object.
        """
        return s


def create_container() -> AsyncContainer:
    """Assemble and return the fully-configured Dishka IoC container.

    All infrastructure and module providers are registered here so that
    any ``FromDishka[...]`` dependency can be resolved at request time.

    Returns:
        A ready-to-use ``AsyncContainer`` instance.
    """
    logger.info("Initialising Dishka IoC container...")
    return make_async_container(
        ConfigProvider(),
        LoggingProvider(),
        DatabaseProvider(),
        CacheProvider(),
        SecurityProvider(),
        StorageProvider(),
        CategoryProvider(),
        BrandProvider(),
        AttributeGroupProvider(),
        IdentityProvider(),
        UserProvider(),
    )
