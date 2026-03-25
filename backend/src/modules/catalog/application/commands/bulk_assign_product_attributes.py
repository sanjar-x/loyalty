"""Bulk assign product-level attributes in a single transaction."""

import uuid
from dataclasses import dataclass, field
from typing import Any

from src.modules.catalog.domain.entities import ProductAttributeValue
from src.modules.catalog.domain.exceptions import (
    AttributeNotDictionaryError,
    AttributeNotFoundError,
    AttributeNotInFamilyError,
    AttributeLevelMismatchError,
    AttributeValueNotFoundError,
    DuplicateProductAttributeError,
    ProductNotFoundError,
)
from src.modules.catalog.domain.value_objects import AttributeLevel
from src.modules.catalog.domain.interfaces import (
    IAttributeFamilyRepository,
    IAttributeRepository,
    IAttributeValueRepository,
    ICategoryRepository,
    IFamilyAttributeBindingRepository,
    IFamilyAttributeExclusionRepository,
    IProductAttributeValueRepository,
    IProductRepository,
)
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class AttributeAssignmentItem:
    attribute_id: uuid.UUID
    attribute_value_id: uuid.UUID


@dataclass(frozen=True)
class BulkAssignProductAttributesCommand:
    product_id: uuid.UUID
    items: list[AttributeAssignmentItem]


@dataclass(frozen=True)
class BulkAssignProductAttributesResult:
    assigned_count: int
    pav_ids: list[uuid.UUID]


class BulkAssignProductAttributesHandler:
    def __init__(
        self,
        product_repo: IProductRepository,
        pav_repo: IProductAttributeValueRepository,
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
        self._pav_repo = pav_repo
        self._attribute_repo = attribute_repo
        self._attribute_value_repo = attribute_value_repo
        self._category_repo = category_repo
        self._family_repo = family_repo
        self._family_binding_repo = family_binding_repo
        self._exclusion_repo = exclusion_repo
        self._uow = uow
        self._logger = logger.bind(handler="BulkAssignProductAttributesHandler")

    async def handle(
        self, command: BulkAssignProductAttributesCommand
    ) -> BulkAssignProductAttributesResult:
        async with self._uow:
            # 1. Validate product exists
            product = await self._product_repo.get(command.product_id)
            if product is None:
                raise ProductNotFoundError(product_id=command.product_id)

            # 2. Resolve effective attribute IDs from family (if category has family)
            effective_attr_ids: set[uuid.UUID] | None = None
            category = await self._category_repo.get(product.primary_category_id)
            if category is not None and category.family_id is not None:
                chain = await self._family_repo.get_ancestor_chain(category.family_id)
                chain_ids = [f.id for f in chain]
                all_bindings = (
                    await self._family_binding_repo.get_bindings_for_families(chain_ids)
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

            # 3. Batch-prefetch all attributes and values (avoid N+1)
            attr_ids = [item.attribute_id for item in command.items]
            val_ids = [item.attribute_value_id for item in command.items]

            attrs_by_id: dict[uuid.UUID, Any] = {}
            for aid in attr_ids:
                a = await self._attribute_repo.get(aid)
                if a is not None:
                    attrs_by_id[a.id] = a

            vals_by_id: dict[uuid.UUID, Any] = {}
            for vid in val_ids:
                v = await self._attribute_value_repo.get(vid)
                if v is not None:
                    vals_by_id[v.id] = v

            # 4. Validate and create all assignments
            pav_ids: list[uuid.UUID] = []

            for item in command.items:
                # Check family membership
                if (
                    effective_attr_ids is not None
                    and item.attribute_id not in effective_attr_ids
                ):
                    raise AttributeNotInFamilyError(
                        product_id=command.product_id,
                        attribute_id=item.attribute_id,
                    )

                # Validate attribute exists, is dictionary, and is product-level
                attribute = attrs_by_id.get(item.attribute_id)
                if attribute is None:
                    raise AttributeNotFoundError(attribute_id=item.attribute_id)
                if attribute.level != AttributeLevel.PRODUCT:
                    raise AttributeLevelMismatchError(
                        attribute_id=item.attribute_id,
                        expected_level="product",
                        actual_level=attribute.level.value,
                    )
                if not attribute.is_dictionary:
                    raise AttributeNotDictionaryError(attribute_id=item.attribute_id)

                # Validate value exists and belongs to attribute
                attr_value = vals_by_id.get(item.attribute_value_id)
                if attr_value is None:
                    raise AttributeValueNotFoundError(value_id=item.attribute_value_id)
                if attr_value.attribute_id != item.attribute_id:
                    raise AttributeValueNotFoundError(value_id=item.attribute_value_id)

                # Check no duplicate
                if await self._pav_repo.check_assignment_exists(
                    command.product_id, item.attribute_id
                ):
                    raise DuplicateProductAttributeError(
                        product_id=command.product_id,
                        attribute_id=item.attribute_id,
                    )

                # Create assignment
                pav = ProductAttributeValue.create(
                    product_id=command.product_id,
                    attribute_id=item.attribute_id,
                    attribute_value_id=item.attribute_value_id,
                )
                await self._pav_repo.add(pav)
                pav_ids.append(pav.id)

            await self._uow.commit()

        return BulkAssignProductAttributesResult(
            assigned_count=len(pav_ids),
            pav_ids=pav_ids,
        )
