"""Query handler: list variants for a given product.

Strict CQRS read side -- queries the ORM directly and returns
a list of ProductVariantReadModel DTOs for a specific product.
"""

import uuid
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.modules.catalog.application.queries.list_skus import sku_orm_to_read_model
from src.modules.catalog.application.queries.read_models import (
    MoneyReadModel,
    ProductVariantReadModel,
    SKUReadModel,
)
from src.modules.catalog.infrastructure.models import (
    SKU as OrmSKU,
)
from src.modules.catalog.infrastructure.models import (
    ProductVariant as OrmProductVariant,
)
from src.shared.interfaces.logger import ILogger


def variant_orm_to_read_model(orm: OrmProductVariant) -> ProductVariantReadModel:
    """Convert an ORM ProductVariant to a read model with nested SKUs."""
    default_price: MoneyReadModel | None = None
    if orm.default_price is not None:
        default_price = MoneyReadModel(amount=orm.default_price, currency=orm.default_currency)

    skus: list[SKUReadModel] = []
    for sku_orm in orm.skus:
        if sku_orm.deleted_at is not None:
            continue
        skus.append(sku_orm_to_read_model(sku_orm, variant_default_price=default_price))

    return ProductVariantReadModel(
        id=orm.id,
        product_id=orm.product_id,
        name_i18n=dict(orm.name_i18n) if orm.name_i18n else {},
        description_i18n=dict(orm.description_i18n) if orm.description_i18n else None,
        sort_order=orm.sort_order,
        default_price=default_price,
        skus=skus,
    )


@dataclass(frozen=True)
class ListVariantsQuery:
    """Parameters for listing variants of a product.

    Attributes:
        product_id: UUID of the parent product.
        offset: Number of records to skip.
        limit: Maximum number of records to return.
    """

    product_id: uuid.UUID
    offset: int = 0
    limit: int = 50


class ListVariantsHandler:
    """Fetch all active variants for a given product."""

    def __init__(self, session: AsyncSession, logger: ILogger) -> None:
        self._session = session
        self._logger = logger.bind(handler="ListVariantsHandler")

    async def handle(self, query: ListVariantsQuery) -> tuple[list[ProductVariantReadModel], int]:
        """Retrieve paginated active variants for a product, ordered by sort_order.

        Eagerly loads SKUs and their variant attribute links for each variant.

        Args:
            query: Query parameters with the parent product_id and pagination.

        Returns:
            Tuple of (variant read models, total count).
        """
        count_stmt = (
            select(func.count())
            .select_from(OrmProductVariant)
            .where(
                OrmProductVariant.product_id == query.product_id,
                OrmProductVariant.deleted_at.is_(None),
            )
        )
        count_result = await self._session.execute(count_stmt)
        total: int = count_result.scalar_one()

        stmt = (
            select(OrmProductVariant)
            .where(
                OrmProductVariant.product_id == query.product_id,
                OrmProductVariant.deleted_at.is_(None),
            )
            .options(selectinload(OrmProductVariant.skus).selectinload(OrmSKU.attribute_values))
            .order_by(OrmProductVariant.sort_order)
            .limit(query.limit)
            .offset(query.offset)
        )
        result = await self._session.execute(stmt)
        rows = result.scalars().all()
        return [variant_orm_to_read_model(orm) for orm in rows], total
