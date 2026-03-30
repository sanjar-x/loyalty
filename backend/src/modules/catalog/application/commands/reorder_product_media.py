"""
Command handler: bulk-reorder media assets for a product.

Accepts a list of (media_id, sort_order) pairs and updates all
assets' ``sort_order`` in a single statement via CASE/WHEN.
"""

import uuid
from dataclasses import dataclass

from src.modules.catalog.domain.exceptions import MediaAssetNotFoundError
from src.modules.catalog.domain.interfaces import IMediaAssetRepository
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class ReorderItem:
    """A single media asset reorder instruction."""

    media_id: uuid.UUID
    sort_order: int


@dataclass(frozen=True)
class ReorderProductMediaCommand:
    """Input for bulk-reordering media assets.

    Attributes:
        product_id: UUID of the parent product (ownership check).
        items: List of (media_id, sort_order) pairs.
    """

    product_id: uuid.UUID
    items: list[ReorderItem]


class ReorderProductMediaHandler:
    """Bulk-update sort_order for media assets belonging to one product."""

    def __init__(
        self,
        media_repo: IMediaAssetRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._media_repo = media_repo
        self._uow = uow
        self._logger = logger.bind(handler="ReorderProductMediaHandler")

    async def handle(self, command: ReorderProductMediaCommand) -> None:
        """Execute the reorder-product-media command."""
        async with self._uow:
            updates = [(item.media_id, item.sort_order) for item in command.items]
            updated = await self._media_repo.bulk_update_sort_order(
                command.product_id, updates
            )
            if updated < len(updates):
                # Some media_ids did not belong to this product or don't exist
                raise MediaAssetNotFoundError(
                    media_id="(bulk reorder)",
                    product_id=command.product_id,
                )
            await self._uow.commit()
