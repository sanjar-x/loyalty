"""Unit tests for all catalog command handlers."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from _pytest.mark.structures import MarkDecorator

from src.modules.catalog.application.commands.delete_brand import (
    DeleteBrandCommand,
    DeleteBrandHandler,
)
from src.modules.catalog.application.commands.delete_category import (
    DeleteCategoryCommand,
    DeleteCategoryHandler,
)
from src.modules.catalog.application.commands.update_brand import (
    UpdateBrandCommand,
    UpdateBrandHandler,
)
from src.modules.catalog.application.commands.update_category import (
    UpdateCategoryCommand,
    UpdateCategoryHandler,
)
from src.modules.catalog.application.constants import CATEGORY_TREE_CACHE_KEY
from src.modules.catalog.domain.exceptions import (
    BrandNotFoundError,
    BrandSlugConflictError,
    CategoryHasChildrenError,
    CategoryNotFoundError,
    CategorySlugConflictError,
)

pytestmark: MarkDecorator = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_uow() -> AsyncMock:
    uow = AsyncMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=False)
    uow.register_aggregate = MagicMock()
    return uow


def make_logger() -> MagicMock:
    logger = MagicMock()
    logger.bind = MagicMock(return_value=logger)
    logger.info = MagicMock()
    return logger


def make_brand(
    brand_id: uuid.UUID | None = None,
    name: str = "Test Brand",
    slug: str = "test-brand",
    logo_url: str | None = None,
    logo_status: None = None,
) -> MagicMock:
    brand = MagicMock()
    brand.id = brand_id or uuid.uuid4()
    brand.name = name
    brand.slug = slug
    brand.logo_url = logo_url
    brand.logo_status = logo_status
    brand.update = MagicMock()
    return brand


def make_category(
    cat_id: uuid.UUID | None = None,
    name: str = "Electronics",
    slug: str = "electronics",
    full_slug: str = "electronics",
    level: int = 0,
    sort_order: int = 1,
    parent_id: uuid.UUID | None = None,
) -> MagicMock:
    category = MagicMock()
    category.id = cat_id or uuid.uuid4()
    category.name = name
    category.slug = slug
    category.full_slug = full_slug
    category.level = level
    category.sort_order = sort_order
    category.parent_id = parent_id
    # update() returns old_full_slug (str) when slug changed, or None otherwise
    category.update = MagicMock(return_value=None)
    return category


# ===========================================================================
# DeleteBrandHandler
# ===========================================================================


class TestDeleteBrandHandler:
    async def test_delete_brand_success(self) -> None:
        brand_id = uuid.uuid4()
        brand = make_brand(brand_id=brand_id)

        brand_repo = AsyncMock()
        brand_repo.get.return_value = brand

        uow = make_uow()
        logger = make_logger()

        handler = DeleteBrandHandler(brand_repo=brand_repo, uow=uow, logger=logger)
        await handler.handle(DeleteBrandCommand(brand_id=brand_id))

        brand_repo.get.assert_awaited_once_with(brand_id)
        uow.register_aggregate.assert_called_once_with(brand)
        brand_repo.delete.assert_awaited_once_with(brand_id)
        uow.commit.assert_awaited_once()

    async def test_delete_brand_not_found(self) -> None:
        brand_id = uuid.uuid4()

        brand_repo = AsyncMock()
        brand_repo.get.return_value = None

        uow = make_uow()
        logger = make_logger()

        handler = DeleteBrandHandler(brand_repo=brand_repo, uow=uow, logger=logger)

        with pytest.raises(BrandNotFoundError):
            await handler.handle(DeleteBrandCommand(brand_id=brand_id))

        brand_repo.delete.assert_not_awaited()
        uow.commit.assert_not_awaited()


# ===========================================================================
# UpdateBrandHandler
# ===========================================================================


class TestUpdateBrandHandler:
    async def test_update_brand_name_only(self) -> None:
        brand_id = uuid.uuid4()
        brand = make_brand(brand_id=brand_id, name="Old Name", slug="old-slug")

        brand_repo = AsyncMock()
        brand_repo.get_for_update.return_value = brand

        uow = make_uow()
        logger = make_logger()

        handler = UpdateBrandHandler(brand_repo=brand_repo, uow=uow, logger=logger)
        result = await handler.handle(UpdateBrandCommand(brand_id=brand_id, name="New Name"))

        # slug was not provided, so no slug conflict check
        brand_repo.check_slug_exists_excluding.assert_not_awaited()
        brand.update.assert_called_once_with(name="New Name", slug=None)
        brand_repo.update.assert_awaited_once_with(brand)
        uow.register_aggregate.assert_called_once_with(brand)
        uow.commit.assert_awaited_once()
        assert result.id == brand_id

    async def test_update_brand_slug_success(self) -> None:
        brand_id = uuid.uuid4()
        brand = make_brand(brand_id=brand_id, slug="old-slug")

        brand_repo = AsyncMock()
        brand_repo.get_for_update.return_value = brand
        brand_repo.check_slug_exists_excluding.return_value = False

        uow = make_uow()
        logger = make_logger()

        handler = UpdateBrandHandler(brand_repo=brand_repo, uow=uow, logger=logger)
        result = await handler.handle(UpdateBrandCommand(brand_id=brand_id, slug="new-slug"))

        brand_repo.check_slug_exists_excluding.assert_awaited_once_with("new-slug", brand_id)
        brand.update.assert_called_once_with(name=None, slug="new-slug")
        uow.commit.assert_awaited_once()
        assert result.id == brand_id

    async def test_update_brand_not_found(self) -> None:
        brand_id = uuid.uuid4()

        brand_repo = AsyncMock()
        brand_repo.get_for_update.return_value = None

        uow = make_uow()
        logger = make_logger()

        handler = UpdateBrandHandler(brand_repo=brand_repo, uow=uow, logger=logger)

        with pytest.raises(BrandNotFoundError):
            await handler.handle(UpdateBrandCommand(brand_id=brand_id, name="Whatever"))

        brand_repo.update.assert_not_awaited()
        uow.commit.assert_not_awaited()

    async def test_update_brand_slug_conflict(self) -> None:
        brand_id = uuid.uuid4()
        brand = make_brand(brand_id=brand_id, slug="old-slug")

        brand_repo = AsyncMock()
        brand_repo.get_for_update.return_value = brand
        brand_repo.check_slug_exists_excluding.return_value = True

        uow = make_uow()
        logger = make_logger()

        handler = UpdateBrandHandler(brand_repo=brand_repo, uow=uow, logger=logger)

        with pytest.raises(BrandSlugConflictError):
            await handler.handle(UpdateBrandCommand(brand_id=brand_id, slug="taken-slug"))

        brand.update.assert_not_called()
        brand_repo.update.assert_not_awaited()
        uow.commit.assert_not_awaited()

    async def test_update_brand_same_slug_skips_check(self) -> None:
        brand_id = uuid.uuid4()
        brand = make_brand(brand_id=brand_id, slug="same-slug")

        brand_repo = AsyncMock()
        brand_repo.get_for_update.return_value = brand

        uow = make_uow()
        logger = make_logger()

        handler = UpdateBrandHandler(brand_repo=brand_repo, uow=uow, logger=logger)
        result = await handler.handle(UpdateBrandCommand(brand_id=brand_id, slug="same-slug"))

        # Same slug as current -> no conflict check
        brand_repo.check_slug_exists_excluding.assert_not_awaited()
        brand.update.assert_called_once_with(name=None, slug="same-slug")
        uow.commit.assert_awaited_once()
        assert result.id == brand_id


# ===========================================================================
# DeleteCategoryHandler
# ===========================================================================


class TestDeleteCategoryHandler:
    async def test_delete_category_success(self) -> None:
        cat_id = uuid.uuid4()
        category = make_category(cat_id=cat_id)

        category_repo = AsyncMock()
        category_repo.get.return_value = category
        category_repo.has_children.return_value = False

        uow = make_uow()
        cache = AsyncMock()
        logger = make_logger()

        handler = DeleteCategoryHandler(
            category_repo=category_repo, uow=uow, cache=cache, logger=logger
        )
        await handler.handle(DeleteCategoryCommand(category_id=cat_id))

        category_repo.get.assert_awaited_once_with(cat_id)
        category_repo.has_children.assert_awaited_once_with(cat_id)
        uow.register_aggregate.assert_called_once_with(category)
        category_repo.delete.assert_awaited_once_with(cat_id)
        uow.commit.assert_awaited_once()
        cache.delete.assert_awaited_once_with(CATEGORY_TREE_CACHE_KEY)

    async def test_delete_category_not_found(self) -> None:
        cat_id = uuid.uuid4()

        category_repo = AsyncMock()
        category_repo.get.return_value = None

        uow = make_uow()
        cache = AsyncMock()
        logger = make_logger()

        handler = DeleteCategoryHandler(
            category_repo=category_repo, uow=uow, cache=cache, logger=logger
        )

        with pytest.raises(CategoryNotFoundError):
            await handler.handle(DeleteCategoryCommand(category_id=cat_id))

        category_repo.delete.assert_not_awaited()
        uow.commit.assert_not_awaited()

    async def test_delete_category_has_children(self) -> None:
        cat_id = uuid.uuid4()
        category = make_category(cat_id=cat_id)

        category_repo = AsyncMock()
        category_repo.get.return_value = category
        category_repo.has_children.return_value = True

        uow = make_uow()
        cache = AsyncMock()
        logger = make_logger()

        handler = DeleteCategoryHandler(
            category_repo=category_repo, uow=uow, cache=cache, logger=logger
        )

        with pytest.raises(CategoryHasChildrenError):
            await handler.handle(DeleteCategoryCommand(category_id=cat_id))

        category_repo.delete.assert_not_awaited()
        uow.commit.assert_not_awaited()

    async def test_delete_category_cache_error_suppressed(self) -> None:
        cat_id = uuid.uuid4()
        category = make_category(cat_id=cat_id)

        category_repo = AsyncMock()
        category_repo.get.return_value = category
        category_repo.has_children.return_value = False

        uow = make_uow()
        cache = AsyncMock()
        cache.delete.side_effect = RuntimeError("Redis down")
        logger = make_logger()

        handler = DeleteCategoryHandler(
            category_repo=category_repo, uow=uow, cache=cache, logger=logger
        )

        # Should NOT raise despite cache.delete raising
        await handler.handle(DeleteCategoryCommand(category_id=cat_id))

        uow.commit.assert_awaited_once()
        cache.delete.assert_awaited_once_with(CATEGORY_TREE_CACHE_KEY)


# ===========================================================================
# UpdateCategoryHandler
# ===========================================================================


class TestUpdateCategoryHandler:
    async def test_update_category_name_only(self) -> None:
        cat_id = uuid.uuid4()
        category = make_category(cat_id=cat_id, name="Old Name", slug="old-slug")
        # update returns None when slug did not change
        category.update.return_value = None

        category_repo = AsyncMock()
        category_repo.get_for_update.return_value = category

        uow = make_uow()
        cache = AsyncMock()
        logger = make_logger()

        handler = UpdateCategoryHandler(
            category_repo=category_repo, uow=uow, cache=cache, logger=logger
        )
        result = await handler.handle(UpdateCategoryCommand(category_id=cat_id, name="New Name"))

        category_repo.check_slug_exists_excluding.assert_not_awaited()
        category.update.assert_called_once_with(name="New Name", slug=None, sort_order=None)
        # No slug change -> no descendant update
        category_repo.update_descendants_full_slug.assert_not_awaited()
        uow.commit.assert_awaited_once()
        assert result.id == cat_id

    async def test_update_category_slug_success(self) -> None:
        cat_id = uuid.uuid4()
        category = make_category(
            cat_id=cat_id,
            slug="old-slug",
            full_slug="old-slug",
            parent_id=None,
        )
        # update returns old_full_slug when slug changed
        category.update.return_value = "old-slug"
        # After update, full_slug is the new value
        category.full_slug = "new-slug"

        category_repo = AsyncMock()
        category_repo.get_for_update.return_value = category
        category_repo.check_slug_exists_excluding.return_value = False

        uow = make_uow()
        cache = AsyncMock()
        logger = make_logger()

        handler = UpdateCategoryHandler(
            category_repo=category_repo, uow=uow, cache=cache, logger=logger
        )
        result = await handler.handle(UpdateCategoryCommand(category_id=cat_id, slug="new-slug"))

        category_repo.check_slug_exists_excluding.assert_awaited_once_with("new-slug", None, cat_id)
        category.update.assert_called_once_with(name=None, slug="new-slug", sort_order=None)
        category_repo.update_descendants_full_slug.assert_awaited_once_with(
            old_prefix="old-slug",
            new_prefix="new-slug",
        )
        uow.commit.assert_awaited_once()
        cache.delete.assert_awaited_once_with(CATEGORY_TREE_CACHE_KEY)
        assert result.id == cat_id

    async def test_update_category_not_found(self) -> None:
        cat_id = uuid.uuid4()

        category_repo = AsyncMock()
        category_repo.get_for_update.return_value = None

        uow = make_uow()
        cache = AsyncMock()
        logger = make_logger()

        handler = UpdateCategoryHandler(
            category_repo=category_repo, uow=uow, cache=cache, logger=logger
        )

        with pytest.raises(CategoryNotFoundError):
            await handler.handle(UpdateCategoryCommand(category_id=cat_id, name="Whatever"))

        category_repo.update.assert_not_awaited()
        uow.commit.assert_not_awaited()

    async def test_update_category_slug_conflict(self) -> None:
        cat_id = uuid.uuid4()
        parent_id = uuid.uuid4()
        category = make_category(cat_id=cat_id, slug="old-slug", parent_id=parent_id)

        category_repo = AsyncMock()
        category_repo.get_for_update.return_value = category
        category_repo.check_slug_exists_excluding.return_value = True

        uow = make_uow()
        cache = AsyncMock()
        logger = make_logger()

        handler = UpdateCategoryHandler(
            category_repo=category_repo, uow=uow, cache=cache, logger=logger
        )

        with pytest.raises(CategorySlugConflictError):
            await handler.handle(UpdateCategoryCommand(category_id=cat_id, slug="taken-slug"))

        category.update.assert_not_called()
        category_repo.update.assert_not_awaited()
        uow.commit.assert_not_awaited()

    async def test_update_category_same_slug_skips_check(self) -> None:
        cat_id = uuid.uuid4()
        category = make_category(cat_id=cat_id, slug="same-slug")
        category.update.return_value = None

        category_repo = AsyncMock()
        category_repo.get_for_update.return_value = category

        uow = make_uow()
        cache = AsyncMock()
        logger = make_logger()

        handler = UpdateCategoryHandler(
            category_repo=category_repo, uow=uow, cache=cache, logger=logger
        )
        result = await handler.handle(UpdateCategoryCommand(category_id=cat_id, slug="same-slug"))

        # Same slug as current -> no conflict check
        category_repo.check_slug_exists_excluding.assert_not_awaited()
        category.update.assert_called_once_with(name=None, slug="same-slug", sort_order=None)
        uow.commit.assert_awaited_once()
        assert result.id == cat_id

    async def test_update_category_sort_order(self) -> None:
        cat_id = uuid.uuid4()
        category = make_category(cat_id=cat_id, sort_order=1)
        category.update.return_value = None

        category_repo = AsyncMock()
        category_repo.get_for_update.return_value = category

        uow = make_uow()
        cache = AsyncMock()
        logger = make_logger()

        handler = UpdateCategoryHandler(
            category_repo=category_repo, uow=uow, cache=cache, logger=logger
        )
        result = await handler.handle(UpdateCategoryCommand(category_id=cat_id, sort_order=5))

        category_repo.check_slug_exists_excluding.assert_not_awaited()
        category.update.assert_called_once_with(name=None, slug=None, sort_order=5)
        # No slug change -> no descendant update
        category_repo.update_descendants_full_slug.assert_not_awaited()
        uow.commit.assert_awaited_once()
        assert result.id == cat_id
