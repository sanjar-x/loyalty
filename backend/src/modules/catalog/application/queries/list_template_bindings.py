"""
Query handler: paginated listing of template-attribute bindings.

Strict CQRS read side -- does not use IUnitOfWork, domain aggregates, or
repositories. Queries the ORM directly via AsyncSession and returns
Pydantic read models.
"""

import uuid
from dataclasses import dataclass

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.modules.catalog.infrastructure.models import (
    TemplateAttributeBinding as OrmBinding,
)
from src.shared.interfaces.logger import ILogger
from src.shared.pagination import paginate

# ---------------------------------------------------------------------------
# Read Models
# ---------------------------------------------------------------------------


class TemplateBindingReadModel(BaseModel):
    """Read model for a single template-attribute binding."""

    id: uuid.UUID
    template_id: uuid.UUID
    attribute_id: uuid.UUID
    sort_order: int
    requirement_level: str
    filter_settings: dict | None = None
    attribute_code: str = ""
    attribute_name_i18n: dict[str, str] = {}
    attribute_data_type: str = ""
    attribute_ui_type: str = ""
    attribute_level: str = ""
    attribute_is_filterable: bool = False


class TemplateBindingListReadModel(BaseModel):
    """Paginated list of template bindings."""

    items: list[TemplateBindingReadModel]
    total: int
    offset: int
    limit: int


# ---------------------------------------------------------------------------
# Query
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ListTemplateBindingsQuery:
    """Pagination parameters for template binding listing."""

    template_id: uuid.UUID
    offset: int = 0
    limit: int = 50


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------


class ListTemplateBindingsHandler:
    """Fetch a paginated list of attribute bindings for a template."""

    def __init__(self, session: AsyncSession, logger: ILogger):
        self._session = session
        self._logger = logger.bind(handler="ListTemplateBindingsHandler")

    async def handle(
        self, query: ListTemplateBindingsQuery
    ) -> TemplateBindingListReadModel:
        """Retrieve a paginated binding list for a template."""
        base = (
            select(OrmBinding)
            .options(selectinload(OrmBinding.attribute))
            .where(OrmBinding.template_id == query.template_id)
            .order_by(OrmBinding.sort_order)
        )

        items, total = await paginate(
            self._session,
            base,
            offset=query.offset,
            limit=query.limit,
            mapper=self._to_read_model,
        )

        return TemplateBindingListReadModel(
            items=items,
            total=total,
            offset=query.offset,
            limit=query.limit,
        )

    @staticmethod
    def _to_read_model(row: OrmBinding) -> TemplateBindingReadModel:
        """Convert an ORM row to a read model."""
        attr = row.attribute
        return TemplateBindingReadModel(
            id=row.id,
            template_id=row.template_id,
            attribute_id=row.attribute_id,
            sort_order=row.sort_order,
            requirement_level=row.requirement_level.value,
            filter_settings=dict(row.filter_settings) if row.filter_settings else None,
            attribute_code=attr.code if attr else "",
            attribute_name_i18n=dict(attr.name_i18n) if attr else {},
            attribute_data_type=attr.data_type.value if attr else "",
            attribute_ui_type=attr.ui_type.value if attr else "",
            attribute_level=attr.level.value if attr else "",
            attribute_is_filterable=attr.is_filterable if attr else False,
        )
