"""Command handler: update an existing product variant.

Fetches the product aggregate with its variants, locates the target
variant, builds update kwargs from provided fields, and delegates
mutation to ``ProductVariant.update()``.

Part of the application layer (CQRS write side).
"""

import uuid
from dataclasses import dataclass, field

from src.modules.catalog.application.constants import storefront_pdp_cache_key
from src.modules.catalog.domain.exceptions import (
    ProductNotFoundError,
    VariantNotFoundError,
)
from src.modules.catalog.domain.interfaces import IProductRepository
from src.modules.catalog.domain.value_objects import Money
from shared.exceptions import OptimisticLockError
from shared.interfaces.cache import ICacheService
from shared.interfaces.logger import ILogger
from shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class UpdateVariantCommand:
    """Input for updating an existing product variant.

    All fields except ``product_id`` and ``variant_id`` are optional;
    omitting a field means "keep the current value". Pass ``None``
    explicitly for ``description_i18n`` or ``default_price`` (with the
    field name in ``_provided_fields``) to clear the value.

    Attributes:
        product_id: UUID of the product that owns the variant.
        variant_id: UUID of the variant to update.
        name_i18n: New multilingual name, or None to keep current.
        description_i18n: New description, None to clear, or absent to keep.
        sort_order: New sort order, or None to keep current.
        default_price: New default price as a domain ``Money``, ``None``
            to clear, or absent (not in ``_provided_fields``) to keep
            unchanged. (CAT-001 — was ``default_price_amount`` /
            ``default_price_currency`` split fields.)
        _provided_fields: Set of field names explicitly provided by the caller.
    """

    product_id: uuid.UUID
    variant_id: uuid.UUID
    name_i18n: dict[str, str] | None = None
    description_i18n: dict[str, str] | None = None
    sort_order: int | None = None
    default_price: Money | None = None
    _provided_fields: frozenset[str] = field(default_factory=frozenset)
    expected_version: int | None = None
    """T-1.3 — when set, the handler enforces optimistic locking before
    mutating the variant: ``ProductVariant.version`` mismatch raises
    :class:`OptimisticLockError`. ``None`` (default) keeps the legacy
    last-write-wins behaviour."""


@dataclass(frozen=True)
class UpdateVariantResult:
    """Output of a successful variant update.

    Attributes:
        id: UUID of the updated variant.
        version: Post-mutation optimistic-lock counter.
    """

    id: uuid.UUID
    version: int = 0


class UpdateVariantHandler:
    """Apply partial updates to an existing product variant.

    Orchestrates: fetch product with variants -> find variant ->
    build update kwargs -> delegate to ProductVariant.update() ->
    persist -> commit.
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
        self._logger = logger.bind(handler="UpdateVariantHandler")

    async def handle(self, command: UpdateVariantCommand) -> UpdateVariantResult:
        """Execute the update-variant command.

        Args:
            command: Variant update parameters.

        Returns:
            Result containing the updated variant ID.

        Raises:
            ProductNotFoundError: If no product exists with the given ID.
            VariantNotFoundError: If no active variant with the given ID
                exists within the product.
            ValueError: If name_i18n is empty (propagated from domain).
        """
        async with self._uow:
            product = await self._product_repo.get_for_update_with_variants(
                command.product_id
            )
            if product is None:
                raise ProductNotFoundError(product_id=command.product_id)

            variant = product.find_variant(command.variant_id)
            if variant is None:
                raise VariantNotFoundError(
                    variant_id=command.variant_id, product_id=command.product_id
                )

            # T-1.3 — early optimistic-lock check on the variant version
            # when an expected value was provided (typically via the
            # router's ``If-Match`` header).
            if (
                command.expected_version is not None
                and command.expected_version != variant.version
            ):
                raise OptimisticLockError(
                    entity_type="ProductVariant",
                    entity_id=variant.id,
                    expected_version=command.expected_version,
                    actual_version=variant.version,
                )

            update_kwargs: dict[str, object] = {}

            if "name_i18n" in command._provided_fields:
                update_kwargs["name_i18n"] = command.name_i18n

            if "description_i18n" in command._provided_fields:
                update_kwargs["description_i18n"] = command.description_i18n

            if "sort_order" in command._provided_fields:
                update_kwargs["sort_order"] = command.sort_order

            if "default_price" in command._provided_fields:
                update_kwargs["default_price"] = command.default_price
                if command.default_price is not None:
                    update_kwargs["default_currency"] = command.default_price.currency

            if update_kwargs:
                variant.update(**update_kwargs)

            # T-1.3 — ``ProductRepository.update`` propagates post-
            # flush variant version bumps back onto the domain
            # variants in-place, so ``variant.version`` is the new
            # ETag value once the call returns.
            await self._product_repo.update(product)
            self._uow.register_aggregate(product)
            await self._uow.commit()

        try:
            await self._cache.delete(storefront_pdp_cache_key(product.slug))
        except Exception as exc:  # pragma: no cover
            self._logger.warning("pdp_cache_invalidation_failed", error=str(exc))

        self._logger.info(
            "Variant updated",
            variant_id=str(variant.id),
            product_id=str(command.product_id),
        )
        return UpdateVariantResult(id=variant.id, version=variant.version)
