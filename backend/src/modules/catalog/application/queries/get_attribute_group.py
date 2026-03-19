"""
Query handler: get a single attribute group by ID.

Strict CQRS read side -- queries the database directly via AsyncSession
and returns a read model DTO.
"""

import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.application.queries.read_models import (
    AttributeGroupReadModel,
)
from src.modules.catalog.domain.exceptions import AttributeGroupNotFoundError

_GET_ATTRIBUTE_GROUP_SQL = text(
    "SELECT id, code, name_i18n, sort_order FROM attribute_groups WHERE id = :group_id"
)


class GetAttributeGroupHandler:
    """Fetch a single attribute group by its UUID."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def handle(self, group_id: uuid.UUID) -> AttributeGroupReadModel:
        """Retrieve an attribute group by ID.

        Args:
            group_id: UUID of the attribute group.

        Returns:
            Attribute group read model.

        Raises:
            AttributeGroupNotFoundError: If the group does not exist.
        """
        result = await self._session.execute(_GET_ATTRIBUTE_GROUP_SQL, {"group_id": group_id})
        row = result.mappings().first()

        if row is None:
            raise AttributeGroupNotFoundError(group_id=group_id)

        return AttributeGroupReadModel(
            id=row["id"],
            code=row["code"],
            name_i18n=row["name_i18n"],
            sort_order=row["sort_order"],
        )
