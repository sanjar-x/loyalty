"""
Query handler: attribute usage analytics.

Returns where an attribute is used -- which templates bind it, which
categories inherit it, and how many products have values for it.
Strict CQRS read side -- queries the ORM directly and returns a result dataclass.
"""

import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.domain.exceptions import AttributeNotFoundError
from src.modules.catalog.infrastructure.models import (
    Attribute as OrmAttribute,
    AttributeTemplate as OrmAttributeTemplate,
    Category as OrmCategory,
    ProductAttributeValue as OrmProductAttributeValue,
    TemplateAttributeBinding as OrmTemplateAttributeBinding,
)
from src.shared.interfaces.logger import ILogger


@dataclass(frozen=True)
class AttributeUsageQuery:
    """Input for the attribute usage analytics query.

    Attributes:
        attribute_id: UUID of the attribute to look up.
    """

    attribute_id: uuid.UUID


@dataclass
class AttributeUsageResult:
    """Output of the attribute usage analytics query.

    Attributes:
        template_count: Number of templates that bind this attribute.
        templates: List of template summaries [{id, code, name_i18n}].
        category_count: Number of categories that inherit this attribute.
        categories: List of category summaries [{id, full_slug, name_i18n}].
        product_count: Number of products with a value for this attribute.
    """

    template_count: int = 0
    templates: list[dict[str, Any]] = field(default_factory=list)
    category_count: int = 0
    categories: list[dict[str, Any]] = field(default_factory=list)
    product_count: int = 0


class GetAttributeUsageHandler:
    """Return usage analytics for a single attribute."""

    def __init__(self, session: AsyncSession, logger: ILogger) -> None:
        self._session = session
        self._logger = logger.bind(handler="GetAttributeUsageHandler")

    async def handle(self, query: AttributeUsageQuery) -> AttributeUsageResult:
        """Execute the attribute usage analytics query.

        Args:
            query: Contains the attribute_id to analyse.

        Returns:
            Usage result with templates, categories, and product count.

        Raises:
            AttributeNotFoundError: If the attribute does not exist.
        """
        # Verify the attribute exists
        attr_exists = await self._session.execute(
            select(OrmAttribute.id).where(OrmAttribute.id == query.attribute_id).limit(1)
        )
        if attr_exists.scalar_one_or_none() is None:
            raise AttributeNotFoundError(attribute_id=query.attribute_id)

        # 1. Templates using this attribute
        template_stmt = (
            select(
                OrmAttributeTemplate.id,
                OrmAttributeTemplate.code,
                OrmAttributeTemplate.name_i18n,
            )
            .join(
                OrmTemplateAttributeBinding,
                OrmTemplateAttributeBinding.template_id == OrmAttributeTemplate.id,
            )
            .where(OrmTemplateAttributeBinding.attribute_id == query.attribute_id)
        )
        template_rows = (await self._session.execute(template_stmt)).all()
        templates = [
            {"id": row.id, "code": row.code, "name_i18n": row.name_i18n}
            for row in template_rows
        ]

        # 2. Categories inheriting via effective_template_id
        template_ids = [row.id for row in template_rows]
        categories: list[dict[str, Any]] = []
        if template_ids:
            category_stmt = select(
                OrmCategory.id,
                OrmCategory.full_slug,
                OrmCategory.name_i18n,
            ).where(OrmCategory.effective_template_id.in_(template_ids))
            category_rows = (await self._session.execute(category_stmt)).all()
            categories = [
                {
                    "id": row.id,
                    "full_slug": row.full_slug,
                    "name_i18n": row.name_i18n,
                }
                for row in category_rows
            ]

        # 3. Product count
        product_count_stmt = select(
            func.count(func.distinct(OrmProductAttributeValue.product_id))
        ).where(OrmProductAttributeValue.attribute_id == query.attribute_id)
        product_count: int = (
            await self._session.execute(product_count_stmt)
        ).scalar_one()

        return AttributeUsageResult(
            template_count=len(templates),
            templates=templates,
            category_count=len(categories),
            categories=categories,
            product_count=product_count,
        )
