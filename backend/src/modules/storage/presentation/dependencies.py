"""Storage dependency injection providers.

Configures the Dishka DI container with all providers required by the
Storage module: S3 client factory, blob storage service, repository,
and the storage facade.
"""

from collections.abc import AsyncIterable

from aiobotocore.client import AioBaseClient
from dishka import Provider, Scope, provide

from src.bootstrap.config import Settings
from src.infrastructure.storage.factory import S3ClientFactory
from src.modules.storage.domain.interfaces import IStorageRepository
from src.modules.storage.infrastructure.repository import StorageObjectRepository
from src.modules.storage.infrastructure.service import S3StorageService
from src.modules.storage.presentation.facade import StorageFacade
from src.shared.interfaces.blob_storage import IBlobStorage
from src.shared.interfaces.storage import IStorageFacade


class StorageProvider(Provider):
    """Dishka provider that wires all Storage module dependencies.

    Registers the S3 client factory (app-scoped), per-request S3 client,
    repository, blob storage service, and the storage facade.
    """

    @provide(scope=Scope.APP)
    def s3_factory(self, settings: Settings) -> S3ClientFactory:
        """Create a singleton S3 client factory from application settings.

        Args:
            settings: Application configuration containing S3 credentials.

        Returns:
            A configured ``S3ClientFactory`` instance.
        """
        return S3ClientFactory(
            access_key=settings.S3_ACCESS_KEY.get_secret_value(),
            secret_key=settings.S3_SECRET_KEY.get_secret_value(),
            region=settings.S3_REGION,
            endpoint_url=settings.S3_ENDPOINT_URL,
        )

    @provide(scope=Scope.REQUEST)
    async def s3_client(self, factory: S3ClientFactory) -> AsyncIterable[AioBaseClient]:
        """Yield a per-request S3 client from the factory.

        Args:
            factory: The application-scoped S3 client factory.

        Yields:
            An ``AioBaseClient`` instance for S3 operations.
        """
        async for client in factory.create_client():
            yield client

    storage_repo = provide(
        StorageObjectRepository, scope=Scope.REQUEST, provides=IStorageRepository
    )

    @provide(scope=Scope.REQUEST)
    def storage_service(
        self, client: AioBaseClient, settings: Settings
    ) -> IBlobStorage:
        """Create a per-request S3 storage service.

        Args:
            client: The S3 client for this request.
            settings: Application configuration containing the bucket name.

        Returns:
            An ``S3StorageService`` implementing ``IBlobStorage``.
        """
        return S3StorageService(
            s3_client=client,
            bucket_name=settings.S3_BUCKET_NAME,
        )

    storage_facade = provide(
        StorageFacade, scope=Scope.REQUEST, provides=IStorageFacade
    )
