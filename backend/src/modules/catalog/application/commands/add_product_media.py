"""
Command handler: reserve a media upload slot and return a presigned S3 PUT URL.

Validates product existence, enforces the MAIN-per-variant uniqueness rule,
persists a MediaAsset in PENDING_UPLOAD state, and returns a presigned PUT URL
for direct client upload. Part of the application layer (CQRS write side).
"""

import uuid
from dataclasses import dataclass

from sqlalchemy.exc import IntegrityError

from src.modules.catalog.application.constants import (
    MEDIA_ROLE_MAIN,
    PRESIGNED_URL_EXPIRATION_SECONDS,
    raw_media_key,
)
from src.modules.catalog.domain.entities import MediaAsset
from src.modules.catalog.domain.exceptions import (
    DuplicateMainMediaError,
    ProductNotFoundError,
)
from src.modules.catalog.domain.interfaces import (
    IMediaAssetRepository,
    IProductRepository,
)
from src.shared.exceptions import ValidationError
from src.shared.interfaces.blob_storage import IBlobStorage
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork

# SEC-08: Maximum number of PENDING_UPLOAD media assets allowed per product.
# Prevents abuse of presigned URL generation (each URL consumes S3 resources).
MAX_PENDING_UPLOADS_PER_PRODUCT = 20


async def enforce_main_media_uniqueness(
    product_id: uuid.UUID,
    variant_id: uuid.UUID | None,
    role: str,
    media_repo: IMediaAssetRepository,
) -> None:
    """Check that no MAIN media asset already exists for a product/variant combo.

    This is an application-level guard shared by both the upload-based and
    external media handlers.  A database-level unique constraint should
    back this check to prevent TOCTOU races; the callers additionally
    wrap their commit in an ``IntegrityError`` catch as a safety net.

    Raises:
        DuplicateMainMediaError: If a MAIN asset already exists.
    """
    if role != MEDIA_ROLE_MAIN:
        return
    has_main = await media_repo.has_main_for_variant(product_id, variant_id)
    if has_main:
        raise DuplicateMainMediaError(
            product_id=product_id,
            variant_id=variant_id,
        )


@dataclass(frozen=True)
class AddProductMediaCommand:
    """Input for reserving a product media upload slot.

    Attributes:
        product_id: UUID of the product to attach media to.
        variant_id: Optional variant discriminator (swatch media).
        media_type: MIME-type hint or media category (e.g. ``"image/jpeg"``).
        role: Semantic role of the asset (e.g. ``"MAIN"``, ``"GALLERY"``).
        content_type: MIME type the client will send in the PUT request.
        sort_order: Display ordering among sibling assets.
    """

    product_id: uuid.UUID
    variant_id: uuid.UUID | None
    media_type: str
    role: str
    content_type: str
    sort_order: int = 0


@dataclass(frozen=True)
class AddProductMediaResult:
    """Output of the add-product-media command.

    Attributes:
        media_id: UUID of the newly created MediaAsset.
        presigned_upload_url: Presigned S3 PUT URL for direct client upload.
        object_key: S3 key where the raw file will be stored.
    """

    media_id: uuid.UUID
    presigned_upload_url: str
    object_key: str


class AddProductMediaHandler:
    """Reserve a media slot and prepare a presigned S3 upload URL."""

    def __init__(
        self,
        product_repo: IProductRepository,
        media_repo: IMediaAssetRepository,
        blob_storage: IBlobStorage,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._product_repo = product_repo
        self._media_repo = media_repo
        self._blob_storage = blob_storage
        self._uow = uow
        self._logger = logger.bind(handler="AddProductMediaHandler")

    async def handle(self, command: AddProductMediaCommand) -> AddProductMediaResult:
        """Execute the add-product-media command.

        Args:
            command: Media upload parameters.

        Returns:
            Result containing the new media ID, presigned URL, and S3 key.

        Raises:
            ProductNotFoundError: If the product does not exist.
            ConflictError: If a MAIN media asset already exists for this variant.
        """
        # SEC-08: Limit the number of outstanding PENDING_UPLOAD slots to
        # prevent abuse of presigned URL generation.
        pending_count = await self._media_repo.count_pending_uploads(command.product_id)
        if pending_count >= MAX_PENDING_UPLOADS_PER_PRODUCT:
            raise ValidationError(
                f"Too many pending uploads for product {command.product_id}. "
                f"Maximum {MAX_PENDING_UPLOADS_PER_PRODUCT} pending uploads allowed. "
                f"Please confirm or delete existing uploads before requesting new ones."
            )

        # 1. Build S3 key and create domain entity
        media_id = uuid.uuid7()
        object_key = raw_media_key(command.product_id, media_id)

        media = MediaAsset.create_upload(
            product_id=command.product_id,
            variant_id=command.variant_id,
            media_type=command.media_type,
            role=command.role,
            sort_order=command.sort_order,
            raw_object_key=object_key,
            media_id=media_id,
        )

        # 2. Generate presigned PUT URL outside the transaction (S3 I/O must not
        #    hold a DB connection).
        #    Accepted trade-off: the presigned URL is generated before the
        #    transaction, so if the transaction fails, an orphaned S3 upload may
        #    occur. A periodic S3 lifecycle policy handles cleanup.
        presigned_url = await self._blob_storage.generate_presigned_put_url(
            object_name=object_key,
            content_type=command.content_type,
            expiration=PRESIGNED_URL_EXPIRATION_SECONDS,
        )

        # 3. Verify product exists, enforce MAIN uniqueness, and persist atomically
        async with self._uow:
            product = await self._product_repo.get(command.product_id)
            if product is None:
                raise ProductNotFoundError(product_id=command.product_id)

            await enforce_main_media_uniqueness(
                product_id=command.product_id,
                variant_id=command.variant_id,
                role=command.role,
                media_repo=self._media_repo,
            )

            await self._media_repo.add(media)
            try:
                await self._uow.commit()
            except IntegrityError:
                # TOCTOU safety net: two concurrent requests may both pass
                # the has_main_for_variant check.  A DB unique constraint on
                # (product_id, variant_id, role='MAIN') rejects the second
                # insert at commit time.
                raise DuplicateMainMediaError(
                    product_id=command.product_id,
                    variant_id=command.variant_id,
                )

        return AddProductMediaResult(
            media_id=media.id,
            presigned_upload_url=presigned_url,
            object_key=object_key,
        )
