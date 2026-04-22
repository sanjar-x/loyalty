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
from src.infrastructure.tracking.provider import TrackingProvider
from src.modules.activity.infrastructure.provider import ActivityProvider
from src.modules.cart.infrastructure.provider import CartProvider
from src.modules.catalog.presentation.dependencies import (
    AttributeGroupProvider,
    AttributeProvider,
    AttributeTemplateProvider,
    AttributeValueProvider,
    BrandProvider,
    CategoryProvider,
    MediaAssetProvider,
    ProductProvider,
    StorefrontCatalogProvider,
)
from src.modules.geo.presentation.dependencies import GeoProvider
from src.modules.identity.infrastructure.provider import IdentityProvider
from src.modules.logistics.infrastructure.provider import (
    LogisticsCommandProvider,
    LogisticsInfraProvider,
    LogisticsQueryProvider,
)
from src.modules.pricing.infrastructure.provider import PricingProvider
from src.modules.supplier.presentation.dependencies import SupplierProvider
from src.modules.user.infrastructure.provider import ProfileProvider

logger: BoundLogger = structlog.get_logger(__name__)


class ConfigProvider(Provider):
    """Dishka provider that exposes application configuration objects."""

    @provide(scope=Scope.APP)
    def get_settings(self) -> Settings:
        """Provide the global ``Settings`` singleton."""
        return settings


def create_container() -> AsyncContainer:
    """Assemble and return the fully-configured Dishka IoC container."""
    logger.info("Initialising Dishka IoC container...")
    return make_async_container(
        ConfigProvider(),
        LoggingProvider(),
        DatabaseProvider(),
        CacheProvider(),
        TrackingProvider(),
        SecurityProvider(),
        GeoProvider(),
        CategoryProvider(),
        BrandProvider(),
        AttributeGroupProvider(),
        AttributeProvider(),
        AttributeValueProvider(),
        AttributeTemplateProvider(),
        StorefrontCatalogProvider(),
        ProductProvider(),
        MediaAssetProvider(),
        IdentityProvider(),
        ProfileProvider(),
        SupplierProvider(),
        CartProvider(),
        LogisticsInfraProvider(),
        LogisticsCommandProvider(),
        LogisticsQueryProvider(),
        PricingProvider(),
        ActivityProvider(),
    )
