# src/bootstrap/ioc.py
import structlog
from dishka import AsyncContainer, Provider, Scope, make_async_container, provide
from structlog import BoundLogger

from src.bootstrap.config import Settings, settings
from src.infrastructure.cache.provider import CacheProvider
from src.infrastructure.database.provider import DatabaseProvider
from src.infrastructure.logging.provider import LoggingProvider
from src.infrastructure.security.provider import SecurityProvider
from src.modules.catalog.presentation.dependencies import (
    BrandProvider,
    CategoryProvider,
)
from src.modules.storage.presentation.dependencies import StorageProvider

logger: BoundLogger = structlog.get_logger(__name__)


class ConfigProvider(Provider):
    @provide(scope=Scope.APP)
    def get_settings(self) -> Settings:
        return settings


def create_container() -> AsyncContainer:
    logger.info("Инициализация IoC контейнера Dishka...")
    return make_async_container(
        ConfigProvider(),
        LoggingProvider(),
        DatabaseProvider(),
        CacheProvider(),
        SecurityProvider(),
        StorageProvider(),
        CategoryProvider(),
        BrandProvider(),
    )
