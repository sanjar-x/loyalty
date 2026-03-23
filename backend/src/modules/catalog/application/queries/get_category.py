"""
Query handler: retrieve a single category by ID.

Strict CQRS read side — does not use IUnitOfWork, domain aggregates, or
repositories. Queries the ORM directly via AsyncSession and returns a
Pydantic read model.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.application.queries.read_models import CategoryReadModel
from src.modules.catalog.domain.exceptions import CategoryNotFoundError
from src.modules.catalog.infrastructure.models import Category as OrmCategory
from src.shared.interfaces.logger import ILogger


def category_orm_to_read_model(orm: OrmCategory) -> CategoryReadModel:
    """Convert an ORM Category to a CategoryReadModel."""
    return CategoryReadModel(
        id=orm.id,
        name=orm.name,
        slug=orm.slug,
        full_slug=orm.full_slug,
        level=orm.level,
        sort_order=orm.sort_order,
        parent_id=orm.parent_id,
    )


class GetCategoryHandler:
    """Fetch a single category by its UUID."""

    def __init__(self, session: AsyncSession, logger: ILogger):
        self._session = session
        self._logger = logger.bind(handler="GetCategoryHandler")

    async def handle(self, category_id: uuid.UUID) -> CategoryReadModel:
        """Retrieve a category read model.

        Args:
            category_id: UUID of the category to retrieve.

        Returns:
            Category read model with current state.

        Raises:
            CategoryNotFoundError: If no category with this ID exists.
        """
        stmt = select(OrmCategory).where(OrmCategory.id == category_id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()

        if orm is None:
            raise CategoryNotFoundError(category_id=category_id)

        return category_orm_to_read_model(orm)
