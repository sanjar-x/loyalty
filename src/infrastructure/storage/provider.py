from collections.abc import AsyncIterable

import structlog
from aiobotocore.client import AioBaseClient
from dishka import Provider, Scope, provide

from src.bootstrap.config import settings
from src.infrastructure.storage.factory import S3ClientFactory
from src.infrastructure.storage.service import S3StorageService
from src.shared.interfaces.storage import IS3torageService

logger = structlog.get_logger(__name__)


class StorageProvider(Provider):
    @provide(scope=Scope.APP)
    def provide_s3_factory(self) -> S3ClientFactory:
        """
        Фабрика живет как Singleton (APP scope).
        Она просто хранит настройки и AioSession.
        """
        logger.info("Инициализация фабрики S3ClientFactory...")
        return S3ClientFactory(
            access_key=settings.S3_ACCESS_KEY,
            secret_key=settings.S3_SECRET_KEY,
            region=settings.S3_REGION,
            endpoint_url=settings.S3_ENDPOINT_URL,
        )

    @provide(scope=Scope.REQUEST)
    async def provide_s3_client(
        self, factory: S3ClientFactory
    ) -> AsyncIterable[AioBaseClient]:
        """
        Создает одноразовое TCP-соединение (REQUEST scope).
        dishka вызовет этот метод при начале запроса, дождется yield,
        а в конце запроса продолжит выполнение и закроет ресурсы.
        """
        logger.debug("Запрос S3 клиента у фабрики")
        async for client in factory.create_client():
            yield client
        logger.debug("Работа с S3 завершена")

    @provide(scope=Scope.REQUEST)
    def provide_storage_service(self, client: AioBaseClient) -> IS3torageService:
        """
        Собирает финальный сервис под интерфейсом IStorageService.
        Внедряется в хэндлеры FastAPI.
        """
        logger.debug("Инициализация S3StorageService")
        return S3StorageService(
            s3_client=client,
            bucket_name=settings.S3_BUCKET_NAME,
        )
