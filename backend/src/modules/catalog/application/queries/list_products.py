"""
Query handler: paginated product listing with filters.

Strict CQRS read side -- queries the ORM directly and returns read models.
Supports filtering by status and brand_id, with limit/offset pagination.
"""

import uuid
from dataclasses import dataclass

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.application.queries.read_models import (
    ProductListItemReadModel,
    ProductListReadModel,
)
from src.modules.catalog.domain.value_objects import ProductStatus
from src.modules.catalog.infrastructure.models import Product as OrmProduct
from src.shared.interfaces.logger import ILogger
from src.shared.pagination import paginate


@dataclass(frozen=True)
class ListProductsQuery:
    """Pagination and filter parameters for product listing.

    Attributes:
        offset: Number of records to skip.
        limit: Maximum number of records to return.
        status: Filter by product status (e.g. "draft", "published").
        brand_id: Filter by brand UUID.
    """

    offset: int = 0
    limit: int = 50
    status: str | None = None
    brand_id: uuid.UUID | None = None


class ListProductsHandler:
    """Fetch a paginated and filtered list of products."""

    def __init__(self, session: AsyncSession, logger: ILogger) -> None:
        self._session = session
        self._logger = logger.bind(handler="ListProductsHandler")

    async def handle(self, query: ListProductsQuery) -> ProductListReadModel:
        """Retrieve a paginated product list with optional filters.

        Only non-deleted products are returned (``deleted_at IS NULL``).

        Args:
            query: Pagination and filter parameters.

        Returns:
            Paginated list read model with items and total count.
        """
        base = select(OrmProduct)
        base = self._apply_filters(base, query)
        base = base.order_by(OrmProduct.created_at.desc())

        items, total = await paginate(
            self._session,
            base,
            offset=query.offset,
            limit=query.limit,
            mapper=self._to_read_model,
        )

        return ProductListReadModel(
            items=items,
            total=total,
            offset=query.offset,
            limit=query.limit,
        )

    @staticmethod
    def _apply_filters(
        stmt: Select[OrmProduct], query: ListProductsQuery
    ) -> Select[OrmProduct]:
        """Apply optional filter clauses to the query."""
        stmt = stmt.where(OrmProduct.deleted_at.is_(None))
        if query.status is not None:
            try:
                status_enum = ProductStatus(query.status)
            except ValueError:
                return stmt.where(False)
            stmt = stmt.where(OrmProduct.status == status_enum)
        if query.brand_id is not None:
            stmt = stmt.where(OrmProduct.brand_id == query.brand_id)
        return stmt

    @staticmethod
    def _to_read_model(orm: OrmProduct) -> ProductListItemReadModel:
        """Convert an ORM row to a list item read model."""
        return ProductListItemReadModel(
            id=orm.id,
            slug=orm.slug,
            title_i18n=orm.title_i18n,
            status=orm.status.value,
            brand_id=orm.brand_id,
            primary_category_id=orm.primary_category_id,
            version=orm.version,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )
