"""Bulk assign product-level attributes in a single transaction."""

import uuid
from dataclasses import dataclass

from src.modules.catalog.application.queries.resolve_template_attributes import (
    resolve_effective_attribute_ids,
)
from src.modules.catalog.domain.entities import ProductAttributeValue
from src.modules.catalog.domain.exceptions import (
    AttributeLevelMismatchError,
    AttributeNotDictionaryError,
    AttributeNotFoundError,
    AttributeNotInTemplateError,
    AttributeValueNotFoundError,
    DuplicateProductAttributeError,
    ProductNotFoundError,
)
from src.modules.catalog.domain.interfaces import (
    IAttributeRepository,
    IAttributeTemplateRepository,
    IAttributeValueRepository,
    ICategoryRepository,
    IProductAttributeValueRepository,
    IProductRepository,
    ITemplateAttributeBindingRepository,
)
from src.modules.catalog.domain.value_objects import AttributeLevel
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
        template_repo: IAttributeTemplateRepository,
        template_binding_repo: ITemplateAttributeBindingRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._product_repo = product_repo
        self._pav_repo = pav_repo
        self._attribute_repo = attribute_repo
        self._attribute_value_repo = attribute_value_repo
        self._category_repo = category_repo
        self._template_repo = template_repo
        self._template_binding_repo = template_binding_repo
        self._uow = uow
        self._logger = logger.bind(handler="BulkAssignProductAttributesHandler")

    async def handle(  # noqa: C901
        self, command: BulkAssignProductAttributesCommand
    ) -> BulkAssignProductAttributesResult:
        if len(command.items) > 100:
            raise ValueError("Cannot assign more than 100 attributes at once")

        async with self._uow:
            # 1. Validate product exists
            product = await self._product_repo.get(command.product_id)
            if product is None:
                raise ProductNotFoundError(product_id=command.product_id)

            # 2. Resolve effective attribute IDs from template (if category has template)
            effective_attr_ids: set[uuid.UUID] | None = None
            category = await self._category_repo.get(product.primary_category_id)
            if category is not None and category.effective_template_id is not None:
                effective_attr_ids = await resolve_effective_attribute_ids(
                    self._template_binding_repo,
                    category.effective_template_id,
                )

            # 3. Check for duplicates within the batch
            seen_attr_ids: set[uuid.UUID] = set()
            for item in command.items:
                if item.attribute_id in seen_attr_ids:
                    raise DuplicateProductAttributeError(
                        product_id=command.product_id,
                        attribute_id=item.attribute_id,
                    )
                seen_attr_ids.add(item.attribute_id)

            # 4. Batch-prefetch all attributes and values (avoid N+1)
            attr_ids = [item.attribute_id for item in command.items]
            val_ids = [item.attribute_value_id for item in command.items]

            attrs_by_id = await self._attribute_repo.get_many(attr_ids)
            vals_by_id = await self._attribute_value_repo.get_many(val_ids)

            # 5. Bulk-check existing assignments (avoid N+1)
            existing_assignments = await self._pav_repo.check_assignments_exist_bulk(
                command.product_id, attr_ids
            )

            # 6. Validate and create all assignments
            pav_ids: list[uuid.UUID] = []

            for item in command.items:
                # Check template membership
                if (
                    effective_attr_ids is not None
                    and item.attribute_id not in effective_attr_ids
                ):
                    raise AttributeNotInTemplateError(
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
                if item.attribute_id in existing_assignments:
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
