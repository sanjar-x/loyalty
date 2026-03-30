"""
Command handler: update a product media asset.

Supports partial update of role, variant_id, and sort_order.
Re-validates MAIN uniqueness when changing role to ``main``.
"""

import uuid
from dataclasses import dataclass

from src.modules.catalog.domain.exceptions import (
    DuplicateMainMediaError,
    MediaAssetNotFoundError,
    ProductNotFoundError,
    VariantNotFoundError,
)
from src.modules.catalog.domain.interfaces import (
    IMediaAssetRepository,
    IProductRepository,
)
from src.modules.catalog.domain.value_objects import MediaRole
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class UpdateProductMediaCommand:
    """Input for updating a media asset.

    Attributes:
        product_id: UUID of the parent product (ownership check).
        media_id: UUID of the media asset to update.
        _provided_fields: Fields explicitly sent by the client.
        variant_id: New variant binding (or None to unbind).
        role: New role value.
        sort_order: New display order.
    """

    product_id: uuid.UUID
    media_id: uuid.UUID
    _provided_fields: frozenset[str] = frozenset()
    variant_id: uuid.UUID | None = None
    role: str | None = None
    sort_order: int | None = None


@dataclass(frozen=True)
class UpdateProductMediaResult:
    """Output of media asset update."""

    id: uuid.UUID


class UpdateProductMediaHandler:
    """Partially update a media asset with ownership validation."""

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
        self._logger = logger.bind(handler="UpdateProductMediaHandler")

    async def handle(
        self, command: UpdateProductMediaCommand
    ) -> UpdateProductMediaResult:
        """Execute the update-product-media command."""
        async with self._uow:
            media = await self._media_repo.get_for_update(command.media_id)
            if media is None:
                raise MediaAssetNotFoundError(media_id=command.media_id)
            if media.product_id != command.product_id:
                raise MediaAssetNotFoundError(
                    media_id=command.media_id, product_id=command.product_id
                )

            # Resolve the effective variant_id after this update
            new_variant_id = media.variant_id
            if "variant_id" in command._provided_fields:
                new_variant_id = command.variant_id

            # Validate variant belongs to the product (if changing)
            if (
                "variant_id" in command._provided_fields
                and command.variant_id is not None
                and command.variant_id != media.variant_id
            ):
                product = await self._product_repo.get_with_variants(command.product_id)
                if product is None:
                    raise ProductNotFoundError(product_id=command.product_id)
                if product.find_variant(command.variant_id) is None:
                    raise VariantNotFoundError(
                        variant_id=command.variant_id,
                        product_id=command.product_id,
                    )

            # Check MAIN uniqueness when changing role to MAIN
            new_role = command.role if "role" in command._provided_fields else None
            if (
                new_role == MediaRole.MAIN.value
                and await self._media_repo.check_main_exists(
                    command.product_id,
                    new_variant_id,
                    exclude_media_id=command.media_id,
                )
            ):
                raise DuplicateMainMediaError(
                    product_id=command.product_id,
                    variant_id=new_variant_id,
                )

            # Apply provided fields
            if "variant_id" in command._provided_fields:
                media.variant_id = command.variant_id
            if "role" in command._provided_fields and command.role is not None:
                media.role = MediaRole(command.role)
            if (
                "sort_order" in command._provided_fields
                and command.sort_order is not None
            ):
                media.sort_order = command.sort_order

            await self._media_repo.update(media)
            await self._uow.commit()

        return UpdateProductMediaResult(id=media.id)
