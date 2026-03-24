"""Query handler: paginated supplier listing."""

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.supplier.application.queries.get_supplier import (
    supplier_orm_to_read_model,
)
from src.modules.supplier.application.queries.read_models import SupplierListReadModel
from src.modules.supplier.infrastructure.models import Supplier as OrmSupplier
from src.shared.interfaces.logger import ILogger


@dataclass(frozen=True)
class ListSuppliersQuery:
    offset: int = 0
    limit: int = 50


class ListSuppliersHandler:
    def __init__(self, session: AsyncSession, logger: ILogger):
        self._session = session
        self._logger = logger.bind(handler="ListSuppliersHandler")

    async def handle(self, query: ListSuppliersQuery) -> SupplierListReadModel:
        count_result = await self._session.execute(
            select(func.count()).select_from(OrmSupplier)
        )
        total = count_result.scalar_one()

        stmt = (
            select(OrmSupplier)
            .order_by(OrmSupplier.name)
            .limit(query.limit)
            .offset(query.offset)
        )
        result = await self._session.execute(stmt)
        rows = result.scalars().all()

        items = [supplier_orm_to_read_model(orm) for orm in rows]
        return SupplierListReadModel(
            items=items, total=total, offset=query.offset, limit=query.limit,
        )
