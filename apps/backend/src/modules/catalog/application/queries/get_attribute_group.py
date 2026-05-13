"""
Query handler: retrieve a single attribute group by ID.

Strict CQRS read side — does not use IUnitOfWork, domain aggregates, or
repositories. Queries the ORM directly via AsyncSession and returns a
Pydantic read model.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.application.queries.read_models import (
    AttributeGroupReadModel,
)
from src.modules.catalog.domain.exceptions import AttributeGroupNotFoundError
from src.modules.catalog.infrastructure.models import (
    AttributeGroup as OrmAttributeGroup,
)
from src.shared.interfaces.logger import ILogger


def attribute_group_orm_to_read_model(
    orm: OrmAttributeGroup,
) -> AttributeGroupReadModel:
    """Convert an ORM AttributeGroup to an AttributeGroupReadModel."""
    return AttributeGroupReadModel(
        id=orm.id,
        code=orm.code,
        name_i18n=dict(orm.name_i18n) if orm.name_i18n else {},
        sort_order=orm.sort_order,
    )


class GetAttributeGroupHandler:
    """Fetch a single attribute group by its UUID."""

    def __init__(self, session: AsyncSession, logger: ILogger):
        self._session = session
        self._logger = logger.bind(handler="GetAttributeGroupHandler")

    async def handle(self, group_id: uuid.UUID) -> AttributeGroupReadModel:
        """Retrieve an attribute group read model.

        Args:
            group_id: UUID of the attribute group to retrieve.

        Returns:
            Attribute group read model with current state.

        Raises:
            AttributeGroupNotFoundError: If no group with this ID exists.
        """
        stmt = select(OrmAttributeGroup).where(OrmAttributeGroup.id == group_id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()

        if orm is None:
            raise AttributeGroupNotFoundError(group_id=group_id)

        return attribute_group_orm_to_read_model(orm)
