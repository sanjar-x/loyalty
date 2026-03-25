"""
Command handler: update an existing brand.

Validates slug uniqueness (excluding self), applies partial updates,
and persists changes. When the logo changes, best-effort deletes the
old logo from ImageBackend. Part of the application layer (CQRS write side).
"""

import uuid
from dataclasses import dataclass, field
from typing import Any

from src.modules.catalog.domain.entities import Brand
from src.modules.catalog.domain.exceptions import (
    BrandNotFoundError,
    BrandSlugConflictError,
)
from src.modules.catalog.domain.interfaces import IBrandRepository
from src.modules.catalog.infrastructure.image_backend_client import ImageBackendClient
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class UpdateBrandCommand:
    """Input for updating a brand.

    Attributes:
        brand_id: UUID of the brand to update.
        name: New display name, or None to keep current.
        slug: New URL-safe slug, or None to keep current.
        logo_url: New logo URL, or None to keep current.
        logo_storage_object_id: New storage object ID, or None to keep current.
    """

    brand_id: uuid.UUID
    name: str | None = None
    slug: str | None = None
    logo_url: str | None = None
    logo_storage_object_id: uuid.UUID | None = None
    _provided_fields: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True)
class UpdateBrandResult:
    """Output of brand update.

    Attributes:
        id: UUID of the updated brand.
        name: Updated display name.
        slug: Updated URL-safe slug.
        logo_url: Current public logo URL, if any.
    """

    id: uuid.UUID
    name: str
    slug: str
    logo_url: str | None = None


class UpdateBrandHandler:
    """Apply partial updates to an existing brand."""

    def __init__(
        self,
        brand_repo: IBrandRepository,
        uow: IUnitOfWork,
        image_backend: ImageBackendClient,
        logger: ILogger,
    ) -> None:
        self._brand_repo = brand_repo
        self._uow = uow
        self._image_backend = image_backend
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
        old_logo_sid: uuid.UUID | None = None

        async with self._uow:
            brand: Brand | None = await self._brand_repo.get_for_update(
                command.brand_id
            )
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

            # Track old logo for cleanup if logo fields are being updated
            logo_changing = (
                "logo_url" in command._provided_fields
                or "logo_storage_object_id" in command._provided_fields
            )
            if logo_changing:
                old_logo_sid = brand.logo_storage_object_id

            _SAFE_FIELDS = frozenset(
                {"name", "slug", "logo_url", "logo_storage_object_id"}
            )
            safe_fields = command._provided_fields & _SAFE_FIELDS
            update_kwargs: dict[str, Any] = {
                f: getattr(command, f) for f in safe_fields
            }
            brand.update(**update_kwargs)
            await self._brand_repo.update(brand)
            self._uow.register_aggregate(brand)
            await self._uow.commit()

        # Best-effort cleanup of old logo after successful commit
        if old_logo_sid and old_logo_sid != command.logo_storage_object_id:
            await self._image_backend.delete(old_logo_sid)

        self._logger.info("Brand updated", brand_id=str(brand.id))

        return UpdateBrandResult(
            id=brand.id,
            name=brand.name,
            slug=brand.slug,
            logo_url=brand.logo_url,
        )
