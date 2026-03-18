"""
Command handler: update an existing product.

Validates the optional optimistic-lock version, checks slug uniqueness when
the slug is being changed, builds a kwargs dict for only the fields the caller
explicitly provided, and delegates the actual mutation to ``Product.update()``.
Part of the application layer (CQRS write side).
"""

import uuid
from dataclasses import dataclass
from typing import Any

from src.modules.catalog.domain.exceptions import (
    ConcurrencyError,
    ProductNotFoundError,
    ProductSlugConflictError,
)
from src.modules.catalog.domain.interfaces import IProductRepository
from src.shared.interfaces.uow import IUnitOfWork

# Module-level sentinel -- distinguishes "not provided" from "set to None" for
# nullable fields (supplier_id, country_of_origin).  This sentinel is local to
# the command module; the handler builds kwargs conditionally so it never
# crosses into the domain entity layer.
_SENTINEL: object = object()


@dataclass(frozen=True)
class UpdateProductCommand:
    """Input for updating an existing product.

    All fields except ``product_id`` are optional; omitting a field (or
    leaving it at its default) means "keep the current value".  Pass ``None``
    explicitly for ``supplier_id`` / ``country_of_origin`` to *clear* those
    fields; the sentinel default leaves them unchanged.

    Attributes:
        product_id: UUID of the product to update.
        title_i18n: New multilingual title, or None to keep current.
        description_i18n: New multilingual description, or None to keep current.
        slug: New URL-safe slug, or None to keep current.
        brand_id: New brand UUID, or None to keep current.
        primary_category_id: New primary category UUID, or None to keep current.
        supplier_id: New supplier UUID, None to clear, or absent (sentinel) to keep.
        country_of_origin: New ISO country code, None to clear, or absent to keep.
        tags: New tags list, or None to keep current.
        version: Expected product version for optimistic locking, or None to skip.
    """

    product_id: uuid.UUID
    title_i18n: dict[str, str] | None = None
    description_i18n: dict[str, str] | None = None
    slug: str | None = None
    brand_id: uuid.UUID | None = None
    primary_category_id: uuid.UUID | None = None
    supplier_id: uuid.UUID | None | object = _SENTINEL
    country_of_origin: str | None | object = _SENTINEL
    tags: list[str] | None = None
    version: int | None = None


@dataclass(frozen=True)
class UpdateProductResult:
    """Output of a successful product update.

    Attributes:
        id: UUID of the updated product.
    """

    id: uuid.UUID


class UpdateProductHandler:
    """Apply partial updates to an existing product.

    Orchestrates: fetch -> version check -> slug uniqueness check ->
    conditional field mutation -> persist -> commit.

    No domain events are emitted (product lifecycle events are deferred to P2).
    """

    def __init__(
        self,
        product_repo: IProductRepository,
        uow: IUnitOfWork,
    ) -> None:
        self._product_repo = product_repo
        self._uow = uow

    async def handle(self, command: UpdateProductCommand) -> UpdateProductResult:
        """Execute the update-product command.

        Args:
            command: Product update parameters.

        Returns:
            Result containing the updated product ID.

        Raises:
            ProductNotFoundError: If no product exists with the given ID.
            ConcurrencyError: If ``command.version`` is provided and does not
                match the product's current version (optimistic locking).
            ProductSlugConflictError: If the new slug is already taken by
                another product.
            ValueError: If ``title_i18n`` is provided but empty (enforced
                by the domain entity).
        """
        async with self._uow:
            product = await self._product_repo.get(command.product_id)
            if product is None:
                raise ProductNotFoundError(product_id=command.product_id)

            # --- Optimistic locking: API-level version guard ---
            # When a version is provided, fail fast before applying any
            # mutations. The DB-level guard (version_id_col / StaleDataError)
            # catches the narrow race condition that slips past this check.
            if command.version is not None and command.version != product.version:
                raise ConcurrencyError(
                    entity_type="Product",
                    entity_id=product.id,
                    expected_version=command.version,
                    actual_version=product.version,
                )

            # --- Slug uniqueness check (only when slug is actually changing) ---
            if (
                command.slug is not None
                and command.slug != product.slug
                and await self._product_repo.check_slug_exists_excluding(
                    command.slug, command.product_id
                )
            ):
                raise ProductSlugConflictError(slug=command.slug)

            # --- Build kwargs for only the fields the caller provided ---
            # Non-sentinel scalar fields: None means "keep current"; any other
            # value means "apply this change".
            # Sentinel fields: the command's _SENTINEL means "keep current";
            # None means "clear"; any UUID/str means "set".
            update_kwargs: dict[str, Any] = {}

            if command.title_i18n is not None:
                update_kwargs["title_i18n"] = command.title_i18n
            if command.description_i18n is not None:
                update_kwargs["description_i18n"] = command.description_i18n
            if command.slug is not None:
                update_kwargs["slug"] = command.slug
            if command.brand_id is not None:
                update_kwargs["brand_id"] = command.brand_id
            if command.primary_category_id is not None:
                update_kwargs["primary_category_id"] = command.primary_category_id
            if command.supplier_id is not _SENTINEL:
                update_kwargs["supplier_id"] = command.supplier_id
            if command.country_of_origin is not _SENTINEL:
                update_kwargs["country_of_origin"] = command.country_of_origin
            if command.tags is not None:
                update_kwargs["tags"] = command.tags

            product.update(**update_kwargs)

            await self._product_repo.update(product)
            await self._uow.commit()

        return UpdateProductResult(id=product.id)
