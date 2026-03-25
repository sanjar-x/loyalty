"""
Command handler: delete a product media asset.

Deletes the MediaAsset DB record and performs a best-effort cleanup call to
ImageBackend (if a storage_object_id is present).
Part of the application layer (CQRS write side).
"""

import uuid
from dataclasses import dataclass

from src.modules.catalog.domain.exceptions import MediaAssetNotFoundError
from src.modules.catalog.domain.interfaces import IMediaAssetRepository
from src.modules.catalog.infrastructure.image_backend_client import ImageBackendClient
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class DeleteProductMediaCommand:
    """Input for deleting a product media asset.

    Attributes:
        product_id: UUID of the owning product (used for ownership validation).
        media_id: UUID of the MediaAsset to delete.
    """

    product_id: uuid.UUID
    media_id: uuid.UUID


class DeleteProductMediaHandler:
    """Delete a product media asset and clean up via ImageBackend."""

    def __init__(
        self,
        media_repo: IMediaAssetRepository,
        uow: IUnitOfWork,
        image_backend: ImageBackendClient,
        logger: ILogger,
    ) -> None:
        self._media_repo = media_repo
        self._uow = uow
        self._image_backend = image_backend
        self._logger = logger.bind(handler="DeleteProductMediaHandler")

    async def handle(self, command: DeleteProductMediaCommand) -> None:
        """Execute the delete-product-media command.

        Args:
            command: Deletion parameters.

        Raises:
            MediaAssetNotFoundError: If the media asset does not exist.
        """
        media = await self._media_repo.get(command.media_id)
        if media is None:
            raise MediaAssetNotFoundError(media_id=command.media_id)

        if media.product_id != command.product_id:
            raise MediaAssetNotFoundError(
                media_id=command.media_id, product_id=command.product_id
            )

        storage_object_id = media.storage_object_id

        await self._media_repo.delete(command.media_id)
        await self._uow.commit()

        # Best-effort ImageBackend cleanup (delete() swallows errors internally)
        if storage_object_id:
            await self._image_backend.delete(storage_object_id)

        self._logger.info(
            "Media asset deleted",
            media_id=str(command.media_id),
            product_id=str(command.product_id),
        )
