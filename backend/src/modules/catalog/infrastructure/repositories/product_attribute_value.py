"""
ProductAttributeValue repository -- Data Mapper implementation.

Translates between :class:`~src.modules.catalog.domain.entities.ProductAttributeValue`
(domain) and the ``product_attribute_values`` ORM table. Provides duplicate-guard
checks scoped to the (product_id, attribute_id) pair.
"""

import uuid

from sqlalchemy import select

from src.modules.catalog.domain.entities import (
    ProductAttributeValue as DomainProductAttributeValue,
)
from src.modules.catalog.domain.interfaces import IProductAttributeValueRepository
from src.modules.catalog.infrastructure.models import (
    ProductAttributeValue as OrmProductAttributeValue,
)
from src.modules.catalog.infrastructure.repositories.base import BaseRepository


class ProductAttributeValueRepository(
    BaseRepository[DomainProductAttributeValue, OrmProductAttributeValue],
    IProductAttributeValueRepository,
    model_class=OrmProductAttributeValue,
):
    """Data Mapper repository for ProductAttributeValue child entities.

    Inherits generic CRUD from :class:`BaseRepository` and adds
    duplicate-guard checks and product-scoped queries.
    """

    def _to_domain(self, orm: OrmProductAttributeValue) -> DomainProductAttributeValue:
        """Map an ORM row to a domain entity."""
        return DomainProductAttributeValue(
            id=orm.id,
            product_id=orm.product_id,
            attribute_id=orm.attribute_id,
            attribute_value_id=orm.attribute_value_id,
        )

    def _to_orm(
        self,
        entity: DomainProductAttributeValue,
        orm: OrmProductAttributeValue | None = None,
    ) -> OrmProductAttributeValue:
        """Map a domain entity to an ORM row (create or update)."""
        if orm is None:
            orm = OrmProductAttributeValue()
        orm.id = entity.id
        orm.product_id = entity.product_id
        orm.attribute_id = entity.attribute_id
        orm.attribute_value_id = entity.attribute_value_id
        return orm

    async def list_by_product(
        self, product_id: uuid.UUID
    ) -> list[DomainProductAttributeValue]:
        """List all attribute assignments for a given product."""
        stmt = select(OrmProductAttributeValue).where(
            OrmProductAttributeValue.product_id == product_id
        ).order_by(OrmProductAttributeValue.attribute_id)
        result = await self._session.execute(stmt)
        return [self._to_domain(orm) for orm in result.scalars().all()]

    async def check_assignment_exists(
        self, product_id: uuid.UUID, attribute_id: uuid.UUID
    ) -> bool:
        """Check whether a product+attribute pair already exists (duplicate guard)."""
        stmt = (
            select(OrmProductAttributeValue.id)
            .where(
                OrmProductAttributeValue.product_id == product_id,
                OrmProductAttributeValue.attribute_id == attribute_id,
            )
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.first() is not None

    async def check_assignments_exist_bulk(
        self, product_id: uuid.UUID, attribute_ids: list[uuid.UUID]
    ) -> set[uuid.UUID]:
        """Return set of attribute_ids that already have assignments for this product."""
        if not attribute_ids:
            return set()
        stmt = select(OrmProductAttributeValue.attribute_id).where(
            OrmProductAttributeValue.product_id == product_id,
            OrmProductAttributeValue.attribute_id.in_(attribute_ids),
        )
        result = await self._session.execute(stmt)
        return {row[0] for row in result.all()}

    async def get_by_product_and_attribute(
        self, product_id: uuid.UUID, attribute_id: uuid.UUID
    ) -> DomainProductAttributeValue | None:
        """Retrieve a PAV by product+attribute pair, or None."""
        stmt = (
            select(OrmProductAttributeValue)
            .where(
                OrmProductAttributeValue.product_id == product_id,
                OrmProductAttributeValue.attribute_id == attribute_id,
            )
            .limit(1)
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None
