"""
Query handler: paginated brand listing.

Strict CQRS read side — does not use IUnitOfWork, domain aggregates, or
repositories. Queries the ORM directly via AsyncSession and returns a
Pydantic read model.
"""

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.application.queries.read_models import (
    BrandListReadModel,
    BrandReadModel,
)
from src.modules.catalog.infrastructure.models import Brand as OrmBrand


@dataclass(frozen=True)
class ListBrandsQuery:
    """Pagination parameters for brand listing.

    Attributes:
        offset: Number of records to skip.
        limit: Maximum number of records to return.
    """

    offset: int = 0
    limit: int = 20


class ListBrandsHandler:
    """Fetch a paginated list of brands."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def handle(self, query: ListBrandsQuery) -> BrandListReadModel:
        """Retrieve a paginated brand list.

        Args:
            query: Pagination parameters.

        Returns:
            Paginated list read model with items and total count.
        """
        count_result = await self._session.execute(select(func.count()).select_from(OrmBrand))
        total = count_result.scalar_one()

        stmt = select(OrmBrand).order_by(OrmBrand.name).limit(query.limit).offset(query.offset)
        result = await self._session.execute(stmt)
        rows = result.scalars().all()

        items = [
            BrandReadModel(
                id=orm.id,
                name=orm.name,
                slug=orm.slug,
                logo_url=orm.logo_url,
                logo_status=orm.logo_status,
            )
            for orm in rows
        ]

        return BrandListReadModel(
            items=items,
            total=total,
            offset=query.offset,
            limit=query.limit,
        )
