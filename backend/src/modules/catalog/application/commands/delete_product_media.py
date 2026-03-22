"""
Command handler: delete a product media asset.

Removes the MediaAsset DB record and attempts to clean up the associated raw
S3 object (if present). S3 deletion errors are swallowed so that a missing
or already-deleted object does not block the database record removal.
Part of the application layer (CQRS write side).
"""

import uuid
from dataclasses import dataclass

from src.modules.catalog.domain.interfaces import IMediaAssetRepository
from src.shared.exceptions import NotFoundError
from src.shared.interfaces.blob_storage import IBlobStorage
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
    """Delete a product media asset and clean up its raw S3 object."""

    def __init__(
        self,
        media_repo: IMediaAssetRepository,
        blob_storage: IBlobStorage,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._media_repo = media_repo
        self._blob = blob_storage
        self._uow = uow
        self._logger = logger.bind(handler="DeleteProductMediaHandler")

    async def handle(self, cmd: DeleteProductMediaCommand) -> None:
        """Execute the delete-product-media command.

        Args:
            cmd: Deletion parameters.

        Raises:
            NotFoundError: If the media asset does not exist.
        """
        # Load the record first (outside transaction) to get the raw_object_key
        # so we know what to clean up in S3 after the DB delete
        media = await self._media_repo.get(cmd.media_id)
        if media is None:
            raise NotFoundError(f"Media {cmd.media_id} not found")

        if media.product_id != cmd.product_id:
            raise NotFoundError(f"Media {cmd.media_id} not found for product {cmd.product_id}")

        raw_object_key = media.raw_object_key
        public_url = media.public_url
        is_external = media.is_external

        # Delete the DB record atomically
        async with self._uow:
            await self._media_repo.delete(cmd.media_id)
            await self._uow.commit()

        # Best-effort S3 cleanup — errors are logged but do not propagate
        if raw_object_key:
            try:
                await self._blob.delete_object(raw_object_key)
            except Exception:  # noqa: BLE001
                self._logger.warning(
                    "Failed to delete raw S3 object during media deletion",
                    raw_object_key=raw_object_key,
                    media_id=str(cmd.media_id),
                )

        # Best-effort cleanup of the processed S3 object (if any)
        if public_url is not None and not is_external:
            # Extract S3 key from the public URL (everything after the bucket base)
            processed_key = public_url.split("/", 3)[-1] if "/" in public_url else public_url
            try:
                await self._blob.delete_object(processed_key)
            except Exception:  # noqa: BLE001
                self._logger.warning(
                    "Failed to delete processed S3 object during media deletion",
                    processed_key=processed_key,
                    media_id=str(cmd.media_id),
                )

        self._logger.info(
            "Media asset deleted",
            media_id=str(cmd.media_id),
            product_id=str(cmd.product_id),
        )
