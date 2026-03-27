"""
Command handler: add a media asset to a product.

Validates product existence, variant ownership (if provided), and
MAIN role uniqueness before creating a new ``MediaAsset`` record.
"""

import uuid
from dataclasses import dataclass

from src.modules.catalog.domain.entities import MediaAsset
from src.modules.catalog.domain.exceptions import (
    DuplicateMainMediaError,
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
class AddProductMediaCommand:
    """Input for adding a media asset to a product.

    Attributes:
        product_id: UUID of the parent product.
        storage_object_id: Reference to the file in ImageBackend.
        variant_id: Optional variant-level binding.
        media_type: One of image, video, model_3d, document.
        role: One of main, hover, gallery, hero_video, size_guide, packaging.
        sort_order: Display order (non-negative).
        is_external: Whether the resource is hosted externally.
        url: Public URL (required for external assets).
    """

    product_id: uuid.UUID
    storage_object_id: uuid.UUID | None = None
    variant_id: uuid.UUID | None = None
    media_type: str = "image"
    role: str = "gallery"
    sort_order: int = 0
    is_external: bool = False
    url: str | None = None


@dataclass(frozen=True)
class AddProductMediaResult:
    """Output of media asset creation."""

    media_id: uuid.UUID


class AddProductMediaHandler:
    """Create a new media asset for a product."""

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
        self._logger = logger.bind(handler="AddProductMediaHandler")

    async def handle(self, command: AddProductMediaCommand) -> AddProductMediaResult:
        """Execute the add-product-media command."""
        async with self._uow:
            # Validate product exists
            product = await self._product_repo.get_with_variants(command.product_id)
            if product is None:
                raise ProductNotFoundError(product_id=command.product_id)

            # Validate variant belongs to this product (if provided)
            if command.variant_id is not None:
                variant = product.find_variant(command.variant_id)
                if variant is None:
                    raise VariantNotFoundError(
                        variant_id=command.variant_id,
                        product_id=command.product_id,
                    )

            # Check MAIN uniqueness per (product, variant)
            if (
                command.role == MediaRole.MAIN.value
                and await self._media_repo.check_main_exists(
                    command.product_id, command.variant_id
                )
            ):
                raise DuplicateMainMediaError(
                    product_id=command.product_id,
                    variant_id=command.variant_id,
                )

            media = MediaAsset.create(
                product_id=command.product_id,
                variant_id=command.variant_id,
                media_type=command.media_type,
                role=command.role,
                sort_order=command.sort_order,
                is_external=command.is_external,
                storage_object_id=command.storage_object_id,
                url=command.url,
            )

            await self._media_repo.add(media)
            await self._uow.commit()

        return AddProductMediaResult(media_id=media.id)
