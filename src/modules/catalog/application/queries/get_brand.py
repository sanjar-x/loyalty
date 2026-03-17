"""
Query handler: retrieve a single brand by ID.

Strict CQRS read side — does not use IUnitOfWork, domain aggregates, or
repositories. Queries the database directly via AsyncSession + raw SQL
and returns a Pydantic read model.
"""

import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.application.queries.read_models import BrandReadModel
from src.modules.catalog.domain.exceptions import BrandNotFoundError

_GET_BRAND_SQL = text(
    "SELECT id, name, slug, logo_url, logo_status FROM brands WHERE id = :brand_id"
)


class GetBrandHandler:
    """Fetch a single brand by its UUID."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def handle(self, brand_id: uuid.UUID) -> BrandReadModel:
        """Retrieve a brand read model.

        Args:
            brand_id: UUID of the brand to retrieve.

        Returns:
            Brand read model with current state.

        Raises:
            BrandNotFoundError: If no brand with this ID exists.
        """
        result = await self._session.execute(_GET_BRAND_SQL, {"brand_id": brand_id})
        row = result.mappings().first()

        if row is None:
            raise BrandNotFoundError(brand_id=brand_id)

        return BrandReadModel(
            id=row["id"],
            name=row["name"],
            slug=row["slug"],
            logo_url=row["logo_url"],
            logo_status=row["logo_status"],
        )
