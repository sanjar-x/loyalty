"""
Query handler: get a single attribute value by ID.

Strict CQRS read side -- queries the ORM directly via AsyncSession
and returns a read model DTO.  Verifies the value belongs to the
specified parent attribute.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.application.queries.read_models import AttributeValueReadModel
from src.modules.catalog.domain.exceptions import AttributeValueNotFoundError
from src.modules.catalog.infrastructure.models import (
    AttributeValue as OrmAttributeValue,
)
from src.shared.interfaces.logger import ILogger


class GetAttributeValueHandler:
    """Fetch a single attribute value by its UUID, scoped to an attribute."""

    def __init__(self, session: AsyncSession, logger: ILogger):
        self._session = session
        self._logger = logger.bind(handler="GetAttributeValueHandler")

    async def handle(
        self, attribute_id: uuid.UUID, value_id: uuid.UUID
    ) -> AttributeValueReadModel:
        """Retrieve an attribute value by ID, verifying it belongs to the attribute.

        Args:
            attribute_id: UUID of the parent attribute.
            value_id: UUID of the attribute value.

        Returns:
            Attribute value read model.

        Raises:
            AttributeValueNotFoundError: If the value does not exist or
                does not belong to the specified attribute.
        """
        stmt = select(OrmAttributeValue).where(
            OrmAttributeValue.id == value_id,
            OrmAttributeValue.attribute_id == attribute_id,
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()

        if orm is None:
            raise AttributeValueNotFoundError(value_id=value_id)

        return AttributeValueReadModel(
            id=orm.id,
            attribute_id=orm.attribute_id,
            code=orm.code,
            slug=orm.slug,
            value_i18n=orm.value_i18n,
            search_aliases=list(orm.search_aliases) if orm.search_aliases else [],
            meta_data=orm.meta_data,
            value_group=orm.value_group,
            sort_order=orm.sort_order,
            is_active=orm.is_active,
        )
