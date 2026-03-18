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
    AttributeProvider,
    AttributeValueProvider,
    BrandProvider,
    CategoryAttributeBindingProvider,
    CategoryProvider,
    ProductProvider,
    StorefrontCatalogProvider,
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
        """Provide the global ``Settings`` singleton."""
        return settings

    @provide(scope=Scope.APP)
    def get_storage_config(self, s: Settings) -> IStorageConfig:
        """Provide the storage configuration interface."""
        return s


def create_container() -> AsyncContainer:
    """Assemble and return the fully-configured Dishka IoC container."""
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
        AttributeProvider(),
        AttributeValueProvider(),
        CategoryAttributeBindingProvider(),
        StorefrontCatalogProvider(),
        ProductProvider(),
        IdentityProvider(),
        UserProvider(),
    )
