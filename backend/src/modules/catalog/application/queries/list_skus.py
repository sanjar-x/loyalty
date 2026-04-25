"""
Query handler: list SKUs for a given product.

Strict CQRS read side -- queries the ORM directly and returns
a list of SKUReadModel DTOs for a specific product.
"""

import uuid
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.modules.catalog.application.queries.read_models import (
    MoneyReadModel,
    SKUListReadModel,
    SKUReadModel,
    VariantAttributePairReadModel,
    resolve_sku_price,
)
from src.modules.catalog.infrastructure.models import (
    SKU as OrmSKU,
)
from src.shared.interfaces.logger import ILogger


def sku_orm_to_read_model(
    orm: OrmSKU,
    variant_default_price: MoneyReadModel | None = None,
) -> SKUReadModel:
    """Convert an ORM SKU row to a SKUReadModel."""
    variant_attrs = [
        VariantAttributePairReadModel(
            attribute_id=link.attribute_id,
            attribute_value_id=link.attribute_value_id,
        )
        for link in orm.attribute_values
    ]

    compare_at: MoneyReadModel | None = None
    if orm.compare_at_price is not None:
        compare_at = MoneyReadModel(
            amount=orm.compare_at_price,
            currency=orm.currency,
        )

    sku_price: MoneyReadModel | None = None
    if orm.price is not None:
        sku_price = MoneyReadModel(amount=orm.price, currency=orm.currency)

    selling_price: MoneyReadModel | None = None
    if orm.selling_price is not None and orm.selling_currency:
        selling_price = MoneyReadModel(
            amount=orm.selling_price,
            currency=orm.selling_currency,
        )
    pricing_status = (
        orm.pricing_status.value
        if hasattr(orm.pricing_status, "value")
        else orm.pricing_status
    )
    resolved = resolve_sku_price(
        sku_price,
        variant_default_price,
        selling_price=selling_price,
        pricing_status=pricing_status,
    )

    return SKUReadModel(
        id=orm.id,
        product_id=orm.product_id,
        variant_id=orm.variant_id,
        sku_code=orm.sku_code,
        variant_hash=orm.variant_hash,
        price=sku_price,
        resolved_price=resolved,
        compare_at_price=compare_at,
        is_active=orm.is_active,
        version=orm.version,
        deleted_at=orm.deleted_at,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
        variant_attributes=variant_attrs,
    )


@dataclass(frozen=True)
class ListSKUsQuery:
    """Parameters for listing SKUs of a product.

    Attributes:
        product_id: UUID of the parent product.
        variant_id: Optional variant filter.
        offset: Number of records to skip.
        limit: Maximum number of records to return. None means no limit.
    """

    product_id: uuid.UUID
    variant_id: uuid.UUID | None = None
    offset: int = 0
    limit: int | None = 50


class ListSKUsHandler:
    """Fetch all SKUs for a given product."""

    def __init__(self, session: AsyncSession, logger: ILogger) -> None:
        self._session = session
        self._logger = logger.bind(handler="ListSKUsHandler")

    async def handle(self, query: ListSKUsQuery) -> SKUListReadModel:
        """Retrieve paginated SKUs for a product, ordered by creation time.

        Eagerly loads variant attribute links for each SKU.

        Args:
            query: Query parameters with the parent product_id and pagination.

        Returns:
            Tuple of (SKU read models, total count).
        """
        # Build base WHERE conditions
        conditions = [
            OrmSKU.product_id == query.product_id,
            OrmSKU.deleted_at.is_(None),
        ]
        if query.variant_id is not None:
            conditions.append(OrmSKU.variant_id == query.variant_id)

        # Count total
        count_stmt = select(func.count()).select_from(OrmSKU).where(*conditions)
        count_result = await self._session.execute(count_stmt)
        total: int = count_result.scalar_one()

        # Fetch page
        stmt = (
            select(OrmSKU)
            .where(*conditions)
            .options(
                selectinload(OrmSKU.attribute_values),
                selectinload(OrmSKU.variant),
            )
            .order_by(OrmSKU.created_at)
        )
        stmt = stmt.offset(query.offset)
        if query.limit is not None:
            stmt = stmt.limit(query.limit)

        result = await self._session.execute(stmt)
        rows = result.scalars().all()

        items: list[SKUReadModel] = []
        for orm in rows:
            variant_default: MoneyReadModel | None = None
            if orm.variant is not None and orm.variant.default_price is not None:
                variant_default = MoneyReadModel(
                    amount=orm.variant.default_price,
                    currency=orm.variant.default_currency,
                )
            items.append(
                sku_orm_to_read_model(orm, variant_default_price=variant_default)
            )

        return SKUListReadModel(
            items=items,
            total=total,
            offset=query.offset,
            limit=query.limit if query.limit is not None else total,
        )
