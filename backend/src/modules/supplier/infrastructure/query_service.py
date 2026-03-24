"""Cross-module supplier query service implementation."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.supplier.domain.exceptions import (
    SupplierInactiveError,
    SupplierNotFoundError,
)
from src.modules.supplier.domain.interfaces import ISupplierQueryService, SupplierInfo
from src.modules.supplier.infrastructure.models import Supplier as OrmSupplier


class SupplierQueryService(ISupplierQueryService):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_supplier_info(self, supplier_id: uuid.UUID) -> SupplierInfo | None:
        stmt = select(OrmSupplier).where(OrmSupplier.id == supplier_id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm is None:
            return None
        return SupplierInfo(
            id=orm.id, name=orm.name, type=orm.type, is_active=orm.is_active
        )

    async def assert_supplier_active(self, supplier_id: uuid.UUID) -> SupplierInfo:
        info = await self.get_supplier_info(supplier_id)
        if info is None:
            raise SupplierNotFoundError(supplier_id)
        if not info.is_active:
            raise SupplierInactiveError(supplier_id)
        return info
