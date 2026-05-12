"""
Query handler: paginated brand listing.

Strict CQRS read side — does not use IUnitOfWork, domain aggregates, or
repositories. Queries the ORM directly via AsyncSession and returns a
Pydantic read model.
"""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.application.queries.get_brand import brand_orm_to_read_model
from src.modules.catalog.application.queries.read_models import (
    BrandListReadModel,
)
from src.modules.catalog.infrastructure.models import Brand as OrmBrand
from src.shared.interfaces.logger import ILogger
from src.shared.pagination import paginate


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

    def __init__(self, session: AsyncSession, logger: ILogger):
        self._session = session
        self._logger = logger.bind(handler="ListBrandsHandler")

    async def handle(self, query: ListBrandsQuery) -> BrandListReadModel:
        """Retrieve a paginated brand list.

        Args:
            query: Pagination parameters.

        Returns:
            Paginated list read model with items and total count.
        """
        base = select(OrmBrand).order_by(OrmBrand.name)

        items, total = await paginate(
            self._session,
            base,
            offset=query.offset,
            limit=query.limit,
            mapper=brand_orm_to_read_model,
        )

        return BrandListReadModel(
            items=items,
            total=total,
            offset=query.offset,
            limit=query.limit,
        )
