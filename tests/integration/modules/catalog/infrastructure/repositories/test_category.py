import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.domain.entities import Category
from src.modules.catalog.infrastructure.repositories.category import CategoryRepository


async def test_category_repository_add_and_get_all_ordered(db_session: AsyncSession):
    # Arrange
    repository = CategoryRepository(session=db_session)

    # Let's create two categories
    root_category = Category.create_root(
        name="Electronics",
        slug="electronics",
        sort_order=10,
    )

    child_category = Category.create_child(
        name="Laptops",
        slug="laptops",
        parent=root_category,
        sort_order=1,
    )

    # Act
    await repository.add(root_category)
    await repository.add(child_category)

    # Because of our nested transaction, DB changes are saved for checking
    categories = await repository.get_all_ordered()

    # Assert
    assert len(categories) == 2
    # root level 0, sort 10 -> child level 1, sort 1
    # the order by level asc, sort_order asc should put root first, child second
    assert categories[0].id == root_category.id
    assert categories[1].id == child_category.id


async def test_category_repository_check_slug_exists(db_session: AsyncSession):
    # Arrange
    repository = CategoryRepository(session=db_session)
    category = Category.create_root(
        name="Books",
        slug="books",
        sort_order=1,
    )
    await repository.add(category)

    # Act
    exists_same_level = await repository.check_slug_exists(slug="books", parent_id=None)
    exists_other_level = await repository.check_slug_exists(
        slug="books", parent_id=uuid.uuid4()
    )
    not_exists = await repository.check_slug_exists(slug="magazines", parent_id=None)

    # Assert
    assert exists_same_level is True
    assert exists_other_level is False
    assert not_exists is False
