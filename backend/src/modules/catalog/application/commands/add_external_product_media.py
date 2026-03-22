"""
Command handler: add an externally hosted media asset to a product.

Creates a MediaAsset in COMPLETED state (no upload or processing required)
with the provided external URL. Part of the application layer (CQRS write side).
"""

import uuid
from dataclasses import dataclass

from src.modules.catalog.domain.entities import MediaAsset
from src.modules.catalog.domain.interfaces import (
    IMediaAssetRepository,
    IProductRepository,
)
from src.shared.exceptions import NotFoundError
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
        public_url: Public URL of the externally hosted file.
    """

    media_id: uuid.UUID
    public_url: str


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
        self, cmd: AddExternalProductMediaCommand
    ) -> AddExternalProductMediaResult:
        """Execute the add-external-product-media command.

        Args:
            cmd: External media parameters.

        Returns:
            Result containing the new media ID and external URL.

        Raises:
            NotFoundError: If the product does not exist.
        """
        product = await self._product_repo.get(cmd.product_id)
        if product is None:
            raise NotFoundError(f"Product {cmd.product_id} not found")

        media = MediaAsset.create_external(
            product_id=cmd.product_id,
            attribute_value_id=cmd.attribute_value_id,
            media_type=cmd.media_type.upper(),
            role=cmd.role.upper(),
            external_url=cmd.external_url,
            sort_order=cmd.sort_order,
        )

        async with self._uow:
            await self._media_repo.add(media)
            await self._uow.commit()

        return AddExternalProductMediaResult(
            media_id=media.id,
            public_url=media.public_url,
        )
