"""
Command handler: add an externally hosted media asset to a product.

Creates a MediaAsset in COMPLETED state (no upload or processing required)
with the provided external URL. Part of the application layer (CQRS write side).
"""

import uuid
from dataclasses import dataclass

from sqlalchemy.exc import IntegrityError  # DB-level uniqueness safety net

from src.modules.catalog.domain.entities import MediaAsset
from src.modules.catalog.domain.exceptions import ProductNotFoundError
from src.modules.catalog.domain.interfaces import (
    IMediaAssetRepository,
    IProductRepository,
)
from src.shared.exceptions import ConflictError
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class AddExternalProductMediaCommand:
    """Input for adding an externally hosted media asset.

    Attributes:
        product_id: UUID of the product to attach media to.
        attribute_value_id: Optional variant discriminator (swatch media).
        media_type: Media category string (e.g. ``"image"``, ``"video"``).
        role: Semantic role of the asset (e.g. ``"main"``, ``"gallery"``).
        external_url: Public URL of the externally hosted file.
        sort_order: Display ordering among sibling assets.
    """

    product_id: uuid.UUID
    attribute_value_id: uuid.UUID | None
    media_type: str
    role: str
    external_url: str
    sort_order: int = 0


@dataclass(frozen=True)
class AddExternalProductMediaResult:
    """Output of the add-external-product-media command.

    Attributes:
        media_id: UUID of the newly created MediaAsset.
        product_id: UUID of the owning product.
        attribute_value_id: Optional variant discriminator.
        media_type: Media category string.
        role: Semantic role of the asset.
        sort_order: Display ordering among sibling assets.
        processing_status: FSM status (always COMPLETED for external).
        public_url: Public URL of the externally hosted file.
        is_external: Always True for external media.
        external_url: External URL.
    """

    media_id: uuid.UUID
    product_id: uuid.UUID
    attribute_value_id: uuid.UUID | None
    media_type: str
    role: str
    sort_order: int
    processing_status: str
    public_url: str
    is_external: bool
    external_url: str


class AddExternalProductMediaHandler:
    """Persist an externally hosted media asset in COMPLETED state."""

    def __init__(
        self,
        product_repo: IProductRepository,
        media_repo: IMediaAssetRepository,
        uow: IUnitOfWork,
    ) -> None:
        self._product_repo = product_repo
        self._media_repo = media_repo
        self._uow = uow

    async def handle(
        self, command: AddExternalProductMediaCommand
    ) -> AddExternalProductMediaResult:
        """Execute the add-external-product-media command.

        Args:
            command: External media parameters.

        Returns:
            Result containing the new media ID and external URL.

        Raises:
            ProductNotFoundError: If the product does not exist.
        """
        media = MediaAsset.create_external(
            product_id=command.product_id,
            attribute_value_id=command.attribute_value_id,
            media_type=command.media_type,
            role=command.role,
            external_url=command.external_url,
            sort_order=command.sort_order,
        )

        async with self._uow:
            product = await self._product_repo.get(command.product_id)
            if product is None:
                raise ProductNotFoundError(product_id=command.product_id)

            if command.role == "main":
                has_main = await self._media_repo.has_main_for_variant(
                    command.product_id,
                    command.attribute_value_id,
                )
                if has_main:
                    raise ConflictError(
                        f"MAIN media already exists for product {command.product_id} "
                        f"variant {command.attribute_value_id}"
                    )

            await self._media_repo.add(media)
            try:
                await self._uow.commit()
            except IntegrityError as exc:
                if "uix_media_single_main_per_color" in str(exc.orig):
                    raise ConflictError(
                        f"MAIN media already exists for product {command.product_id} "
                        f"variant {command.attribute_value_id}"
                    ) from None
                raise

        return AddExternalProductMediaResult(
            media_id=media.id,
            product_id=media.product_id,
            attribute_value_id=media.attribute_value_id,
            media_type=media.media_type,
            role=media.role,
            sort_order=media.sort_order,
            processing_status=media.processing_status.value
            if media.processing_status
            else "COMPLETED",
            public_url=media.public_url or "",
            is_external=media.is_external,
            external_url=media.external_url or "",
        )
