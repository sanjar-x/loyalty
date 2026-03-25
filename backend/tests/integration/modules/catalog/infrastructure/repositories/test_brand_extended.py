# tests/integration/modules/catalog/infrastructure/repositories/test_brand_extended.py
"""Extended integration tests for BrandRepository — update, delete, get_by_slug, slug exclusion, for_update."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.domain.entities import Brand
from src.modules.catalog.infrastructure.repositories.brand import BrandRepository


def _make_brand(name: str = "TestBrand", slug: str | None = None) -> Brand:
    return Brand.create(name=name, slug=slug or name.lower().replace(" ", "-"))


async def test_update_brand(db_session: AsyncSession):
    repo = BrandRepository(session=db_session)
    brand = _make_brand(name="OldName", slug="old-name")
    await repo.add(brand)
    await db_session.flush()

    brand.update(name="NewName", slug="new-name")
    updated = await repo.update(brand)

    assert updated.name == "NewName"
    assert updated.slug == "new-name"


async def test_update_nonexistent_raises(db_session: AsyncSession):
    repo = BrandRepository(session=db_session)
    brand = _make_brand(name="Ghost", slug="ghost")

    import pytest

    with pytest.raises(ValueError, match="not found in DB"):
        await repo.update(brand)


async def test_delete_brand(db_session: AsyncSession):
    repo = BrandRepository(session=db_session)
    brand = _make_brand(name="DeleteMe", slug="delete-me")
    await repo.add(brand)
    await db_session.flush()

    await repo.delete(brand.id)
    await db_session.flush()

    assert await repo.get(brand.id) is None


async def test_get_returns_none_for_missing(db_session: AsyncSession):
    repo = BrandRepository(session=db_session)
    assert await repo.get(uuid.uuid4()) is None


async def test_get_by_slug(db_session: AsyncSession):
    repo = BrandRepository(session=db_session)
    brand = _make_brand(name="Puma", slug="puma")
    await repo.add(brand)
    await db_session.flush()

    found = await repo.get_by_slug("puma")
    assert found is not None
    assert found.id == brand.id

    not_found = await repo.get_by_slug("nonexistent")
    assert not_found is None


async def test_check_slug_exists_excluding(db_session: AsyncSession):
    repo = BrandRepository(session=db_session)
    brand = _make_brand(name="Reebok", slug="reebok")
    await repo.add(brand)
    await db_session.flush()

    # Slug exists but exclude self — should be False
    assert await repo.check_slug_exists_excluding("reebok", brand.id) is False
    # Slug exists excluding a different ID — should be True
    assert await repo.check_slug_exists_excluding("reebok", uuid.uuid4()) is True
    # Non-existent slug — should be False
    assert await repo.check_slug_exists_excluding("nope", uuid.uuid4()) is False


async def test_get_for_update(db_session: AsyncSession):
    repo = BrandRepository(session=db_session)
    brand = _make_brand(name="Locked", slug="locked")
    await repo.add(brand)
    await db_session.flush()

    locked = await repo.get_for_update(brand.id)
    assert locked is not None
    assert locked.id == brand.id

    assert await repo.get_for_update(uuid.uuid4()) is None


async def test_brand_with_logo_fields(db_session: AsyncSession):
    repo = BrandRepository(session=db_session)
    storage_object_id = uuid.uuid4()
    brand = Brand.create(
        name="WithLogo",
        slug="with-logo",
        logo_url="https://cdn.example.com/logo.png",
        logo_storage_object_id=storage_object_id,
    )
    await repo.add(brand)
    await db_session.flush()

    fetched = await repo.get(brand.id)
    assert fetched is not None
    assert fetched.logo_storage_object_id == storage_object_id
    assert fetched.logo_url == "https://cdn.example.com/logo.png"
