from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.supplier.domain.entities import Supplier
from src.modules.supplier.domain.value_objects import SupplierType
from src.modules.supplier.infrastructure.repositories.supplier import SupplierRepository


async def test_supplier_repository_add_and_get(db_session: AsyncSession):
    repo = SupplierRepository(session=db_session)
    supplier = Supplier.create(
        name="Test Supplier",
        supplier_type=SupplierType.LOCAL,
        country_code="RU",
        subdivision_code="RU-MOW",
    )
    added = await repo.add(supplier)
    fetched = await repo.get(supplier.id)
    assert added.id == supplier.id
    assert fetched is not None
    assert fetched.name == "Test Supplier"
    assert fetched.type == SupplierType.LOCAL
    assert fetched.country_code == "RU"
    assert fetched.subdivision_code == "RU-MOW"
    assert fetched.is_active is True


async def test_supplier_repository_update(db_session: AsyncSession):
    repo = SupplierRepository(session=db_session)
    supplier = Supplier.create(
        name="Old Name",
        supplier_type=SupplierType.LOCAL,
        country_code="RU",
    )
    await repo.add(supplier)
    supplier.update(name="New Name")
    updated = await repo.update(supplier)
    assert updated.name == "New Name"


async def test_supplier_repository_deactivate(db_session: AsyncSession):
    repo = SupplierRepository(session=db_session)
    supplier = Supplier.create(
        name="Active Supplier",
        supplier_type=SupplierType.CROSS_BORDER,
        country_code="CN",
    )
    await repo.add(supplier)
    supplier.deactivate()
    updated = await repo.update(supplier)
    assert updated.is_active is False
