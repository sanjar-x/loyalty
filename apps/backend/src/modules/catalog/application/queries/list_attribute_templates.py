"""
Query handler: paginated attribute template listing.

Strict CQRS read side -- does not use IUnitOfWork, domain aggregates, or
repositories. Queries the ORM directly via AsyncSession and returns
Pydantic read models.
"""

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.application.queries.read_models import (
    AttributeTemplateListReadModel,
    AttributeTemplateReadModel,
)
from src.modules.catalog.domain.exceptions import AttributeTemplateNotFoundError
from src.modules.catalog.infrastructure.models import (
    AttributeTemplate as OrmAttributeTemplate,
)
from src.shared.interfaces.logger import ILogger
from src.shared.pagination import paginate

# ---------------------------------------------------------------------------
# ORM -> Read Model converter
# ---------------------------------------------------------------------------


def template_orm_to_read_model(orm: OrmAttributeTemplate) -> AttributeTemplateReadModel:
    """Convert an ORM AttributeTemplate to an AttributeTemplateReadModel."""
    return AttributeTemplateReadModel(
        id=orm.id,
        code=orm.code,
        name_i18n=orm.name_i18n or {},
        description_i18n=orm.description_i18n or {},
        sort_order=orm.sort_order,
    )


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ListAttributeTemplatesQuery:
    """Pagination parameters for attribute template listing.

    Attributes:
        offset: Number of records to skip.
        limit: Maximum number of records to return.
    """

    offset: int = 0
    limit: int = 50


@dataclass(frozen=True)
class GetAttributeTemplateQuery:
    """Query to retrieve a single attribute template by ID.

    Attributes:
        template_id: UUID of the template to retrieve.
    """

    template_id: uuid.UUID


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------


class ListAttributeTemplatesHandler:
    """Fetch a paginated list of attribute templates."""

    def __init__(self, session: AsyncSession, logger: ILogger):
        self._session = session
        self._logger = logger.bind(handler="ListAttributeTemplatesHandler")

    async def handle(
        self, query: ListAttributeTemplatesQuery
    ) -> AttributeTemplateListReadModel:
        """Retrieve a paginated attribute template list.

        Args:
            query: Pagination parameters.

        Returns:
            Paginated list read model with items and total count.
        """
        base = select(OrmAttributeTemplate).order_by(
            OrmAttributeTemplate.sort_order,
            OrmAttributeTemplate.code,
        )

        items, total = await paginate(
            self._session,
            base,
            offset=query.offset,
            limit=query.limit,
            mapper=template_orm_to_read_model,
        )

        return AttributeTemplateListReadModel(
            items=items,
            total=total,
            offset=query.offset,
            limit=query.limit,
        )


class GetAttributeTemplateHandler:
    """Fetch a single attribute template by its UUID."""

    def __init__(self, session: AsyncSession, logger: ILogger):
        self._session = session
        self._logger = logger.bind(handler="GetAttributeTemplateHandler")

    async def handle(
        self, query: GetAttributeTemplateQuery
    ) -> AttributeTemplateReadModel:
        """Retrieve an attribute template read model.

        Args:
            query: Contains the UUID of the template to retrieve.

        Returns:
            Attribute template read model with current state.

        Raises:
            AttributeTemplateNotFoundError: If no template with this ID exists.
        """
        stmt = select(OrmAttributeTemplate).where(
            OrmAttributeTemplate.id == query.template_id
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()

        if orm is None:
            raise AttributeTemplateNotFoundError(template_id=query.template_id)

        return template_orm_to_read_model(orm)
