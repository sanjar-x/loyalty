"""
Command handler: update an existing brand.

Validates slug uniqueness (excluding self), applies partial updates,
and persists changes. Part of the application layer (CQRS write side).
"""

import uuid
from dataclasses import dataclass

from src.modules.catalog.domain.entities import Brand
from src.modules.catalog.domain.exceptions import (
    BrandNotFoundError,
    BrandSlugConflictError,
)
from src.modules.catalog.domain.interfaces import IBrandRepository
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class UpdateBrandCommand:
    """Input for updating a brand.

    Attributes:
        brand_id: UUID of the brand to update.
        name: New display name, or None to keep current.
        slug: New URL-safe slug, or None to keep current.
    """

    brand_id: uuid.UUID
    name: str | None = None
    slug: str | None = None


@dataclass(frozen=True)
class UpdateBrandResult:
    """Output of brand update.

    Attributes:
        id: UUID of the updated brand.
        name: Updated display name.
        slug: Updated URL-safe slug.
        logo_url: Current public logo URL, if any.
        logo_status: Current logo FSM state string, if any.
    """

    id: uuid.UUID
    name: str
    slug: str
    logo_url: str | None = None
    logo_status: str | None = None


class UpdateBrandHandler:
    """Apply partial updates to an existing brand."""

    def __init__(
        self,
        brand_repo: IBrandRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._brand_repo = brand_repo
        self._uow = uow
        self._logger = logger.bind(handler="UpdateBrandHandler")

    async def handle(self, command: UpdateBrandCommand) -> UpdateBrandResult:
        """Execute the update-brand command.

        Args:
            command: Brand update parameters.

        Returns:
            Result containing the updated brand state.

        Raises:
            BrandNotFoundError: If the brand does not exist.
            BrandSlugConflictError: If the new slug is already taken.
        """
        async with self._uow:
            brand: Brand | None = await self._brand_repo.get_for_update(command.brand_id)
            if brand is None:
                raise BrandNotFoundError(brand_id=command.brand_id)

            if (
                command.slug is not None
                and command.slug != brand.slug
                and await self._brand_repo.check_slug_exists_excluding(
                    command.slug, command.brand_id
                )
            ):
                raise BrandSlugConflictError(slug=command.slug)

            brand.update(name=command.name, slug=command.slug)
            await self._brand_repo.update(brand)
            self._uow.register_aggregate(brand)
            await self._uow.commit()

        self._logger.info("Brand updated", brand_id=str(brand.id))

        return UpdateBrandResult(
            id=brand.id,
            name=brand.name,
            slug=brand.slug,
            logo_url=brand.logo_url,
            logo_status=brand.logo_status.value if brand.logo_status else None,
        )
