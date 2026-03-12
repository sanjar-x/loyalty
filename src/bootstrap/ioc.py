import structlog
from dishka import AsyncContainer, Provider, Scope, make_async_container, provide
from structlog import BoundLogger

from src.bootstrap.config import Settings, settings
from src.infrastructure.cache.provider import CacheProvider
from src.infrastructure.database.provider import DatabaseProvider
from src.modules.catalog.presentation.dependencies import CategoryProvider

logger: BoundLogger = structlog.get_logger(__name__)


class ConfigProvider(Provider):
    @provide(scope=Scope.APP)
    def provide_settings(self) -> Settings:
        return settings


def create_container() -> AsyncContainer:
    logger.info("Инициализация IoC контейнера...")
    return make_async_container(
        ConfigProvider(), DatabaseProvider(), CacheProvider(), CategoryProvider()
    )
