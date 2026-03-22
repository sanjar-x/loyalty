"""
Command handler: create a new brand.

Validates slug uniqueness, persists the Brand aggregate, and optionally
generates a presigned S3 URL for direct logo upload. Part of the
application layer (CQRS write side).
"""

import uuid
from dataclasses import dataclass

from src.modules.catalog.application.constants import raw_logo_key
from src.modules.catalog.domain.entities import Brand
from src.modules.catalog.domain.exceptions import BrandSlugConflictError
from src.modules.catalog.domain.interfaces import IBrandRepository
from src.shared.interfaces.blob_storage import IBlobStorage
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class LogoMetadata:
    """Client-provided metadata about the logo file to be uploaded.

    Attributes:
        filename: Original filename from the client.
        content_type: MIME type of the logo file.
        size: File size in bytes, if known.
    """

    filename: str
    content_type: str
    size: int | None = None


@dataclass(frozen=True)
class CreateBrandCommand:
    """Input for creating a new brand.

    Attributes:
        name: Display name of the brand.
        slug: URL-safe unique identifier.
        logo: Optional logo metadata; triggers presigned URL generation.
    """

    name: str
    slug: str
    logo: LogoMetadata | None = None


@dataclass(frozen=True)
class CreateBrandResult:
    """Output of brand creation.

    Attributes:
        brand_id: UUID of the newly created brand.
        presigned_upload_url: Presigned PUT URL for logo upload, if requested.
        object_key: S3 key for the logo upload destination, if requested.
    """

    brand_id: uuid.UUID
    presigned_upload_url: str | None = None
    object_key: str | None = None


class CreateBrandHandler:
    """Create a new brand with optional logo upload preparation."""

    def __init__(
        self,
        brand_repo: IBrandRepository,
        uow: IUnitOfWork,
        blob_storage: IBlobStorage,
        logger: ILogger,
    ) -> None:
        self._brand_repo = brand_repo
        self._uow = uow
        self._blob_storage = blob_storage
        self._logger = logger.bind(handler="CreateBrandHandler")

    async def handle(self, command: CreateBrandCommand) -> CreateBrandResult:
        """Execute the create-brand command.

        Args:
            command: Brand creation parameters.

        Returns:
            Result containing the brand ID and optional presigned URL.

        Raises:
            BrandSlugConflictError: If the slug is already taken.
        """
        # Pre-compute outside the transaction — S3 I/O must not hold a DB connection.
        # Accepted trade-off: the presigned URL is generated before the transaction,
        # so if the transaction fails, an orphaned S3 upload may occur. A periodic
        # S3 lifecycle policy handles cleanup of such orphaned objects.
        brand_id = uuid.uuid4()
        presigned_url: str | None = None
        object_key: str | None = None

        if command.logo:
            object_key = raw_logo_key(brand_id)
            presigned_url = await self._blob_storage.generate_presigned_put_url(
                object_name=object_key,
                content_type=command.logo.content_type,
            )

        # Transaction — database operations only
        async with self._uow:
            if await self._brand_repo.check_slug_exists(command.slug):
                raise BrandSlugConflictError(slug=command.slug)

            brand = Brand.create(name=command.name, slug=command.slug, brand_id=brand_id)
            brand = await self._brand_repo.add(brand)

            if command.logo and object_key:
                brand.init_logo_upload(
                    object_key=object_key,
                    content_type=command.logo.content_type,
                )
                await self._brand_repo.update(brand)

            self._uow.register_aggregate(brand)
            await self._uow.commit()

        self._logger.info("Brand created", brand_id=str(brand.id))

        return CreateBrandResult(
            brand_id=brand.id,
            presigned_upload_url=presigned_url,
            object_key=object_key,
        )
