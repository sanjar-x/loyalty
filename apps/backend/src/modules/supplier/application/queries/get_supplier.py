"""Query handler: retrieve a single supplier by ID."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.supplier.application.queries.read_models import SupplierReadModel
from src.modules.supplier.domain.exceptions import SupplierNotFoundError
from src.modules.supplier.infrastructure.models import Supplier as OrmSupplier
from src.shared.interfaces.logger import ILogger


def supplier_orm_to_read_model(orm: OrmSupplier) -> SupplierReadModel:
    return SupplierReadModel(
        id=orm.id,
        name=orm.name,
        type=orm.type.value,
        country_code=orm.country_code,
        subdivision_code=orm.subdivision_code,
        is_active=orm.is_active,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


class GetSupplierHandler:
    def __init__(self, session: AsyncSession, logger: ILogger):
        self._session = session
        self._logger = logger.bind(handler="GetSupplierHandler")

    async def handle(self, supplier_id: uuid.UUID) -> SupplierReadModel:
        stmt = select(OrmSupplier).where(OrmSupplier.id == supplier_id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()

        if orm is None:
            raise SupplierNotFoundError(supplier_id)

        return supplier_orm_to_read_model(orm)
