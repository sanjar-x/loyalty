# tests/integration/modules/catalog/infrastructure/repositories/test_category_extended.py
"""Extended integration tests for CategoryRepository — CRUD, tree queries, slug exclusion, descendants."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.domain.entities import Category
from src.modules.catalog.infrastructure.repositories.category import CategoryRepository


async def test_get_returns_none_for_missing(db_session: AsyncSession):
    repo = CategoryRepository(session=db_session)
    assert await repo.get(uuid.uuid4()) is None


async def test_delete_category(db_session: AsyncSession):
    repo = CategoryRepository(session=db_session)
    cat = Category.create_root(name_i18n={"en": "Temp"}, slug="temp", sort_order=1)
    await repo.add(cat)
    await db_session.flush()

    await repo.delete(cat.id)
    await db_session.flush()

    assert await repo.get(cat.id) is None


async def test_get_for_update(db_session: AsyncSession):
    repo = CategoryRepository(session=db_session)
    cat = Category.create_root(name_i18n={"en": "LockMe"}, slug="lock-me", sort_order=1)
    await repo.add(cat)
    await db_session.flush()

    locked = await repo.get_for_update(cat.id)
    assert locked is not None
    assert locked.id == cat.id

    assert await repo.get_for_update(uuid.uuid4()) is None


async def test_check_slug_exists_excluding(db_session: AsyncSession):
    repo = CategoryRepository(session=db_session)
    cat = Category.create_root(name_i18n={"en": "Books"}, slug="books-excl", sort_order=1)
    await repo.add(cat)
    await db_session.flush()

    # Exclude self — should be False
    assert await repo.check_slug_exists_excluding("books-excl", None, cat.id) is False
    # Exclude different ID — should be True
    assert await repo.check_slug_exists_excluding("books-excl", None, uuid.uuid4()) is True
    # Nonexistent slug — should be False
    assert await repo.check_slug_exists_excluding("no-such", None, uuid.uuid4()) is False


async def test_has_children(db_session: AsyncSession):
    repo = CategoryRepository(session=db_session)
    root = Category.create_root(name_i18n={"en": "Parent"}, slug="parent-hc", sort_order=1)
    child = Category.create_child(name_i18n={"en": "Child"}, slug="child-hc", parent=root, sort_order=1)
    await repo.add(root)
    await repo.add(child)
    await db_session.flush()

    assert await repo.has_children(root.id) is True
    assert await repo.has_children(child.id) is False
    assert await repo.has_children(uuid.uuid4()) is False


async def test_update_category(db_session: AsyncSession):
    repo = CategoryRepository(session=db_session)
    cat = Category.create_root(name_i18n={"en": "Original"}, slug="original", sort_order=5)
    await repo.add(cat)
    await db_session.flush()

    cat.update(name_i18n={"en": "Updated"}, sort_order=10)
    await repo.update(cat)
    await db_session.flush()

    fetched = await repo.get(cat.id)
    assert fetched is not None
    assert fetched.name_i18n == {"en": "Updated"}
    assert fetched.sort_order == 10


async def test_update_descendants_full_slug(db_session: AsyncSession):
    repo = CategoryRepository(session=db_session)

    root = Category.create_root(name_i18n={"en": "Electronics"}, slug="electronics", sort_order=1)
    child = Category.create_child(name_i18n={"en": "Laptops"}, slug="laptops", parent=root, sort_order=1)
    grandchild = Category.create_child(name_i18n={"en": "Gaming"}, slug="gaming", parent=child, sort_order=1)

    await repo.add(root)
    await repo.add(child)
    await repo.add(grandchild)
    await db_session.flush()

    # Rename root slug from "electronics" to "tech"
    await repo.update_descendants_full_slug("electronics", "tech")
    await db_session.flush()

    # Expire to re-fetch from DB
    db_session.expire_all()

    updated_child = await repo.get(child.id)
    updated_grandchild = await repo.get(grandchild.id)

    assert updated_child is not None
    assert updated_child.full_slug == "tech/laptops"
    assert updated_grandchild is not None
    assert updated_grandchild.full_slug == "tech/laptops/gaming"


async def test_get_all_ordered_empty(db_session: AsyncSession):
    repo = CategoryRepository(session=db_session)
    cats = await repo.get_all_ordered()
    assert cats == []
