"""
Command handler: update an existing SKU variant within a product.

Fetches the product aggregate with its SKUs, locates the target SKU,
optionally checks the optimistic-lock version, re-computes the variant
hash if variant attributes changed (and checks uniqueness), builds a
Money value object for price fields, and delegates mutation to
``SKU.update()`` via the Product aggregate.

Part of the application layer (CQRS write side).
"""

import uuid
from dataclasses import dataclass, field

from redis.exceptions import RedisError

from src.modules.catalog.application.constants import storefront_pdp_cache_key
from src.modules.catalog.domain.events import SKUPurchasePriceUpdatedEvent
from src.modules.catalog.domain.exceptions import (
    ConcurrencyError,
    DuplicateVariantCombinationError,
    ProductNotFoundError,
    SKUCodeConflictError,
    SKUNotFoundError,
)
from src.modules.catalog.domain.interfaces import IProductRepository
from src.modules.catalog.domain.value_objects import Money, PurchaseCurrency
from src.shared.exceptions import OptimisticLockError, ValidationError
from src.shared.interfaces.cache import ICacheService
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class UpdateSKUCommand:
    """Input for updating an existing SKU variant.

    All fields except ``product_id`` and ``sku_id`` are optional; omitting
    a field (or leaving it at its default) means "keep the current value".
    Pass ``None`` explicitly for ``compare_at_price`` to *clear* the
    compare-at price; leaving it out of ``_provided_fields`` keeps it
    unchanged.

    Attributes:
        product_id: UUID of the product that owns the SKU.
        sku_id: UUID of the SKU to update.
        sku_code: New stock-keeping code, or None to keep current.
        price: New selling price as a domain ``Money``, or None to keep
            current. Use ``compare_at_price`` semantics to clear.
        compare_at_price: New compare-at price (Money), None to clear,
            or absent (not in ``_provided_fields``) to keep unchanged.
        purchase_price: New wholesale cost (Money). When provided,
            triggers ``set_purchase_price`` which arms the autonomous
            recompute pipeline (CAT-001).
        is_active: New active flag, or None to keep current.
        variant_attributes: New variant attribute pairs, or None to keep.
        version: Expected SKU version for optimistic locking, or None to skip.
    """

    product_id: uuid.UUID
    variant_id: uuid.UUID
    sku_id: uuid.UUID
    sku_code: str | None = None
    price: Money | None = None
    compare_at_price: Money | None = None
    purchase_price: Money | None = None
    is_active: bool | None = None
    variant_attributes: list[tuple[uuid.UUID, uuid.UUID]] | None = None
    version: int | None = None
    expected_version: int | None = None
    """T-1.4 — header-level optimistic-lock counter, sourced from
    ``If-Match: "v{N}"``. Distinct from the legacy body-level
    ``version`` (kept for backwards compatibility): when set and
    different from the current SKU version, raises
    :class:`OptimisticLockError` so the router can upgrade it to 412
    ``PRECONDITION_FAILED``. Body ``version`` continues to raise
    :class:`ConcurrencyError` (409 with ``CONCURRENCY_ERROR``)."""
    _provided_fields: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True)
class UpdateSKUResult:
    """Output of a successful SKU update.

    Attributes:
        id: UUID of the updated SKU.
        version: Post-mutation optimistic-lock counter (used by the
            router to attach the new ``ETag`` on the response).
    """

    id: uuid.UUID
    version: int = 0


