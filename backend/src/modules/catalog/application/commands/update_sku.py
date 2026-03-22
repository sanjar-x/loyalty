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

from src.modules.catalog.domain.exceptions import (
    ConcurrencyError,
    DuplicateVariantCombinationError,
    ProductNotFoundError,
    SKUNotFoundError,
)
from src.modules.catalog.domain.interfaces import IProductRepository
from src.modules.catalog.domain.value_objects import Money
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class UpdateSKUCommand:
    """Input for updating an existing SKU variant.

    All fields except ``product_id`` and ``sku_id`` are optional; omitting
    a field (or leaving it at its default) means "keep the current value".
    Pass ``None`` explicitly for ``compare_at_price_amount`` to *clear* the
    compare-at price; leaving it out of ``_provided_fields`` keeps it unchanged.

    Attributes:
        product_id: UUID of the product that owns the SKU.
        sku_id: UUID of the SKU to update.
        sku_code: New stock-keeping code, or None to keep current.
        price_amount: New price in smallest currency units, or None to keep.
        price_currency: Currency code for the new price, or None to keep.
        compare_at_price_amount: New compare-at price amount, None to clear,
            or absent (not in _provided_fields) to keep unchanged.
        is_active: New active flag, or None to keep current.
        variant_attributes: New variant attribute pairs, or None to keep.
        version: Expected SKU version for optimistic locking, or None to skip.
    """

    product_id: uuid.UUID
    sku_id: uuid.UUID
    sku_code: str | None = None
    price_amount: int | None = None
    price_currency: str | None = None
    compare_at_price_amount: int | None = None
    is_active: bool | None = None
    variant_attributes: list[tuple[uuid.UUID, uuid.UUID]] | None = None
    version: int | None = None
    _provided_fields: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True)
class UpdateSKUResult:
    """Output of a successful SKU update.

    Attributes:
        id: UUID of the updated SKU.
    """

    id: uuid.UUID


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
    ) -> None:
        self._product_repo = product_repo
        self._uow = uow

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
            product = await self._product_repo.get_with_variants(command.product_id)
            if product is None:
                raise ProductNotFoundError(product_id=command.product_id)

            sku = product.find_sku(command.sku_id)
            if sku is None:
                raise SKUNotFoundError(sku_id=command.sku_id)

            # --- Optimistic locking: API-level version guard ---
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
                update_kwargs["sku_code"] = command.sku_code

            # Build Money for price if provided.  Use existing currency
            # when only the amount changes, and vice versa.
            if command.price_amount is not None or command.price_currency is not None:
                new_amount = (
                    command.price_amount
                    if command.price_amount is not None
                    else (sku.price.amount if sku.price is not None else 0)
                )
                new_currency = (
                    command.price_currency
                    if command.price_currency is not None
                    else (sku.price.currency if sku.price is not None else "RUB")
                )
                update_kwargs["price"] = Money(amount=new_amount, currency=new_currency)

            # Handle compare_at_price via _provided_fields.
            if "compare_at_price_amount" in command._provided_fields:
                if command.compare_at_price_amount is None:
                    # Caller explicitly wants to clear compare_at_price.
                    update_kwargs["compare_at_price"] = None
                else:
                    # Build Money for compare_at_price.  Use the effective
                    # price currency (new if being changed, else existing).
                    effective_currency = (
                        command.price_currency
                        if command.price_currency is not None
                        else (sku.price.currency if sku.price is not None else "RUB")
                    )
                    update_kwargs["compare_at_price"] = Money(
                        amount=command.compare_at_price_amount,
                        currency=effective_currency,
                    )

            if command.is_active is not None:
                update_kwargs["is_active"] = command.is_active

            # --- Variant attributes: re-compute hash and check uniqueness ---
            if command.variant_attributes is not None:
                new_hash = product.compute_variant_hash(command.variant_attributes)
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

            sku.update(**update_kwargs)  # type: ignore[arg-type]

            await self._product_repo.update(product)
            self._uow.register_aggregate(product)
            await self._uow.commit()

        return UpdateSKUResult(id=sku.id)
