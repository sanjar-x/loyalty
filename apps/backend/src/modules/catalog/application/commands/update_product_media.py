"""
Command handler: update a product media asset.

Supports partial update of role, variant_id, and sort_order. Re-validates
MAIN uniqueness against the **effective** post-update (product, variant)
key and verifies any non-null ``variant_id`` actually belongs to the
product before mutation. Emits ``MediaAssetUpdatedEvent`` on the
product aggregate so the outbox carries the change to downstream
subscribers (search reindex, audit, PDP cache invalidation).
"""

import uuid
from dataclasses import dataclass

from src.modules.catalog.application.constants import storefront_pdp_cache_key
from src.modules.catalog.domain.events import MediaAssetUpdatedEvent
from src.modules.catalog.domain.exceptions import (
    DuplicateMainMediaError,
    MediaAssetNotFoundError,
    ProductNotFoundError,
    VariantNotFoundError,
)
from src.modules.catalog.domain.interfaces import (
    IMediaAssetRepository,
    IProductRepository,
)
from src.modules.catalog.domain.value_objects import MediaRole
from src.shared.interfaces.cache import ICacheService
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class UpdateProductMediaCommand:
    """Input for updating a media asset.

    Attributes:
        product_id: UUID of the parent product (ownership check).
        media_id: UUID of the media asset to update.
        _provided_fields: Fields explicitly sent by the client.
        variant_id: New variant binding (or None to unbind).
        role: New role value.
        sort_order: New display order.
    """

    product_id: uuid.UUID
    media_id: uuid.UUID
    _provided_fields: frozenset[str] = frozenset()
    variant_id: uuid.UUID | None = None
    role: str | None = None
    sort_order: int | None = None


@dataclass(frozen=True)
class UpdateProductMediaResult:
    """Output of media asset update."""

    id: uuid.UUID


class UpdateProductMediaHandler:
    """Partially update a media asset with ownership validation."""

    def __init__(
        self,
        product_repo: IProductRepository,
        media_repo: IMediaAssetRepository,
        uow: IUnitOfWork,
        cache: ICacheService,
        logger: ILogger,
    ) -> None:
        self._product_repo = product_repo
        self._media_repo = media_repo
        self._uow = uow
        self._cache = cache
        self._logger = logger.bind(handler="UpdateProductMediaHandler")

    async def handle(
        self, command: UpdateProductMediaCommand
    ) -> UpdateProductMediaResult:
        """Execute the update-product-media command."""
        async with self._uow:
            media = await self._media_repo.get_for_update(command.media_id)
            if media is None:
                raise MediaAssetNotFoundError(media_id=command.media_id)
            if media.product_id != command.product_id:
                raise MediaAssetNotFoundError(
                    media_id=command.media_id, product_id=command.product_id
                )

            # Aggregate root is loaded once and reused for both variant-
            # ownership validation and the event emission below.
            product = await self._product_repo.get_with_variants(command.product_id)
            if product is None:  # pragma: no cover — FK guarantees existence
                raise ProductNotFoundError(product_id=command.product_id)

            # --- Effective post-update keys for validation ---
            previous_variant_id = media.variant_id
            previous_role = media.role
            new_variant_id = (
                command.variant_id
                if "variant_id" in command._provided_fields
                else media.variant_id
            )
            # Effective role: the request's value if provided, else the
            # current row's role. Reading from ``_provided_fields`` alone
            # used to drop the MAIN-uniqueness guard whenever a PATCH
            # only touched ``variantId`` — the DB partial-unique index
            # then surfaced the violation as an opaque 500 instead of a
            # documented 409 ``DuplicateMainMediaError``.
            new_role_value = (
                command.role
                if "role" in command._provided_fields and command.role is not None
                else media.role.value
            )

            # --- Variant ownership: always verify when variant_id is
            #     present and non-null, regardless of whether it equals
            #     the current value. The pre-fix guard skipped this when
            #     the new id matched the current binding, which let a
            #     PATCH from product A point a media row at a variant
            #     owned by product B as long as both products happened
            #     to hold a variant with the same id (impossible under
            #     UUIDv4 but still an aggregate-invariant gap).
            if (
                "variant_id" in command._provided_fields
                and command.variant_id is not None
                and product.find_variant(command.variant_id) is None
            ):
                raise VariantNotFoundError(
                    variant_id=command.variant_id,
                    product_id=command.product_id,
                )

            # --- MAIN uniqueness against the EFFECTIVE (product, variant)
            #     key the row will hold after the mutation. ``check_main_exists``
            #     excludes the row under update so re-asserting the same
            #     role on the same row stays idempotent.
            if (
                new_role_value == MediaRole.MAIN.value
                and await self._media_repo.check_main_exists(
                    command.product_id,
                    new_variant_id,
                    exclude_media_id=command.media_id,
                )
            ):
                raise DuplicateMainMediaError(
                    product_id=command.product_id,
                    variant_id=new_variant_id,
                )

            # --- Apply provided fields ---
            changed = False
            if (
                "variant_id" in command._provided_fields
                and media.variant_id != command.variant_id
            ):
                media.variant_id = command.variant_id
                changed = True
            if "role" in command._provided_fields and command.role is not None:
                new_role = MediaRole(command.role)
                if media.role != new_role:
                    media.role = new_role
                    changed = True
            if (
                "sort_order" in command._provided_fields
                and command.sort_order is not None
                and media.sort_order != command.sort_order
            ):
                media.sort_order = command.sort_order
                changed = True

            if changed:
                await self._media_repo.update(media)
                product.add_domain_event(
                    MediaAssetUpdatedEvent(
                        product_id=product.id,
                        media_asset_id=media.id,
                        variant_id=media.variant_id,
                        previous_variant_id=previous_variant_id,
                        role=media.role.value,
                        previous_role=previous_role.value,
                        sort_order=media.sort_order,
                    )
                )
                self._uow.register_aggregate(product)

            await self._uow.commit()

        try:
            await self._cache.delete(storefront_pdp_cache_key(product.slug))
        except Exception as exc:  # pragma: no cover
            self._logger.warning("pdp_cache_invalidation_failed", error=str(exc))

        return UpdateProductMediaResult(id=media.id)
