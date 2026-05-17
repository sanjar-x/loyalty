"""
Command handler: delete a product media asset.

IMG-005 contract: catalog writes the DB delete AND emits
:class:`MediaAssetDetachedEvent` to the outbox in **one** UoW. The
``cleanup_storage_after_detached`` TaskIQ consumer drives the actual
S3 + ``storage_objects`` cleanup with retry / DLQ.

A prior version of this handler did the cleanup in-process **after**
``uow.commit()`` via an injected ``IMediaCleanupPort`` — a crash
between commit and that ``await`` left the media row gone but the S3
key + ``storage_objects`` row orphaned forever (the periodic sweeper
only chases ``PENDING_UPLOAD``, not ``COMPLETED``). The handler now
mirrors the cascade pattern used by ``DeleteProductHandler``.
"""

import uuid
from dataclasses import dataclass

from src.modules.catalog.domain.events import MediaAssetDetachedEvent
from src.modules.catalog.domain.exceptions import (
    MediaAssetNotFoundError,
    ProductNotFoundError,
)
from src.modules.catalog.domain.interfaces import (
    IMediaAssetRepository,
    IProductRepository,
)
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
    """Delete a media asset and queue storage cleanup via the outbox."""

    def __init__(
        self,
        product_repo: IProductRepository,
        media_repo: IMediaAssetRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._product_repo = product_repo
        self._media_repo = media_repo
        self._uow = uow
        self._logger = logger.bind(handler="DeleteProductMediaHandler")

    async def handle(self, command: DeleteProductMediaCommand) -> None:
        """Execute the delete-product-media command.

        Raises:
            MediaAssetNotFoundError: If the media asset does not exist or
                does not belong to ``product_id``.
            ProductNotFoundError: If the owning product cannot be loaded
                (needed as the aggregate root that carries the detach
                event into the outbox).
        """
        async with self._uow:
            media = await self._media_repo.get_for_update(command.media_id)
            if media is None:
                raise MediaAssetNotFoundError(media_id=command.media_id)

            if media.product_id != command.product_id:
                raise MediaAssetNotFoundError(
                    media_id=command.media_id, product_id=command.product_id
                )

            # Aggregate root is the carrier for the detach event so the
            # outbox sees it in the same commit as the DB delete. No
            # FOR UPDATE — media delete does not bump ``product.version``,
            # and the ownership check above is enough to keep the request
            # scoped to the correct aggregate.
            product = await self._product_repo.get(command.product_id)
            if product is None:  # pragma: no cover — FK guarantees existence
                raise ProductNotFoundError(product_id=command.product_id)

            storage_object_id = media.storage_object_id
            await self._media_repo.delete(command.media_id)

            if storage_object_id is not None:
                # IMG-005 — storage cleanup runs via outbox →
                # ``cleanup_storage_after_detached`` consumer (retry / DLQ).
                product.add_domain_event(
                    MediaAssetDetachedEvent(
                        product_id=product.id,
                        storage_object_id=storage_object_id,
                    )
                )

            self._uow.register_aggregate(product)
            await self._uow.commit()

        self._logger.info(
            "Media asset deleted",
            media_id=str(command.media_id),
            product_id=str(command.product_id),
            storage_object_id=(str(storage_object_id) if storage_object_id else None),
        )
