"""
Command handler: add a SKU variant to an existing product.

Fetches the product aggregate with its SKUs, constructs a Money value
object for pricing, delegates SKU creation to ``Product.add_sku()``
(which computes the variant hash and enforces uniqueness), and persists
the result. Part of the application layer (CQRS write side).
"""

import uuid
from dataclasses import dataclass, field

from src.modules.catalog.domain.exceptions import ProductNotFoundError
from src.modules.catalog.domain.interfaces import IProductRepository
from src.modules.catalog.domain.value_objects import Money
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class AddSKUCommand:
    """Input for adding a new SKU variant to a product.

    Attributes:
        product_id: UUID of the product to add the SKU to.
        sku_code: Human-readable stock-keeping code.
        price_amount: Price in smallest currency units (e.g. kopecks).
        price_currency: 3-character ISO 4217 currency code.
        compare_at_price_amount: Optional strikethrough price amount.
            Must be greater than ``price_amount`` when provided.
        is_active: Whether the variant is immediately available for sale.
        variant_attributes: List of (attribute_id, attribute_value_id) pairs
            that uniquely identify this variant combination.
    """

    product_id: uuid.UUID
    variant_id: uuid.UUID
    sku_code: str
    price_amount: int | None = None
    price_currency: str = "RUB"
    compare_at_price_amount: int | None = None
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
    ) -> None:
        self._product_repo = product_repo
        self._uow = uow

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
            product = await self._product_repo.get_with_variants(command.product_id)
            if product is None:
                raise ProductNotFoundError(product_id=command.product_id)

            if command.compare_at_price_amount is not None and command.price_amount is None:
                raise ValueError("compare_at_price cannot be set when price is not provided")

            price: Money | None = None
            if command.price_amount is not None:
                price = Money(
                    amount=command.price_amount,
                    currency=command.price_currency,
                )

            compare_at_price: Money | None = None
            if command.compare_at_price_amount is not None:
                if (
                    command.price_amount is not None
                    and command.compare_at_price_amount <= command.price_amount
                ):
                    raise ValueError("compare_at_price must be greater than price")
                compare_at_price = Money(
                    amount=command.compare_at_price_amount,
                    currency=command.price_currency,
                )

            sku = product.add_sku(
                variant_id=command.variant_id,
                sku_code=command.sku_code,
                price=price,
                compare_at_price=compare_at_price,
                is_active=command.is_active,
                variant_attributes=command.variant_attributes
                if command.variant_attributes
                else None,
            )

            await self._product_repo.update(product)
            self._uow.register_aggregate(product)
            await self._uow.commit()

        return AddSKUResult(sku_id=sku.id)
