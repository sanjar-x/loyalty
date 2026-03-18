"""
Query handler: get a single attribute by ID or by slug.

Strict CQRS read side -- queries the ORM directly via AsyncSession
and returns a read model DTO.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.application.queries.read_models import AttributeReadModel
from src.modules.catalog.domain.exceptions import AttributeNotFoundError
from src.modules.catalog.infrastructure.models import Attribute as OrmAttribute


class GetAttributeHandler:
    """Fetch a single attribute by its UUID."""

    def __init__(self, session: AsyncSession):
        self._session = session

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

        return self._to_read_model(orm)

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

        return self._to_read_model(orm)

    @staticmethod
    def _to_read_model(orm: OrmAttribute) -> AttributeReadModel:
        """Convert an ORM row to a read model."""
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
