"""Supplier repository — Data Mapper implementation."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.supplier.domain.entities import Supplier as DomainSupplier
from src.modules.supplier.domain.interfaces import ISupplierRepository
from src.modules.supplier.infrastructure.models import Supplier as OrmSupplier


class SupplierRepository(ISupplierRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_domain(self, orm: OrmSupplier) -> DomainSupplier:
        return DomainSupplier(
            id=orm.id,
            name=orm.name,
            type=orm.type,
            country_code=orm.country_code,
            subdivision_code=orm.subdivision_code,
            is_active=orm.is_active,
            version=orm.version,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )

    def _to_orm(
        self, entity: DomainSupplier, orm: OrmSupplier | None = None
    ) -> OrmSupplier:
        if orm is None:
            orm = OrmSupplier()
        orm.id = entity.id
        orm.name = entity.name
        orm.type = entity.type
        orm.country_code = entity.country_code
        orm.subdivision_code = entity.subdivision_code
        orm.is_active = entity.is_active
        return orm

    async def add(self, entity: DomainSupplier) -> DomainSupplier:
        orm = self._to_orm(entity)
        self._session.add(orm)
        await self._session.flush()
        return self._to_domain(orm)

    async def get(self, entity_id: uuid.UUID) -> DomainSupplier | None:
        orm = await self._session.get(OrmSupplier, entity_id)
        if orm:
            return self._to_domain(orm)
        return None

    async def update(self, entity: DomainSupplier) -> DomainSupplier:
        orm = await self._session.get(OrmSupplier, entity.id)
        if not orm:
            raise ValueError(f"Supplier with id {entity.id} not found in database")
        orm = self._to_orm(entity, orm)
        await self._session.flush()
        return self._to_domain(orm)
