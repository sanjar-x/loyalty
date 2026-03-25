"""
Command handler: bulk-generate SKU combinations from attribute selections.

Accepts a list of attribute selections (each with multiple values),
computes the cartesian product, and creates one SKU per combination
in a single Unit-of-Work transaction.  Existing attribute combinations
are silently skipped (not errored).  Part of the application layer
(CQRS write side).
"""

import uuid
from dataclasses import dataclass, field
from itertools import product as cartesian_product

from src.modules.catalog.application.constants import DEFAULT_CURRENCY
from src.modules.catalog.domain.entities import Product
from src.modules.catalog.domain.exceptions import (
    DuplicateVariantCombinationError,
    ProductNotFoundError,
)
from src.modules.catalog.domain.interfaces import IProductRepository
from src.modules.catalog.domain.value_objects import Money
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class AttributeSelection:
    """One attribute with multiple selected values."""

    attribute_id: uuid.UUID
    value_ids: list[uuid.UUID]


@dataclass(frozen=True)
class GenerateSKUMatrixCommand:
    """Input for bulk SKU matrix generation.

    Attributes:
        product_id: UUID of the product to add SKUs to.
        variant_id: UUID of the variant that will own the new SKUs.
        attribute_selections: List of attribute selections whose cartesian
            product defines the SKU combinations.
        price_amount: Optional price in smallest currency units.
        price_currency: 3-character ISO 4217 currency code.
        compare_at_price_amount: Optional strikethrough price amount.
        is_active: Whether generated SKUs are immediately available.
    """

    product_id: uuid.UUID
    variant_id: uuid.UUID
    attribute_selections: list[AttributeSelection]
    price_amount: int | None = None
    price_currency: str = DEFAULT_CURRENCY
    compare_at_price_amount: int | None = None
    is_active: bool = True


@dataclass(frozen=True)
class GenerateSKUMatrixResult:
    """Output of a successful SKU matrix generation.

    Attributes:
        created_count: Number of SKUs actually created.
        skipped_count: Number of combinations skipped (already existing).
        sku_ids: UUIDs of all newly created SKUs.
    """

    created_count: int
    skipped_count: int
    sku_ids: list[uuid.UUID] = field(default_factory=list)


class GenerateSKUMatrixHandler:
    """Generate SKU combinations from a cartesian product of attribute selections.

    Loads the product aggregate, computes all attribute value combinations,
    attempts to create one SKU per combination, and persists the result in
    a single Unit-of-Work transaction.  Duplicate variant combinations
    (same attribute hash) are silently skipped.
    """

    def __init__(
        self,
        product_repo: IProductRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._product_repo = product_repo
        self._uow = uow
        self._logger = logger.bind(handler="GenerateSKUMatrixHandler")

    async def handle(self, command: GenerateSKUMatrixCommand) -> GenerateSKUMatrixResult:
        """Execute the generate-SKU-matrix command.

        Args:
            command: SKU matrix generation parameters.

        Returns:
            Result containing created/skipped counts and new SKU UUIDs.

        Raises:
            ProductNotFoundError: If no product exists with the given ID.
        """
        async with self._uow:
            product = await self._product_repo.get_with_variants(command.product_id)
            if product is None:
                raise ProductNotFoundError(product_id=command.product_id)

            # Build price/compare_at_price pair
            if command.price_amount is not None:
                price, compare_at_price = Money.from_primitives(
                    amount=command.price_amount,
                    currency=command.price_currency,
                    compare_at_amount=command.compare_at_price_amount,
                )
            else:
                price, compare_at_price = None, None

            # Generate cartesian product of attribute selections
            combinations = self._build_combinations(command.attribute_selections)

            created_ids: list[uuid.UUID] = []
            skipped = 0

            for i, combo in enumerate(combinations):
                # Auto-generate sku_code from product slug + index
                sku_code = self._generate_sku_code(product, combo, i)

                # Check if sku_code already exists; append suffix if so
                if await self._product_repo.check_sku_code_exists(sku_code):
                    sku_code = f"{sku_code}-{i + 1}"

                try:
                    sku = product.add_sku(
                        variant_id=command.variant_id,
                        sku_code=sku_code,
                        price=price,
                        compare_at_price=compare_at_price,
                        is_active=command.is_active,
                        variant_attributes=combo,
                    )
                    created_ids.append(sku.id)
                except DuplicateVariantCombinationError:
                    skipped += 1
                    continue

            # Persist all SKUs in a single transaction
            await self._product_repo.update(product)
            self._uow.register_aggregate(product)
            await self._uow.commit()

        self._logger.info(
            "SKU matrix generated",
            product_id=str(command.product_id),
            variant_id=str(command.variant_id),
            created=len(created_ids),
            skipped=skipped,
        )
        return GenerateSKUMatrixResult(
            created_count=len(created_ids),
            skipped_count=skipped,
            sku_ids=created_ids,
        )

    @staticmethod
    def _build_combinations(
        selections: list[AttributeSelection],
    ) -> list[list[tuple[uuid.UUID, uuid.UUID]]]:
        """Build cartesian product of attribute selections.

        Example:
            selections = [
                AttributeSelection(attr_id=size, value_ids=[S, M]),
                AttributeSelection(attr_id=color, value_ids=[white, black]),
            ]
            result = [
                [(size, S), (color, white)],
                [(size, S), (color, black)],
                [(size, M), (color, white)],
                [(size, M), (color, black)],
            ]
        """
        if not selections:
            return [[]]

        per_attr: list[list[tuple[uuid.UUID, uuid.UUID]]] = []
        for sel in selections:
            pairs = [(sel.attribute_id, vid) for vid in sel.value_ids]
            per_attr.append(pairs)

        return [list(combo) for combo in cartesian_product(*per_attr)]

    @staticmethod
    def _generate_sku_code(
        product: Product,
        combo: list[tuple[uuid.UUID, uuid.UUID]],
        index: int,
    ) -> str:
        """Generate a deterministic SKU code from product slug + combination index.

        Args:
            product: The product aggregate (used for its slug).
            combo: List of (attribute_id, attribute_value_id) tuples.
            index: Zero-based index within the generated matrix.

        Returns:
            A string like ``"nike-air-force-001"``.
        """
        return f"{product.slug}-{index + 1:03d}"
