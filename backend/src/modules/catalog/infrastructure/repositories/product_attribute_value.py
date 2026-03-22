"""
ProductAttributeValue repository -- Data Mapper implementation.

Translates between :class:`~src.modules.catalog.domain.entities.ProductAttributeValue`
(domain) and the ``product_attribute_values`` ORM table. Provides duplicate-guard
checks scoped to the (product_id, attribute_id) pair.
"""

import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.domain.entities import (
    ProductAttributeValue as DomainProductAttributeValue,
)
from src.modules.catalog.domain.interfaces import IProductAttributeValueRepository
from src.modules.catalog.infrastructure.models import (
    ProductAttributeValue as OrmProductAttributeValue,
)


class ProductAttributeValueRepository(IProductAttributeValueRepository):
    """Data Mapper repository for ProductAttributeValue child entities.

    Args:
        session: SQLAlchemy async session scoped to the current request.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_domain(self, orm: OrmProductAttributeValue) -> DomainProductAttributeValue:
        """Map an ORM row to a domain entity."""
        return DomainProductAttributeValue(
            id=orm.id,
            product_id=orm.product_id,
            attribute_id=orm.attribute_id,
            attribute_value_id=orm.attribute_value_id,
        )

    def _to_orm(self, entity: DomainProductAttributeValue) -> OrmProductAttributeValue:
        """Map a domain entity to an ORM row."""
        orm = OrmProductAttributeValue()
        orm.id = entity.id
        orm.product_id = entity.product_id
        orm.attribute_id = entity.attribute_id
        orm.attribute_value_id = entity.attribute_value_id
        return orm

    async def add(self, entity: DomainProductAttributeValue) -> DomainProductAttributeValue:
        """Persist a new product attribute assignment and return the refreshed domain entity."""
        orm = self._to_orm(entity)
        self._session.add(orm)
        await self._session.flush()
        return self._to_domain(orm)

    async def get(self, pav_id: uuid.UUID) -> DomainProductAttributeValue | None:
        """Retrieve a product attribute value by primary key, or ``None``."""
        orm = await self._session.get(OrmProductAttributeValue, pav_id)
        if orm:
            return self._to_domain(orm)
        return None

    async def delete(self, pav_id: uuid.UUID) -> None:
        """Delete a product attribute assignment by primary key."""
        stmt = delete(OrmProductAttributeValue).where(OrmProductAttributeValue.id == pav_id)
        await self._session.execute(stmt)

    async def list_by_product(self, product_id: uuid.UUID) -> list[DomainProductAttributeValue]:
        """List all attribute assignments for a given product."""
        stmt = select(OrmProductAttributeValue).where(
            OrmProductAttributeValue.product_id == product_id
        )
        result = await self._session.execute(stmt)
        return [self._to_domain(orm) for orm in result.scalars().all()]

    async def exists(self, product_id: uuid.UUID, attribute_id: uuid.UUID) -> bool:
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
