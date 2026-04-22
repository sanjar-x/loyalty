"""
Command handler: update an existing product.

Validates the optional optimistic-lock version, checks slug uniqueness when
the slug is being changed, builds a kwargs dict for only the fields the caller
explicitly provided, and delegates the actual mutation to ``Product.update()``.
Part of the application layer (CQRS write side).
"""

import uuid
from dataclasses import dataclass, field
from typing import Any

from src.modules.catalog.application.commands.sync_media import compute_media_diff
from src.modules.catalog.application.constants import storefront_pdp_cache_key
from src.modules.catalog.domain.entities import MediaAsset, Product
from src.modules.catalog.domain.exceptions import (
    BrandNotFoundError,
    CategoryNotFoundError,
    ConcurrencyError,
    ProductNotFoundError,
    ProductSlugConflictError,
)
from src.modules.catalog.domain.interfaces import (
    IBrandRepository,
    ICategoryRepository,
    IImageBackendClient,
    IMediaAssetRepository,
    IProductRepository,
)
from src.shared.exceptions import UnprocessableEntityError
from src.shared.interfaces.cache import ICacheService
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


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
        supplier_id: New supplier UUID or None (both valid); absent means not provided.
        country_of_origin: New ISO country code or None; absent means not provided.
        tags: New tags list, or None to keep current.
        version: Expected product version for optimistic locking, or None to skip.
    """

    product_id: uuid.UUID
    title_i18n: dict[str, str] | None = None
    description_i18n: dict[str, str] | None = None
    slug: str | None = None
    brand_id: uuid.UUID | None = None
    primary_category_id: uuid.UUID | None = None
    supplier_id: uuid.UUID | None = None
    country_of_origin: str | None = None
    tags: list[str] | None = None
    version: int | None = None
    media: list[dict] | None = None
    _provided_fields: frozenset[str] = field(default_factory=frozenset)


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
        brand_repo: IBrandRepository,
        category_repo: ICategoryRepository,
        media_repo: IMediaAssetRepository,
        image_backend: IImageBackendClient,
        uow: IUnitOfWork,
        cache: ICacheService,
        logger: ILogger,
    ) -> None:
        self._product_repo = product_repo
        self._brand_repo = brand_repo
        self._category_repo = category_repo
        self._media_repo = media_repo
        self._image_backend = image_backend
        self._uow = uow
        self._cache = cache
        self._logger = logger.bind(handler="UpdateProductHandler")

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
            product = await self._product_repo.get_for_update_with_variants(
                command.product_id
            )
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

            old_slug = product.slug

            # --- FK validation (only when the field is being updated) ---
            if "brand_id" in command._provided_fields:
                if command.brand_id is None:
                    raise UnprocessableEntityError(
                        message="brand_id cannot be set to None.",
                        error_code="BRAND_ID_REQUIRED",
                        details={},
                    )
                brand = await self._brand_repo.get(command.brand_id)
                if brand is None:
                    raise BrandNotFoundError(brand_id=command.brand_id)

            if "primary_category_id" in command._provided_fields:
                if command.primary_category_id is None:
                    raise UnprocessableEntityError(
                        message="primary_category_id cannot be set to None.",
                        error_code="PRIMARY_CATEGORY_ID_REQUIRED",
                        details={},
                    )
                category = await self._category_repo.get(command.primary_category_id)
                if category is None:
                    raise CategoryNotFoundError(category_id=command.primary_category_id)

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
            # The router records which fields were explicitly provided in
            # ``_provided_fields``.  We intersect with Product._UPDATABLE_FIELDS
            # to ensure non-updatable fields (e.g. "version", "product_id")
            # never leak through to entity.update().  Defence-in-depth: the
            # entity also rejects unknown kwargs, but filtering here keeps the
            # application layer self-contained.
            safe_fields = command._provided_fields & Product._UPDATABLE_FIELDS
            update_kwargs: dict[str, Any] = {
                f: getattr(command, f) for f in safe_fields
            }

            product.update(**update_kwargs)

            storage_ids_to_delete: list[uuid.UUID] = []
            if command.media is not None:
                existing = await self._media_repo.list_by_product(command.product_id)
                current_dicts = [
                    {
                        "id": str(m.id),
                        "storage_object_id": str(m.storage_object_id)
                        if m.storage_object_id
                        else None,
                        "url": m.url,
                        "role": m.role,
                        "sort_order": m.sort_order,
                        "variant_id": str(m.variant_id) if m.variant_id else None,
                        "is_external": m.is_external,
                    }
                    for m in existing
                ]
                to_add, to_update, to_delete = compute_media_diff(
                    current_dicts, command.media
                )

                for item in to_delete:
                    mid = uuid.UUID(item["id"])
                    await self._media_repo.delete(mid)
                    sid = item.get("storage_object_id")
                    if sid:
                        storage_ids_to_delete.append(uuid.UUID(sid))

                for item in to_update:
                    media = await self._media_repo.get(uuid.UUID(item["id"]))
                    if media is None:
                        continue
                    media.role = item["role"]
                    media.sort_order = item["sort_order"]
                    media.variant_id = (
                        uuid.UUID(item["variant_id"])
                        if item.get("variant_id")
                        else None
                    )
                    await self._media_repo.update(media)

                for item in to_add:
                    media_asset = MediaAsset.create(
                        product_id=command.product_id,
                        variant_id=uuid.UUID(item["variant_id"])
                        if item.get("variant_id")
                        else None,
                        media_type=item.get("media_type", "IMAGE"),
                        role=item.get("role", "GALLERY"),
                        sort_order=item.get("sort_order", 0),
                        is_external=item.get("is_external", False),
                        storage_object_id=uuid.UUID(item["storage_object_id"])
                        if item.get("storage_object_id")
                        else None,
                        url=item.get("url"),
                        image_variants=item.get("image_variants"),
                    )
                    await self._media_repo.add(media_asset)

            await self._product_repo.update(product)
            self._uow.register_aggregate(product)
            await self._uow.commit()

        # Best-effort ImageBackend cleanup AFTER successful commit
        for sid in storage_ids_to_delete:
            await self._image_backend.delete(sid)

        try:
            slugs_to_invalidate = {old_slug, product.slug}
            for slug in slugs_to_invalidate:
                await self._cache.delete(storefront_pdp_cache_key(slug))
        except Exception as exc:  # pragma: no cover
            self._logger.warning("pdp_cache_invalidation_failed", error=str(exc))

        self._logger.info(
            "Product updated",
            product_id=str(product.id),
            provided_fields=sorted(command._provided_fields),
        )
        return UpdateProductResult(id=product.id)
