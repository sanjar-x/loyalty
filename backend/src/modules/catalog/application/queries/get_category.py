"""
Query handler: retrieve a single category by ID.

Strict CQRS read side — does not use IUnitOfWork, domain aggregates, or
repositories. Queries the database directly via AsyncSession + raw SQL
and returns a Pydantic read model.
"""

import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.application.queries.read_models import CategoryReadModel
from src.modules.catalog.domain.exceptions import CategoryNotFoundError

_GET_CATEGORY_SQL = text(
    "SELECT id, name, slug, full_slug, level, sort_order, parent_id "
    "FROM categories WHERE id = :category_id"
)


class GetCategoryHandler:
    """Fetch a single category by its UUID."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def handle(self, category_id: uuid.UUID) -> CategoryReadModel:
        """Retrieve a category read model.

        Args:
            category_id: UUID of the category to retrieve.

        Returns:
            Category read model with current state.

        Raises:
            CategoryNotFoundError: If no category with this ID exists.
        """
        result = await self._session.execute(_GET_CATEGORY_SQL, {"category_id": category_id})
        row = result.mappings().first()

        if row is None:
            raise CategoryNotFoundError(category_id=category_id)

        return CategoryReadModel(
            id=row["id"],
            name=row["name"],
            slug=row["slug"],
            full_slug=row["full_slug"],
            level=row["level"],
            sort_order=row["sort_order"],
            parent_id=row["parent_id"],
        )
