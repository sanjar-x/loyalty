"""
Command handler: bulk-reorder media assets for a product.

Accepts a list of (media_id, sort_order) pairs and updates all
assets' ``sort_order`` in a single statement via CASE/WHEN.
"""

import uuid
from dataclasses import dataclass

from src.modules.catalog.application.constants import storefront_pdp_cache_key
from src.modules.catalog.domain.interfaces import (
    IMediaAssetRepository,
    IProductRepository,
)
from src.shared.exceptions import ValidationError
from src.shared.interfaces.cache import ICacheService
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
        product_repo: IProductRepository,
        uow: IUnitOfWork,
        cache: ICacheService,
        logger: ILogger,
    ) -> None:
        self._media_repo = media_repo
        self._product_repo = product_repo
        self._uow = uow
        self._cache = cache
        self._logger = logger.bind(handler="ReorderProductMediaHandler")

    async def handle(self, command: ReorderProductMediaCommand) -> None:
        """Execute the reorder-product-media command.

        Raises:
            ValidationError (400):
              * ``REORDER_DUPLICATE_MEDIA_ID`` — the payload lists the
                same ``media_id`` more than once. SQL ``CASE/WHEN`` would
                silently pick a single branch and the caller's intent
                would be lost; reject up front.
              * ``REORDER_UNKNOWN_MEDIA_IDS`` — at least one
                ``media_id`` does not belong to ``product_id`` (or does
                not exist). Caller gets the offending UUIDs back in
                ``details`` for surfacing in the UI.
        """
        # --- Reject duplicate media_ids before touching the DB. ---
        # ``bulk_update_sort_order`` collapses duplicates to whichever
        # CASE branch the engine evaluates last, silently dropping the
        # caller's other intents. The contract is "one decision per id".
        seen: set[uuid.UUID] = set()
        duplicates: list[uuid.UUID] = []
        for item in command.items:
            if item.media_id in seen:
                duplicates.append(item.media_id)
            else:
                seen.add(item.media_id)
        if duplicates:
            raise ValidationError(
                message=(
                    "Reorder payload contains duplicate media_id entries; "
                    "each media asset may appear at most once."
                ),
                error_code="REORDER_DUPLICATE_MEDIA_ID",
                details={"duplicate_media_ids": [str(d) for d in duplicates]},
            )

        async with self._uow:
            updates = [(item.media_id, item.sort_order) for item in command.items]
            updated = await self._media_repo.bulk_update_sort_order(
                command.product_id, updates
            )
            if updated < len(updates):
                # Surface the un-matched id set so the caller can fix
                # the request instead of guessing. ``MediaAssetNotFoundError``
                # used to be raised with ``media_id="(bulk reorder)"``
                # which violates its ``uuid.UUID`` field contract.
                raise ValidationError(
                    message=(
                        "Some media_id entries do not belong to this product "
                        "or do not exist; reorder rejected."
                    ),
                    error_code="REORDER_UNKNOWN_MEDIA_IDS",
                    details={
                        "product_id": str(command.product_id),
                        "requested_count": len(updates),
                        "matched_count": updated,
                    },
                )
            await self._uow.commit()

        try:
            loaded = await self._product_repo.get(command.product_id)
            if loaded is not None:
                await self._cache.delete(storefront_pdp_cache_key(loaded.slug))
        except Exception as exc:  # pragma: no cover
            self._logger.warning("pdp_cache_invalidation_failed", error=str(exc))
