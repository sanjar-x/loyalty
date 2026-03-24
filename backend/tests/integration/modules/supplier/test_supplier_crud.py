from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.supplier.domain.entities import Supplier
from src.modules.supplier.domain.value_objects import SupplierType
from src.modules.supplier.infrastructure.query_service import SupplierQueryService
from src.modules.supplier.infrastructure.repositories.supplier import SupplierRepository


async def test_create_local_supplier(db_session: AsyncSession):
    repo = SupplierRepository(session=db_session)
    supplier = Supplier.create(
        name="Moscow Store",
        supplier_type=SupplierType.LOCAL,
        region="Moscow",
    )
    result = await repo.add(supplier)
    assert result.id == supplier.id
    assert result.is_active is True


async def test_create_cross_border_supplier(db_session: AsyncSession):
    repo = SupplierRepository(session=db_session)
    supplier = Supplier.create(
        name="Poizon",
        supplier_type=SupplierType.CROSS_BORDER,
        region="China",
    )
    result = await repo.add(supplier)
    assert result.type == SupplierType.CROSS_BORDER


async def test_update_supplier_name(db_session: AsyncSession):
    repo = SupplierRepository(session=db_session)
    supplier = Supplier.create(
        name="Old Name",
        supplier_type=SupplierType.LOCAL,
        region="Moscow",
    )
    await repo.add(supplier)
    supplier.update(name="New Name")
    updated = await repo.update(supplier)
    assert updated.name == "New Name"


async def test_query_service_get_info(db_session: AsyncSession):
    repo = SupplierRepository(session=db_session)
    query_svc = SupplierQueryService(session=db_session)
    supplier = Supplier.create(
        name="Test",
        supplier_type=SupplierType.LOCAL,
        region="Moscow",
    )
    await repo.add(supplier)

    info = await query_svc.get_supplier_info(supplier.id)
    assert info is not None
    assert info.name == "Test"
    assert info.is_active is True
