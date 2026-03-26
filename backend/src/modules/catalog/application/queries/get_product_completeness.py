"""
Query handler: product attribute completeness check.

Compares a product's filled attribute values against the template
requirements inherited via its primary category. Returns fill ratios
for required and recommended bindings.
Strict CQRS read side -- queries the ORM directly.
"""

import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.domain.exceptions import ProductNotFoundError
from src.modules.catalog.domain.value_objects import RequirementLevel
from src.modules.catalog.infrastructure.models import (
    Attribute as OrmAttribute,
    Category as OrmCategory,
    Product as OrmProduct,
    ProductAttributeValue as OrmProductAttributeValue,
    TemplateAttributeBinding as OrmTemplateAttributeBinding,
)
from src.shared.interfaces.logger import ILogger


@dataclass(frozen=True)
class ProductCompletenessQuery:
    """Input for the product completeness check.

    Attributes:
        product_id: UUID of the product to check.
    """

    product_id: uuid.UUID


@dataclass
class ProductCompletenessResult:
    """Output of the product completeness check.

    Attributes:
        is_complete: True when all required bindings have values.
        total_required: Number of required attribute bindings.
        filled_required: Number of required bindings with values.
        total_recommended: Number of recommended attribute bindings.
        filled_recommended: Number of recommended bindings with values.
        missing_required: List of missing required attributes [{attribute_id, code, name_i18n}].
        missing_recommended: List of missing recommended attributes [{attribute_id, code, name_i18n}].
    """

    is_complete: bool = True
    total_required: int = 0
    filled_required: int = 0
    total_recommended: int = 0
    filled_recommended: int = 0
    missing_required: list[dict[str, Any]] = field(default_factory=list)
    missing_recommended: list[dict[str, Any]] = field(default_factory=list)


class GetProductCompletenessHandler:
    """Check product attribute completeness against template requirements."""

    def __init__(self, session: AsyncSession, logger: ILogger) -> None:
        self._session = session
        self._logger = logger.bind(handler="GetProductCompletenessHandler")

    async def handle(
        self, query: ProductCompletenessQuery
    ) -> ProductCompletenessResult:
        """Execute the product completeness check.

        Args:
            query: Contains the product_id to check.

        Returns:
            Completeness result with fill ratios and missing attributes.

        Raises:
            ProductNotFoundError: If the product does not exist.
        """
        # 1. Load product -> get primary_category_id
        product_row = (
            await self._session.execute(
                select(OrmProduct.id, OrmProduct.primary_category_id).where(
                    OrmProduct.id == query.product_id,
                    OrmProduct.deleted_at.is_(None),
                )
            )
        ).one_or_none()
        if product_row is None:
            raise ProductNotFoundError(product_id=query.product_id)

        # 2. Load category -> get effective_template_id
        category_row = (
            await self._session.execute(
                select(OrmCategory.effective_template_id).where(
                    OrmCategory.id == product_row.primary_category_id
                )
            )
        ).one_or_none()

        if category_row is None or category_row.effective_template_id is None:
            # No template => 100% complete (no requirements)
            return ProductCompletenessResult(is_complete=True)

        effective_template_id = category_row.effective_template_id

        # 3. Load template bindings for this template
        binding_stmt = select(
            OrmTemplateAttributeBinding.attribute_id,
            OrmTemplateAttributeBinding.requirement_level,
        ).where(OrmTemplateAttributeBinding.template_id == effective_template_id)
        binding_rows = (await self._session.execute(binding_stmt)).all()

        if not binding_rows:
            return ProductCompletenessResult(is_complete=True)

        # Partition bindings by requirement level
        required_attr_ids: set[uuid.UUID] = set()
        recommended_attr_ids: set[uuid.UUID] = set()
        for row in binding_rows:
            if row.requirement_level == RequirementLevel.REQUIRED:
                required_attr_ids.add(row.attribute_id)
            elif row.requirement_level == RequirementLevel.RECOMMENDED:
                recommended_attr_ids.add(row.attribute_id)

        # 4. Load product attribute values
        pav_stmt = select(OrmProductAttributeValue.attribute_id).where(
            OrmProductAttributeValue.product_id == query.product_id
        )
        pav_rows = (await self._session.execute(pav_stmt)).all()
        filled_attr_ids = {row.attribute_id for row in pav_rows}

        # 5. Compare
        missing_required_ids = required_attr_ids - filled_attr_ids
        missing_recommended_ids = recommended_attr_ids - filled_attr_ids

        # Fetch attribute metadata for missing ones
        all_missing_ids = missing_required_ids | missing_recommended_ids
        attr_lookup: dict[uuid.UUID, dict[str, Any]] = {}
        if all_missing_ids:
            attr_stmt = select(
                OrmAttribute.id, OrmAttribute.code, OrmAttribute.name_i18n
            ).where(OrmAttribute.id.in_(all_missing_ids))
            attr_rows = (await self._session.execute(attr_stmt)).all()
            for row in attr_rows:
                attr_lookup[row.id] = {
                    "attribute_id": row.id,
                    "code": row.code,
                    "name_i18n": row.name_i18n,
                }

        missing_required = [
            attr_lookup[aid] for aid in missing_required_ids if aid in attr_lookup
        ]
        missing_recommended = [
            attr_lookup[aid] for aid in missing_recommended_ids if aid in attr_lookup
        ]

        filled_required = len(required_attr_ids) - len(missing_required_ids)
        filled_recommended = len(recommended_attr_ids) - len(missing_recommended_ids)

        return ProductCompletenessResult(
            is_complete=len(missing_required_ids) == 0,
            total_required=len(required_attr_ids),
            filled_required=filled_required,
            total_recommended=len(recommended_attr_ids),
            filled_recommended=filled_recommended,
            missing_required=missing_required,
            missing_recommended=missing_recommended,
        )
