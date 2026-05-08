"""Dishka IoC provider for the Image bounded context.

Wires:
- :class:`IStorageRepository` → :class:`StorageObjectRepository`
- :class:`IBlobStorage` → :class:`S3StorageService`

The :class:`AioBaseClient` (aiobotocore S3 client) is provided as
APP-scope so a single connection pool is shared across requests.
``S3StorageService`` itself is REQUEST-scope but cheap to construct —
it's a thin wrapper around the shared client.
"""

from collections.abc import AsyncIterator

from aiobotocore.client import AioBaseClient
from aiobotocore.session import get_session
from dishka import Provider, Scope, provide
from dishka.dependency_source.composite import CompositeDependencySource
from redis.asyncio.client import Redis

from src.bootstrap.config import Settings
from src.modules.image.application.commands.confirm_upload import ConfirmUploadHandler
from src.modules.image.application.commands.delete_storage_object import (
    DeleteStorageObjectHandler,
)
from src.modules.image.application.commands.import_external import (
    ImportExternalHandler,
)
from src.modules.image.application.commands.request_upload import RequestUploadHandler
from src.modules.image.application.commands.reupload import ReuploadHandler
from src.modules.image.domain.interfaces import IBlobStorage, IStorageRepository
from src.modules.image.infrastructure.repositories.storage_object_repository import (
    StorageObjectRepository,
)
from src.modules.image.infrastructure.services.s3_client import S3StorageService
from src.modules.image.infrastructure.services.sse_manager import SSEManager


class ImageProvider(Provider):
    """Wires storage repository, blob-storage client, S3 service, SSE manager."""

    storage_repo: CompositeDependencySource = provide(
        StorageObjectRepository,
        scope=Scope.REQUEST,
        provides=IStorageRepository,
    )

    delete_storage_object_handler: CompositeDependencySource = provide(
        DeleteStorageObjectHandler, scope=Scope.REQUEST
    )
    request_upload_handler: CompositeDependencySource = provide(
        RequestUploadHandler, scope=Scope.REQUEST
    )
    reupload_handler: CompositeDependencySource = provide(
        ReuploadHandler, scope=Scope.REQUEST
    )
    confirm_upload_handler: CompositeDependencySource = provide(
        ConfirmUploadHandler, scope=Scope.REQUEST
    )
    import_external_handler: CompositeDependencySource = provide(
        ImportExternalHandler, scope=Scope.REQUEST
    )

    @provide(scope=Scope.APP)
    async def s3_client(self, settings: Settings) -> AsyncIterator[AioBaseClient]:
        """Provide a long-lived aiobotocore S3 client.

        Uses ``aiobotocore.session.get_session()`` to construct an async
        client that pools connections. Yielded so Dishka can close it on
        shutdown via the async context-manager protocol.
        """
        session = get_session()
        async with session.create_client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT_URL or None,
            aws_access_key_id=settings.S3_ACCESS_KEY.get_secret_value(),
            aws_secret_access_key=settings.S3_SECRET_KEY.get_secret_value(),
            region_name=settings.S3_REGION,
        ) as client:
            yield client

    @provide(scope=Scope.REQUEST)
    def blob_storage(
        self, s3_client: AioBaseClient, settings: Settings
    ) -> IBlobStorage:
        """Wrap the shared client in S3StorageService for the request scope."""
        return S3StorageService(
            s3_client=s3_client,
            bucket_name=settings.S3_BUCKET_NAME,
        )

    @provide(scope=Scope.REQUEST)
    def sse_manager(self, redis: Redis) -> SSEManager:
        """SSEManager for media-status pub/sub (Redis-backed)."""
        return SSEManager(redis=redis)
