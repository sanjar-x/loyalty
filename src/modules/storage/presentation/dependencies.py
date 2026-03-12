# src/modules/storage/presentation/dependencies.py
from collections.abc import AsyncIterable

import structlog
from aiobotocore.client import AioBaseClient
from dishka import Provider, Scope, provide

from src.bootstrap.config import Settings
from src.infrastructure.storage.factory import S3ClientFactory
from src.modules.storage.domain.interfaces import IStorageRepository
from src.modules.storage.infrastructure.repository import StorageObjectRepository
from src.modules.storage.infrastructure.service import S3StorageService
from src.shared.interfaces.storage import IS3torageService

logger = structlog.get_logger(__name__)


class StorageProvider(Provider):
    @provide(scope=Scope.APP)
    def s3_factory(self, settings: Settings) -> S3ClientFactory:
        return S3ClientFactory(
            access_key=settings.S3_ACCESS_KEY,
            secret_key=settings.S3_SECRET_KEY,
            region=settings.S3_REGION,
            endpoint_url=settings.S3_ENDPOINT_URL,
        )

    @provide(scope=Scope.REQUEST)
    async def s3_client(self, factory: S3ClientFactory) -> AsyncIterable[AioBaseClient]:
        async for client in factory.create_client():
            yield client

    # Здесь для красоты и idiomatic Dishka можно использовать атрибут класса:
    storage_repo = provide(
        StorageObjectRepository, scope=Scope.REQUEST, provides=IStorageRepository
    )

    @provide(scope=Scope.REQUEST)
    def storage_service(
        self, client: AioBaseClient, settings: Settings
    ) -> IS3torageService:
        # Снова просим Dishka прокинуть Settings в аргументы
        return S3StorageService(
            s3_client=client,
            bucket_name=settings.S3_BUCKET_NAME,
        )
