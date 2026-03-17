# src/modules/catalog/infrastructure/repositories/brand.py
import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.domain.entities import Brand as DomainBrand
from src.modules.catalog.domain.interfaces import IBrandRepository
from src.modules.catalog.infrastructure.models import Brand as OrmBrand


class BrandRepository(IBrandRepository):
    """
    Репозиторий Брендов, реализующий Data Mapper паттерн.
    Конвертирует данные между слоем БД (OrmBrand) и Доменным слоем (DomainBrand).
    """

    def __init__(self, session: AsyncSession):
        self._session = session

    def _to_domain(self, orm: OrmBrand) -> DomainBrand:
        return DomainBrand(
            id=orm.id,
            name=orm.name,
            slug=orm.slug,
            logo_status=orm.logo_status,
            logo_file_id=orm.logo_file_id,
            logo_url=orm.logo_url,
        )

    def _to_orm(self, domain: DomainBrand, orm: OrmBrand | None = None) -> OrmBrand:
        if orm is None:
            orm = OrmBrand()
        orm.id = domain.id
        orm.name = domain.name
        orm.slug = domain.slug
        orm.logo_status = domain.logo_status
        orm.logo_file_id = domain.logo_file_id
        orm.logo_url = domain.logo_url
        return orm

    async def add(self, brand: DomainBrand) -> DomainBrand:
        orm = self._to_orm(brand)
        self._session.add(orm)
        await self._session.flush()
        return self._to_domain(orm)

    async def get(self, brand_id: uuid.UUID) -> DomainBrand | None:
        orm = await self._session.get(OrmBrand, brand_id)
        if orm:
            return self._to_domain(orm)
        return None

    async def update(self, brand: DomainBrand) -> DomainBrand:
        orm = await self._session.get(OrmBrand, brand.id)
        if not orm:
            raise ValueError(f"Brand with id {brand.id} not found in DB")
        orm = self._to_orm(brand, orm)
        await self._session.flush()
        return self._to_domain(orm)

    async def delete(self, brand_id: uuid.UUID) -> None:
        statement = delete(OrmBrand).where(OrmBrand.id == brand_id)
        await self._session.execute(statement)

    async def get_by_slug(self, slug: str) -> DomainBrand | None:
        statement = select(OrmBrand).where(OrmBrand.slug == slug).limit(1)
        result = await self._session.execute(statement)
        orm = result.scalar_one_or_none()
        if orm:
            return self._to_domain(orm)
        return None

    async def check_slug_exists(self, slug: str) -> bool:
        statement = select(OrmBrand.id).where(OrmBrand.slug == slug).limit(1)
        result = await self._session.execute(statement)
        return result.first() is not None

    async def check_slug_exists_excluding(self, slug: str, exclude_id: uuid.UUID) -> bool:
        statement = (
            select(OrmBrand.id).where(OrmBrand.slug == slug, OrmBrand.id != exclude_id).limit(1)
        )
        result = await self._session.execute(statement)
        return result.first() is not None

    async def get_for_update(self, brand_id: uuid.UUID) -> DomainBrand | None:
        statement = select(OrmBrand).where(OrmBrand.id == brand_id).with_for_update()
        result = await self._session.execute(statement)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None
