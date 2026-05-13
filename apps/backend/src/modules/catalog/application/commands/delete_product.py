"""
Command handler: soft-delete a product.

Verifies the product exists, then marks it as soft-deleted via the
``Product.soft_delete()`` domain method. As a side-effect, all media
assets attached to the product are also detached and their storage
objects scheduled for cleanup via the same outbox chain that
``UpdateProductHandler`` uses (IMG-005).

Part of the application layer (CQRS write side).
"""

import uuid
from dataclasses import dataclass

from src.modules.catalog.domain.events import MediaAssetDetachedEvent
from src.modules.catalog.domain.exceptions import ProductNotFoundError
from src.modules.catalog.domain.interfaces import (
    IMediaAssetRepository,
    IProductRepository,
)
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class DeleteProductCommand:
    """Input for soft-deleting a product.

    Attributes:
        product_id: UUID of the product to soft-delete.
    """

    product_id: uuid.UUID


class DeleteProductHandler:
    """Soft-delete an existing product by ID + cascade media cleanup."""

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
        self._logger = logger.bind(handler="DeleteProductHandler")

    async def handle(self, command: DeleteProductCommand) -> None:
        """Execute the delete-product command.

        C2.1 — fixes the IMG-005 gap audited in
        ``docs/audit-media-lifecycle-2026-05.md``: prior to this, deleting
        a product soft-cascaded variants/SKUs but left ``media_assets``
        rows + their S3 keys orphaned. Now we list every media asset
        attached to the product, delete the row, and emit a
        ``MediaAssetDetachedEvent`` per asset so the existing
        ``cleanup_storage_after_detached`` consumer (IMG-005) cleans
        S3 + the ``storage_objects`` row asynchronously with the same
        retry / DLQ guarantees as the per-row update path.

        Raises:
            ProductNotFoundError: If the product does not exist.
        """
        async with self._uow:
            product = await self._product_repo.get_for_update_with_variants(
                command.product_id
            )
            if product is None:
                raise ProductNotFoundError(product_id=command.product_id)

            # Cascade media cleanup BEFORE the FSM mutation so the events
            # we emit travel in the same UoW commit. Iteration order does
            # not matter — each asset is independent.
            assets = await self._media_repo.list_by_product(command.product_id)
            for asset in assets:
                await self._media_repo.delete(asset.id)
                if asset.storage_object_id is not None:
                    product.add_domain_event(
                        MediaAssetDetachedEvent(
                            product_id=product.id,
                            storage_object_id=asset.storage_object_id,
                        )
                    )

            product.soft_delete()
            await self._product_repo.update(product)
            self._uow.register_aggregate(product)
            await self._uow.commit()

            self._logger.info(
                "product.soft_deleted",
                product_id=str(command.product_id),
                cascaded_media_count=len(assets),
            )
