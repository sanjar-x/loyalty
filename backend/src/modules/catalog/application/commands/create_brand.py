"""
Command handler: create a new brand.

Validates slug uniqueness, persists the Brand aggregate, and optionally
stores a logo URL and storage object reference. Part of the application
layer (CQRS write side).
"""

import uuid
from dataclasses import dataclass

from src.modules.catalog.domain.entities import Brand
from src.modules.catalog.domain.exceptions import BrandSlugConflictError
from src.modules.catalog.domain.interfaces import IBrandRepository
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class CreateBrandCommand:
    """Input for creating a new brand.

    Attributes:
        name: Display name of the brand.
        slug: URL-safe unique identifier.
        logo_url: Optional public URL for the brand logo.
        logo_storage_object_id: Optional reference to the StorageObject in ImageBackend.
    """

    name: str
    slug: str
    logo_url: str | None = None
    logo_storage_object_id: uuid.UUID | None = None


@dataclass(frozen=True)
class CreateBrandResult:
    """Output of brand creation.

    Attributes:
        brand_id: UUID of the newly created brand.
    """

    brand_id: uuid.UUID


class CreateBrandHandler:
    """Create a new brand with optional logo URL."""

    def __init__(
        self,
        brand_repo: IBrandRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._brand_repo = brand_repo
        self._uow = uow
        self._logger = logger.bind(handler="CreateBrandHandler")

    async def handle(self, command: CreateBrandCommand) -> CreateBrandResult:
        """Execute the create-brand command.

        Args:
            command: Brand creation parameters.

        Returns:
            Result containing the brand ID.

        Raises:
            BrandSlugConflictError: If the slug is already taken.
        """
        brand_id = uuid.uuid4()

        async with self._uow:
            if await self._brand_repo.check_slug_exists(command.slug):
                raise BrandSlugConflictError(slug=command.slug)

            brand = Brand.create(
                name=command.name,
                slug=command.slug,
                brand_id=brand_id,
                logo_url=command.logo_url,
                logo_storage_object_id=command.logo_storage_object_id,
            )
            brand = await self._brand_repo.add(brand)
            self._uow.register_aggregate(brand)
            await self._uow.commit()

        self._logger.info("Brand created", brand_id=str(brand.id))

        return CreateBrandResult(brand_id=brand.id)