class UpdateSKUHandler:
    """Apply partial updates to an existing SKU variant.

    Orchestrates: fetch product with SKUs -> find SKU -> version check ->
    variant hash uniqueness check -> build update kwargs -> delegate to
    SKU.update() -> persist -> commit.

    No domain events are emitted (product lifecycle events are deferred to P2).
    """

    def __init__(
        self,
        product_repo: IProductRepository,
        uow: IUnitOfWork,
        cache: ICacheService,
        logger: ILogger,
    ) -> None:
        self._product_repo = product_repo
        self._uow = uow
        self._cache = cache
        self._logger = logger.bind(handler="UpdateSKUHandler")

    async def handle(self, command: UpdateSKUCommand) -> UpdateSKUResult:
        """Execute the update-SKU command.

        Args:
            command: SKU update parameters.

        Returns:
            Result containing the updated SKU ID.

        Raises:
            ProductNotFoundError: If no product exists with the given ID.
            SKUNotFoundError: If no active SKU with the given ID exists
                within the product.
            ConcurrencyError: If ``command.version`` is provided and does not
                match the SKU's current version (optimistic locking).
            DuplicateVariantCombinationError: If the new variant attributes
                would duplicate an existing active SKU's combination.
            ValueError: If the resulting compare_at_price <= price.
        """
        async with self._uow:
            product = await self._product_repo.get_for_update_with_variants(
                command.product_id
            )
            if product is None:
                raise ProductNotFoundError(product_id=command.product_id)

            # ``find_sku`` walks every variant, so the URL's ``variantId``
            # would otherwise be cosmetic — a PATCH against variant X
            # could mutate a SKU owned by variant Y and return a body
            # with the "wrong" ``variant_id``. Reject cross-variant
            # routing with a clean 404 before any further work.
            sku = product.find_sku(command.sku_id)
            if sku is None or sku.variant_id != command.variant_id:
                raise SKUNotFoundError(sku_id=command.sku_id)

            # T-1.4 — header-level optimistic locking via If-Match.
            # Mismatch raises :class:`OptimisticLockError` (router
            # upgrades to 412 PRECONDITION_FAILED). Distinct path from
            # the legacy ``command.version`` body-level guard below
            # which surfaces as :class:`ConcurrencyError` (409).
            if (
                command.expected_version is not None
                and command.expected_version != sku.version
            ):
                raise OptimisticLockError(
                    entity_type="SKU",
                    entity_id=sku.id,
                    expected_version=command.expected_version,
                    actual_version=sku.version,
                )

            # --- Optimistic locking: API-level version guard (legacy body-level) ---
            if command.version is not None and command.version != sku.version:
                raise ConcurrencyError(
                    entity_type="SKU",
                    entity_id=sku.id,
                    expected_version=command.version,
                    actual_version=sku.version,
                )

            # --- Build update kwargs ---
            update_kwargs: dict[str, object] = {}

            if command.sku_code is not None:
                if await self._product_repo.check_sku_code_exists(
                    command.sku_code, exclude_sku_id=command.sku_id
                ):
                    raise SKUCodeConflictError(
                        sku_code=command.sku_code, product_id=command.product_id
                    )
                update_kwargs["sku_code"] = command.sku_code

            if "price" in command._provided_fields:
                update_kwargs["price"] = command.price

            if "compare_at_price" in command._provided_fields:
                update_kwargs["compare_at_price"] = command.compare_at_price

            if command.is_active is not None:
                update_kwargs["is_active"] = command.is_active

            # --- Variant attributes: re-compute hash and check uniqueness ---
            if command.variant_attributes is not None:
                new_hash = product.compute_variant_hash(
                    sku.variant_id, command.variant_attributes
                )
                # Check uniqueness among active SKUs (excluding the one being updated).
                for v in product.variants:
                    for existing in v.skus:
                        if (
                            existing.id != sku.id
                            and existing.deleted_at is None
                            and existing.variant_hash == new_hash
                        ):
                            raise DuplicateVariantCombinationError(
                                product_id=product.id,
                                variant_hash=new_hash,
                            )
                update_kwargs["variant_attributes"] = command.variant_attributes
                update_kwargs["variant_hash"] = new_hash

            sku.update(**update_kwargs)

            # purchase_price has its own setter that arms recompute (ADR-005)
            if command.purchase_price is not None:
                try:
                    purchase_currency = PurchaseCurrency(
                        command.purchase_price.currency
                    )
                except ValueError as exc:
                    raise ValidationError(
                        message=(
                            f"purchase_price.currency '{command.purchase_price.currency}'"
                            " is not supported (use RUB or CNY)"
                        ),
                        error_code="INVALID_PURCHASE_CURRENCY",
                    ) from exc
                changed = sku.set_purchase_price(
                    purchase_price=command.purchase_price,
                    purchase_currency=purchase_currency,
                )
                # CAT-010 — emit on aggregate root only when value actually
                # changed; idempotent re-submits skip the event.
                if changed:
                    product.add_domain_event(
                        SKUPurchasePriceUpdatedEvent(
                            product_id=product.id,
                            variant_id=sku.variant_id,
                            sku_id=sku.id,
                            purchase_price_amount=command.purchase_price.amount,
                            purchase_currency=purchase_currency.value,
                            aggregate_id=str(product.id),
                        )
                    )

            await self._product_repo.update(product)
            self._uow.register_aggregate(product)
            await self._uow.commit()

        try:
            await self._cache.delete(storefront_pdp_cache_key(product.slug))
        except RedisError as exc:  # pragma: no cover
            # Stale PDP cache means customers see the OLD purchase price
            # until TTL — surface as ``error`` so operators alert on it,
            # not just a quiet warning. CAT-018 H5: also narrowed from
            # ``except Exception`` so programmer errors propagate.
            self._logger.error(
                "pdp_cache_invalidation_failed",
                product_id=str(command.product_id),
                slug=product.slug,
                error=str(exc),
            )

        return UpdateSKUResult(id=sku.id, version=sku.version)
