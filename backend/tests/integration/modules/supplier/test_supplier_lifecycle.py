import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.supplier.domain.entities import Supplier
from src.modules.supplier.domain.exceptions import (
    SupplierInactiveError,
    SupplierNotFoundError,
)
from src.modules.supplier.domain.value_objects import SupplierType
from src.modules.supplier.infrastructure.query_service import SupplierQueryService
from src.modules.supplier.infrastructure.repositories.supplier import SupplierRepository


async def test_deactivate_supplier(db_session: AsyncSession):
    repo = SupplierRepository(session=db_session)
    supplier = Supplier.create(
        name="To Deactivate", supplier_type=SupplierType.LOCAL, region="Moscow",
    )
    await repo.add(supplier)
    supplier.deactivate()
    updated = await repo.update(supplier)
    assert updated.is_active is False


async def test_assert_active_raises_for_inactive(db_session: AsyncSession):
    repo = SupplierRepository(session=db_session)
    query_svc = SupplierQueryService(session=db_session)
    supplier = Supplier.create(
        name="Inactive", supplier_type=SupplierType.LOCAL, region="Moscow",
    )
    await repo.add(supplier)
    supplier.deactivate()
    await repo.update(supplier)

    with pytest.raises(SupplierInactiveError):
        await query_svc.assert_supplier_active(supplier.id)


async def test_assert_active_raises_for_nonexistent(db_session: AsyncSession):
    query_svc = SupplierQueryService(session=db_session)

    with pytest.raises(SupplierNotFoundError):
        await query_svc.assert_supplier_active(uuid.uuid4())
