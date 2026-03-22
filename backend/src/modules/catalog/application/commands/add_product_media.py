"""
Command handler: reserve a media upload slot and return a presigned S3 PUT URL.

Validates product existence, enforces the MAIN-per-variant uniqueness rule,
persists a MediaAsset in PENDING_UPLOAD state, and returns a presigned PUT URL
for direct client upload. Part of the application layer (CQRS write side).
"""

import uuid
from dataclasses import dataclass, field

from src.modules.catalog.application.constants import raw_media_key
from src.modules.catalog.domain.entities import MediaAsset
from src.modules.catalog.domain.interfaces import IMediaAssetRepository, IProductRepository
from src.shared.exceptions import ConflictError, NotFoundError
from src.shared.interfaces.blob_storage import IBlobStorage
from src.shared.interfaces.config import IStorageConfig
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class AddProductMediaCommand:
    """Input for reserving a product media upload slot.

    Attributes:
        product_id: UUID of the product to attach media to.
        attribute_value_id: Optional variant discriminator (swatch media).
        media_type: MIME-type hint or media category (e.g. ``"image/jpeg"``).
        role: Semantic role of the asset (e.g. ``"MAIN"``, ``"GALLERY"``).
        content_type: MIME type the client will send in the PUT request.
        sort_order: Display ordering among sibling assets.
    """

    product_id: uuid.UUID
    attribute_value_id: uuid.UUID | None
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
        config: IStorageConfig,
    ) -> None:
        self._product_repo = product_repo
        self._media_repo = media_repo
        self._blob = blob_storage
        self._uow = uow
        self._config = config

    async def handle(self, cmd: AddProductMediaCommand) -> AddProductMediaResult:
        """Execute the add-product-media command.

        Args:
            cmd: Media upload parameters.

        Returns:
            Result containing the new media ID, presigned URL, and S3 key.

        Raises:
            NotFoundError: If the product does not exist.
            ConflictError: If a MAIN media asset already exists for this variant.
        """
        # 1. Verify product exists
        product = await self._product_repo.get(cmd.product_id)
        if product is None:
            raise NotFoundError(f"Product {cmd.product_id} not found")

        # 2. If role=MAIN, enforce single-main-per-variant constraint
        if cmd.role.upper() == "MAIN":
            has_main = await self._media_repo.has_main_for_variant(
                cmd.product_id,
                cmd.attribute_value_id,
            )
            if has_main:
                raise ConflictError(
                    f"MAIN media already exists for product {cmd.product_id} "
                    f"variant {cmd.attribute_value_id}"
                )

        # 3. Build S3 key and create domain entity
        media_id = uuid.uuid4()
        object_key = raw_media_key(cmd.product_id, media_id)

        media = MediaAsset.create_upload(
            product_id=cmd.product_id,
            attribute_value_id=cmd.attribute_value_id,
            media_type=cmd.media_type.upper(),
            role=cmd.role.upper(),
            sort_order=cmd.sort_order,
            raw_object_key=object_key,
            media_id=media_id,
        )

        # 4. Generate presigned PUT URL outside the transaction (S3 I/O must not
        #    hold a DB connection)
        presigned_url = await self._blob.generate_presigned_put_url(
            object_name=object_key,
            content_type=cmd.content_type,
            expiration=300,
        )

        # 5. Persist and commit
        async with self._uow:
            await self._media_repo.add(media)
            await self._uow.commit()

        return AddProductMediaResult(
            media_id=media.id,
            presigned_upload_url=presigned_url,
            object_key=object_key,
        )
