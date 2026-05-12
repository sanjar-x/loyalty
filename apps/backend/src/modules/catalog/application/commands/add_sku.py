"""
Command handler: add a SKU variant to an existing product.

Fetches the product aggregate with its SKUs, constructs a Money value
object for pricing, delegates SKU creation to ``Product.add_sku()``
(which computes the variant hash and enforces uniqueness), and persists
the result. Part of the application layer (CQRS write side).
"""

import uuid
from dataclasses import dataclass, field

from src.modules.catalog.application.constants import storefront_pdp_cache_key
from src.modules.catalog.domain.exceptions import (
    ProductNotFoundError,
    SKUCodeConflictError,
)
from src.modules.catalog.domain.interfaces import IProductRepository
from src.modules.catalog.domain.value_objects import Money, PurchaseCurrency
from shared.exceptions import ValidationError
from shared.interfaces.cache import ICacheService
from shared.interfaces.logger import ILogger
from shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class AddSKUCommand:
    """Input for adding a new SKU variant to a product.

    Attributes:
        product_id: UUID of the product to add the SKU to.
        sku_code: Human-readable stock-keeping code.
        price: Optional manual selling price (legacy fallback before
            pricing recompute lands a value).
        compare_at_price: Optional strikethrough price; must be greater
            than ``price.amount`` when provided.
        purchase_price: Wholesale cost in ``RUB`` or ``CNY`` (CAT-001).
            Drives autonomous pricing recompute.
        is_active: Whether the variant is immediately available for sale.
        variant_attributes: List of (attribute_id, attribute_value_id)
            pairs that uniquely identify this variant combination.
    """

    product_id: uuid.UUID
    variant_id: uuid.UUID
    sku_code: str
    price: Money | None = None
    compare_at_price: Money | None = None
    purchase_price: Money | None = None
    is_active: bool = True
    variant_attributes: list[tuple[uuid.UUID, uuid.UUID]] = field(default_factory=list)


@dataclass(frozen=True)
class AddSKUResult:
    """Output of a successful SKU addition.

    Attributes:
        sku_id: UUID of the newly created SKU.
    """

    sku_id: uuid.UUID


class AddSKUHandler:
    """Add a new SKU variant to an existing product.

    Validates pricing, delegates variant hash computation and uniqueness
    checking to the Product aggregate, and persists the result.
    No domain events are emitted (product lifecycle events are deferred).
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
        self._logger = logger.bind(handler="AddSKUHandler")

    async def handle(self, command: AddSKUCommand) -> AddSKUResult:
        """Execute the add-SKU command.

        Args:
            command: SKU creation parameters.

        Returns:
            Result containing the new SKU's UUID.

        Raises:
            ProductNotFoundError: If no product exists with the given ID.
            ValueError: If ``compare_at_price_amount`` is provided but is
                not greater than ``price_amount``.
            DuplicateVariantCombinationError: If an active SKU with the same
                variant attribute combination already exists (propagated from
                ``Product.add_sku()``).
        """
        async with self._uow:
            product = await self._product_repo.get_for_update_with_variants(
                command.product_id
            )
            if product is None:
                raise ProductNotFoundError(product_id=command.product_id)

            if await self._product_repo.check_sku_code_exists(command.sku_code):
                raise SKUCodeConflictError(
                    sku_code=command.sku_code, product_id=command.product_id
                )

            if command.compare_at_price is not None:
                if command.price is None:
                    raise ValidationError(
                        message="compare_at_price requires a base price",
                        error_code="INVALID_PRICE",
                    )
                if command.compare_at_price.currency != command.price.currency:
                    raise ValidationError(
                        message="compare_at_price.currency must match price.currency",
                        error_code="INVALID_PRICE",
                    )
                if command.compare_at_price.amount <= command.price.amount:
                    raise ValidationError(
                        message="compare_at_price must be greater than price",
                        error_code="INVALID_PRICE",
                    )

            purchase_currency_vo: PurchaseCurrency | None = None
            if command.purchase_price is not None:
                try:
                    purchase_currency_vo = PurchaseCurrency(
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

            sku = product.add_sku(
                variant_id=command.variant_id,
                sku_code=command.sku_code,
                price=command.price,
                compare_at_price=command.compare_at_price,
                purchase_price=command.purchase_price,
                purchase_currency=purchase_currency_vo,
                is_active=command.is_active,
                variant_attributes=command.variant_attributes
                if command.variant_attributes
                else None,
            )

            await self._product_repo.update(product)
            self._uow.register_aggregate(product)
            await self._uow.commit()

        try:
            await self._cache.delete(storefront_pdp_cache_key(product.slug))
        except Exception as exc:  # pragma: no cover
            self._logger.warning("pdp_cache_invalidation_failed", error=str(exc))

        self._logger.info(
            "SKU added to product",
            sku_id=str(sku.id),
            product_id=str(command.product_id),
        )
        return AddSKUResult(sku_id=sku.id)
