"""
Query handler: get a single attribute by ID or by slug.

Strict CQRS read side -- queries the ORM directly via AsyncSession
and returns a read model DTO.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.application.queries.list_attributes import (
    attribute_orm_to_read_model,
)
from src.modules.catalog.application.queries.read_models import AttributeReadModel
from src.modules.catalog.domain.exceptions import AttributeNotFoundError
from src.modules.catalog.infrastructure.models import Attribute as OrmAttribute
from src.shared.interfaces.logger import ILogger


class GetAttributeHandler:
    """Fetch a single attribute by its UUID."""

    def __init__(self, session: AsyncSession, logger: ILogger):
        self._session = session
        self._logger = logger.bind(handler="GetAttributeHandler")

    async def handle(self, attribute_id: uuid.UUID) -> AttributeReadModel:
        """Retrieve an attribute by ID.

        Args:
            attribute_id: UUID of the attribute.

        Returns:
            Attribute read model.

        Raises:
            AttributeNotFoundError: If the attribute does not exist.
        """
        statement = select(OrmAttribute).where(OrmAttribute.id == attribute_id)
        result = await self._session.execute(statement)
        orm = result.scalar_one_or_none()

        if orm is None:
            raise AttributeNotFoundError(attribute_id=attribute_id)

        return attribute_orm_to_read_model(orm)

    async def handle_by_slug(self, slug: str) -> AttributeReadModel:
        """Retrieve an attribute by slug.

        Args:
            slug: URL-safe slug of the attribute.

        Returns:
            Attribute read model.

        Raises:
            AttributeNotFoundError: If the attribute does not exist.
        """
        statement = select(OrmAttribute).where(OrmAttribute.slug == slug).limit(1)
        result = await self._session.execute(statement)
        orm = result.scalar_one_or_none()

        if orm is None:
            raise AttributeNotFoundError(attribute_id=slug)

        return attribute_orm_to_read_model(orm)
