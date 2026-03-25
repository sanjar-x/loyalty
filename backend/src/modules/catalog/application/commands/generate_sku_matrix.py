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
    AttributeLevelMismatchError,
    AttributeNotFoundError,
    AttributeNotInFamilyError,
    AttributeValueNotFoundError,
    DuplicateVariantCombinationError,
    ProductNotFoundError,
)
from src.modules.catalog.domain.interfaces import (
    IAttributeFamilyRepository,
    IAttributeRepository,
    IAttributeValueRepository,
    ICategoryRepository,
    IFamilyAttributeBindingRepository,
    IFamilyAttributeExclusionRepository,
    IProductRepository,
)
from src.modules.catalog.domain.value_objects import AttributeLevel, Money
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
        attribute_repo: IAttributeRepository,
        attribute_value_repo: IAttributeValueRepository,
        category_repo: ICategoryRepository,
        family_repo: IAttributeFamilyRepository,
        family_binding_repo: IFamilyAttributeBindingRepository,
        exclusion_repo: IFamilyAttributeExclusionRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._product_repo = product_repo
        self._attribute_repo = attribute_repo
        self._attribute_value_repo = attribute_value_repo
        self._category_repo = category_repo
        self._family_repo = family_repo
        self._family_binding_repo = family_binding_repo
        self._exclusion_repo = exclusion_repo
        self._uow = uow
        self._logger = logger.bind(handler="GenerateSKUMatrixHandler")

    async def handle(
        self, command: GenerateSKUMatrixCommand
    ) -> GenerateSKUMatrixResult:
        """Execute the generate-SKU-matrix command.

        Validates attribute level (must be VARIANT), attribute values exist,
        and attributes belong to the product's category family.
        """
        async with self._uow:
            product = await self._product_repo.get_with_variants(command.product_id)
            if product is None:
                raise ProductNotFoundError(product_id=command.product_id)

            # --- Validate attributes: level, values, family membership ---
            await self._validate_selections(product, command.attribute_selections)

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

    async def _validate_selections(
        self,
        product: Product,
        selections: list[AttributeSelection],
    ) -> None:
        """Validate that all attribute selections are variant-level, values exist, and belong to family."""
        # Resolve effective attribute IDs from family (if category has family)
        effective_attr_ids: set[uuid.UUID] | None = None
        category = await self._category_repo.get(product.primary_category_id)
        if category is not None and category.family_id is not None:
            chain = await self._family_repo.get_ancestor_chain(category.family_id)
            chain_ids = [f.id for f in chain]
            all_bindings = await self._family_binding_repo.get_bindings_for_families(
                chain_ids
            )
            all_exclusions = await self._exclusion_repo.get_exclusions_for_families(
                chain_ids
            )

            effective_attr_ids = set()
            for fam in chain:
                for excluded_id in all_exclusions.get(fam.id, set()):
                    effective_attr_ids.discard(excluded_id)
                for binding in all_bindings.get(fam.id, []):
                    effective_attr_ids.add(binding.attribute_id)

        for sel in selections:
            # Check attribute exists and is variant-level
            attribute = await self._attribute_repo.get(sel.attribute_id)
            if attribute is None:
                raise AttributeNotFoundError(attribute_id=sel.attribute_id)
            if attribute.level != AttributeLevel.VARIANT:
                raise AttributeLevelMismatchError(
                    attribute_id=sel.attribute_id,
                    expected_level="variant",
                    actual_level=attribute.level.value,
                )

            # Check family membership
            if (
                effective_attr_ids is not None
                and sel.attribute_id not in effective_attr_ids
            ):
                raise AttributeNotInFamilyError(
                    product_id=product.id,
                    attribute_id=sel.attribute_id,
                )

            # Validate all value_ids exist and belong to the attribute
            for value_id in sel.value_ids:
                attr_value = await self._attribute_value_repo.get(value_id)
                if attr_value is None:
                    raise AttributeValueNotFoundError(value_id=value_id)
                if attr_value.attribute_id != sel.attribute_id:
                    raise AttributeValueNotFoundError(value_id=value_id)

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
