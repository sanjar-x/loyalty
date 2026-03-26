"""
Query handler: paginated attribute listing with filters.

Strict CQRS read side -- queries the ORM directly and returns read models.
Supports filtering by data_type, ui_type, is_dictionary, group_id, level,
and behavior flags, plus search by name across languages.
"""

import uuid
from dataclasses import dataclass

from sqlalchemy import Select, func, literal_column, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.application.queries.read_models import (
    AttributeListReadModel,
    AttributeReadModel,
)
from src.modules.catalog.infrastructure.models import Attribute as OrmAttribute
from src.shared.interfaces.logger import ILogger
from src.shared.pagination import paginate


def attribute_orm_to_read_model(orm: OrmAttribute) -> AttributeReadModel:
    """Convert an ORM Attribute row to an AttributeReadModel."""
    return AttributeReadModel(
        id=orm.id,
        code=orm.code,
        slug=orm.slug,
        name_i18n=orm.name_i18n,
        description_i18n=orm.description_i18n,
        data_type=orm.data_type.value,
        ui_type=orm.ui_type.value,
        is_dictionary=orm.is_dictionary,
        group_id=orm.group_id,
        level=orm.level.value,
        is_filterable=orm.is_filterable,
        is_searchable=orm.is_searchable,
        search_weight=orm.search_weight,
        is_comparable=orm.is_comparable,
        is_visible_on_card=orm.is_visible_on_card,
        is_visible_in_catalog=orm.is_visible_in_catalog,
        validation_rules=dict(orm.validation_rules) if orm.validation_rules else None,
    )


@dataclass(frozen=True)
class ListAttributesQuery:
    """Pagination and filter parameters for attribute listing.

    Attributes:
        offset: Number of records to skip.
        limit: Maximum number of records to return.
        data_type: Filter by data type (e.g. "string", "integer").
        ui_type: Filter by UI type (e.g. "text_button", "dropdown").
        is_dictionary: Filter by dictionary flag.
        group_id: Filter by attribute group UUID.
        level: Filter by attribute level ("product" or "variant").
        is_filterable: Filter by filterable flag.
        is_searchable: Filter by searchable flag.
        is_comparable: Filter by comparable flag.
        search: Search term to match against name_i18n values.
    """

    offset: int = 0
    limit: int = 50
    data_type: str | None = None
    ui_type: str | None = None
    is_dictionary: bool | None = None
    group_id: uuid.UUID | None = None
    level: str | None = None
    is_filterable: bool | None = None
    is_searchable: bool | None = None
    is_comparable: bool | None = None
    search: str | None = None


class ListAttributesHandler:
    """Fetch a paginated and filtered list of attributes."""

    def __init__(self, session: AsyncSession, logger: ILogger):
        self._session = session
        self._logger = logger.bind(handler="ListAttributesHandler")

    async def handle(self, query: ListAttributesQuery) -> AttributeListReadModel:
        """Retrieve a paginated attribute list with optional filters.

        Args:
            query: Pagination and filter parameters.

        Returns:
            Paginated list read model with items and total count.
        """
        base = select(OrmAttribute)
        base = self._apply_filters(base, query)
        base = base.order_by(OrmAttribute.code)

        items, total = await paginate(
            self._session,
            base,
            offset=query.offset,
            limit=query.limit,
            mapper=attribute_orm_to_read_model,
        )

        return AttributeListReadModel(
            items=items,
            total=total,
            offset=query.offset,
            limit=query.limit,
        )

    @staticmethod
    def _apply_filters(
        stmt: Select[tuple[OrmAttribute]], query: ListAttributesQuery
    ) -> Select[tuple[OrmAttribute]]:
        """Apply optional filter clauses to the query."""
        if query.data_type is not None:
            stmt = stmt.where(OrmAttribute.data_type == query.data_type)
        if query.ui_type is not None:
            stmt = stmt.where(OrmAttribute.ui_type == query.ui_type)
        if query.is_dictionary is not None:
            stmt = stmt.where(OrmAttribute.is_dictionary == query.is_dictionary)
        if query.group_id is not None:
            stmt = stmt.where(OrmAttribute.group_id == query.group_id)
        if query.level is not None:
            stmt = stmt.where(OrmAttribute.level == query.level)
        if query.is_filterable is not None:
            stmt = stmt.where(OrmAttribute.is_filterable == query.is_filterable)
        if query.is_searchable is not None:
            stmt = stmt.where(OrmAttribute.is_searchable == query.is_searchable)
        if query.is_comparable is not None:
            stmt = stmt.where(OrmAttribute.is_comparable == query.is_comparable)
        if query.search is not None:
            # Search across all JSONB values using jsonb_each_text lateral join.
            # This avoids CAST(jsonb AS text) ILIKE which bypasses GIN indexes
            # and pollutes results with JSON keys/syntax characters.
            escaped = (
                query.search.replace("\\", "\\\\")
                .replace("%", "\\%")
                .replace("_", "\\_")
            )
            search_pattern = f"%{escaped}%"
            stmt = stmt.where(
                select(literal_column("1"))
                .select_from(func.jsonb_each_text(OrmAttribute.name_i18n).alias("kv"))
                .where(literal_column("kv.value").ilike(search_pattern))
                .correlate(OrmAttribute)
                .exists()
            )
        return stmt
