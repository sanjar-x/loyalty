"""
Query handler: retrieve a single brand by ID.

Strict CQRS read side — does not use IUnitOfWork, domain aggregates, or
repositories. Queries the ORM directly via AsyncSession and returns a
Pydantic read model.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.application.queries.read_models import BrandReadModel
from src.modules.catalog.domain.exceptions import BrandNotFoundError
from src.modules.catalog.infrastructure.models import Brand as OrmBrand
from src.shared.interfaces.logger import ILogger


def brand_orm_to_read_model(orm: OrmBrand) -> BrandReadModel:
    """Convert an ORM Brand to a BrandReadModel."""
    return BrandReadModel(
        id=orm.id,
        name=orm.name,
        slug=orm.slug,
        logo_url=orm.logo_url,
        logo_status=orm.logo_status,
    )


class GetBrandHandler:
    """Fetch a single brand by its UUID."""

    def __init__(self, session: AsyncSession, logger: ILogger):
        self._session = session
        self._logger = logger.bind(handler="GetBrandHandler")

    async def handle(self, brand_id: uuid.UUID) -> BrandReadModel:
        """Retrieve a brand read model.

        Args:
            brand_id: UUID of the brand to retrieve.

        Returns:
            Brand read model with current state.

        Raises:
            BrandNotFoundError: If no brand with this ID exists.
        """
        stmt = select(OrmBrand).where(OrmBrand.id == brand_id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()

        if orm is None:
            raise BrandNotFoundError(brand_id=brand_id)

        return brand_orm_to_read_model(orm)
