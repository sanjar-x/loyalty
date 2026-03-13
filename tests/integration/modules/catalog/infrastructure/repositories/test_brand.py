from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.domain.entities import Brand
from src.modules.catalog.domain.value_objects import MediaProcessingStatus
from src.modules.catalog.infrastructure.repositories.brand import BrandRepository


async def test_brand_repository_add_and_get(db_session: AsyncSession):
    # Arrange
    repository = BrandRepository(session=db_session)
    brand = Brand.create(name="Nike", slug="nike")
    brand.logo_status = MediaProcessingStatus.PENDING_UPLOAD

    # Act
    added_brand = await repository.add(brand)
    fetched_brand = await repository.get(brand.id)

    # Assert
    assert added_brand.id == brand.id
    assert fetched_brand is not None
    assert fetched_brand.id == brand.id
    assert fetched_brand.name == "Nike"
    assert fetched_brand.slug == "nike"
    assert fetched_brand.logo_status == MediaProcessingStatus.PENDING_UPLOAD


async def test_brand_repository_check_slug_exists(db_session: AsyncSession):
    # Arrange
    repository = BrandRepository(session=db_session)
    brand = Brand.create(name="Adidas", slug="adidas")
    await repository.add(brand)

    # Act
    exists = await repository.check_slug_exists("adidas")
    does_not_exist = await repository.check_slug_exists("puma")

    # Assert
    assert exists is True
    assert does_not_exist is False
