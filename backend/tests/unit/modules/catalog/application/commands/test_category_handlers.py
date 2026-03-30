"""Unit tests for Category command handlers (CMD-02).

Tests all 4 Category command handlers:
- CreateCategoryHandler
- UpdateCategoryHandler
- DeleteCategoryHandler
- BulkCreateCategoriesHandler

Per D-01: one test class per handler.
Per D-02: one test file per entity domain.
Per D-03: uses FakeUnitOfWork for all repository interactions.
Per D-07: asserts uow.committed on happy path, uow.committed is False on rejection.
Per D-08: asserts events via uow.collected_events (not entity.domain_events).
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.modules.catalog.application.commands.bulk_create_categories import (
    BulkCategoryItem,
    BulkCreateCategoriesCommand,
    BulkCreateCategoriesHandler,
    MAX_BULK_CATEGORIES,
)
from src.modules.catalog.application.commands.create_category import (
    CreateCategoryCommand,
    CreateCategoryHandler,
)
from src.modules.catalog.application.commands.delete_category import (
    DeleteCategoryCommand,
    DeleteCategoryHandler,
)
from src.modules.catalog.application.commands.update_category import (
    UpdateCategoryCommand,
    UpdateCategoryHandler,
)
from src.modules.catalog.domain.entities import Category
from src.modules.catalog.domain.events import (
    CategoryCreatedEvent,
    CategoryDeletedEvent,
    CategoryUpdatedEvent,
)
from src.modules.catalog.domain.exceptions import (
    AttributeTemplateNotFoundError,
    CategoryHasChildrenError,
    CategoryHasProductsError,
    CategoryNotFoundError,
    CategorySlugConflictError,
)
from src.shared.exceptions import ValidationError
from tests.factories.attribute_template_builder import AttributeTemplateBuilder
from tests.factories.product_builder import ProductBuilder
from tests.fakes.fake_uow import FakeUnitOfWork


def make_logger():
    """Create a mock logger that supports .bind() chaining."""
    logger = MagicMock()
    logger.bind = MagicMock(return_value=logger)
    return logger


def make_cache():
    """AsyncMock for ICacheService (needed by all 4 Category handlers per Pitfall 2).

    All Category handlers call cache invalidation AFTER uow commit in try/except.
    AsyncMock never raises, so cache calls succeed silently.
    """
    return AsyncMock()


# ============================================================================
# TestCreateCategory
# ============================================================================


class TestCreateCategory:
    """Tests for CreateCategoryHandler."""

    async def test_creates_root_category_and_commits(self):
        uow = FakeUnitOfWork()
        handler = CreateCategoryHandler(
            category_repo=uow.categories,
            template_repo=uow.attribute_templates,
            uow=uow,
            cache=make_cache(),
            logger=make_logger(),
        )

        result = await handler.handle(
            CreateCategoryCommand(
                name_i18n={"en": "Electronics", "ru": "Электроника"},
                slug="electronics",
            )
        )

        assert uow.committed is True
        assert result.id in uow.categories._store
        assert result.level == 0
        assert result.full_slug == "electronics"
        assert result.slug == "electronics"

    async def test_creates_child_category(self):
        uow = FakeUnitOfWork()
        parent = Category.create_root(
            name_i18n={"en": "Electronics", "ru": "Электроника"},
            slug="electronics",
        )
        uow.categories._store[parent.id] = parent

        handler = CreateCategoryHandler(
            category_repo=uow.categories,
            template_repo=uow.attribute_templates,
            uow=uow,
            cache=make_cache(),
            logger=make_logger(),
        )

        result = await handler.handle(
            CreateCategoryCommand(
                name_i18n={"en": "Phones", "ru": "Телефоны"},
                slug="phones",
                parent_id=parent.id,
            )
        )

        assert uow.committed is True
        assert result.level == 1
        assert result.full_slug == "electronics/phones"
        assert result.parent_id == parent.id

    async def test_rejects_slug_conflict(self):
        uow = FakeUnitOfWork()
        existing = Category.create_root(
            name_i18n={"en": "Electronics", "ru": "Электроника"},
            slug="electronics",
        )
        uow.categories._store[existing.id] = existing

        handler = CreateCategoryHandler(
            category_repo=uow.categories,
            template_repo=uow.attribute_templates,
            uow=uow,
            cache=make_cache(),
            logger=make_logger(),
        )

        with pytest.raises(CategorySlugConflictError):
            await handler.handle(
                CreateCategoryCommand(
                    name_i18n={"en": "Other Electronics", "ru": "Другая электроника"},
                    slug="electronics",
                )
            )

        assert uow.committed is False

    async def test_rejects_parent_not_found(self):
        uow = FakeUnitOfWork()
        handler = CreateCategoryHandler(
            category_repo=uow.categories,
            template_repo=uow.attribute_templates,
            uow=uow,
            cache=make_cache(),
            logger=make_logger(),
        )

        with pytest.raises(CategoryNotFoundError):
            await handler.handle(
                CreateCategoryCommand(
                    name_i18n={"en": "Phones", "ru": "Телефоны"},
                    slug="phones",
                    parent_id=uuid.uuid4(),
                )
            )

        assert uow.committed is False

    async def test_rejects_template_not_found(self):
        uow = FakeUnitOfWork()
        handler = CreateCategoryHandler(
            category_repo=uow.categories,
            template_repo=uow.attribute_templates,
            uow=uow,
            cache=make_cache(),
            logger=make_logger(),
        )

        with pytest.raises(AttributeTemplateNotFoundError):
            await handler.handle(
                CreateCategoryCommand(
                    name_i18n={"en": "Electronics", "ru": "Электроника"},
                    slug="electronics",
                    template_id=uuid.uuid4(),
                )
            )

        assert uow.committed is False

    async def test_creates_with_template_id(self):
        uow = FakeUnitOfWork()
        template = AttributeTemplateBuilder().build()
        uow.attribute_templates._store[template.id] = template

        handler = CreateCategoryHandler(
            category_repo=uow.categories,
            template_repo=uow.attribute_templates,
            uow=uow,
            cache=make_cache(),
            logger=make_logger(),
        )

        result = await handler.handle(
            CreateCategoryCommand(
                name_i18n={"en": "Electronics", "ru": "Электроника"},
                slug="electronics",
                template_id=template.id,
            )
        )

        assert uow.committed is True
        assert result.template_id == template.id
        assert result.effective_template_id == template.id

    async def test_emits_category_created_event(self):
        uow = FakeUnitOfWork()
        handler = CreateCategoryHandler(
            category_repo=uow.categories,
            template_repo=uow.attribute_templates,
            uow=uow,
            cache=make_cache(),
            logger=make_logger(),
        )

        result = await handler.handle(
            CreateCategoryCommand(
                name_i18n={"en": "Electronics", "ru": "Электроника"},
                slug="electronics",
            )
        )

        assert len(uow.collected_events) == 1
        event = uow.collected_events[0]
        assert isinstance(event, CategoryCreatedEvent)
        assert event.category_id == result.id
        assert event.slug == "electronics"


# ============================================================================
# TestUpdateCategory
# ============================================================================


class TestUpdateCategory:
    """Tests for UpdateCategoryHandler.

    CRITICAL: Every UpdateCategoryCommand MUST include _provided_fields.
    CRITICAL: template_id defaults to ... (Ellipsis), NOT None.
    """

    async def test_updates_name_and_commits(self):
        uow = FakeUnitOfWork()
        cat = Category.create_root(
            name_i18n={"en": "Electronics", "ru": "Электроника"},
            slug="electronics",
        )
        uow.categories._store[cat.id] = cat

        handler = UpdateCategoryHandler(
            category_repo=uow.categories,
            template_repo=uow.attribute_templates,
            uow=uow,
            cache=make_cache(),
            logger=make_logger(),
        )

        result = await handler.handle(
            UpdateCategoryCommand(
                category_id=cat.id,
                name_i18n={"en": "Consumer Electronics", "ru": "Бытовая электроника"},
                _provided_fields=frozenset({"name_i18n"}),
            )
        )

        assert uow.committed is True
        assert result.name_i18n == {
            "en": "Consumer Electronics",
            "ru": "Бытовая электроника",
        }

    async def test_rejects_not_found(self):
        uow = FakeUnitOfWork()
        handler = UpdateCategoryHandler(
            category_repo=uow.categories,
            template_repo=uow.attribute_templates,
            uow=uow,
            cache=make_cache(),
            logger=make_logger(),
        )

        with pytest.raises(CategoryNotFoundError):
            await handler.handle(
                UpdateCategoryCommand(
                    category_id=uuid.uuid4(),
                    name_i18n={"en": "New Name", "ru": "Новое имя"},
                    _provided_fields=frozenset({"name_i18n"}),
                )
            )

        assert uow.committed is False

    async def test_rejects_slug_conflict(self):
        uow = FakeUnitOfWork()
        cat1 = Category.create_root(
            name_i18n={"en": "Electronics", "ru": "Электроника"},
            slug="electronics",
        )
        cat2 = Category.create_root(
            name_i18n={"en": "Clothing", "ru": "Одежда"},
            slug="clothing",
        )
        uow.categories._store[cat1.id] = cat1
        uow.categories._store[cat2.id] = cat2

        handler = UpdateCategoryHandler(
            category_repo=uow.categories,
            template_repo=uow.attribute_templates,
            uow=uow,
            cache=make_cache(),
            logger=make_logger(),
        )

        with pytest.raises(CategorySlugConflictError):
            await handler.handle(
                UpdateCategoryCommand(
                    category_id=cat2.id,
                    slug="electronics",
                    _provided_fields=frozenset({"slug"}),
                )
            )

        assert uow.committed is False

    async def test_slug_change_cascades_to_descendants(self):
        uow = FakeUnitOfWork()
        root = Category.create_root(
            name_i18n={"en": "Electronics", "ru": "Электроника"},
            slug="electronics",
        )
        child = Category.create_child(
            name_i18n={"en": "Phones", "ru": "Телефоны"},
            slug="phones",
            parent=root,
        )
        uow.categories._store[root.id] = root
        uow.categories._store[child.id] = child

        handler = UpdateCategoryHandler(
            category_repo=uow.categories,
            template_repo=uow.attribute_templates,
            uow=uow,
            cache=make_cache(),
            logger=make_logger(),
        )

        result = await handler.handle(
            UpdateCategoryCommand(
                category_id=root.id,
                slug="tech",
                _provided_fields=frozenset({"slug"}),
            )
        )

        assert uow.committed is True
        assert result.slug == "tech"
        assert result.full_slug == "tech"
        # Verify child's full_slug was cascaded by update_descendants_full_slug
        updated_child = uow.categories._store[child.id]
        assert updated_child.full_slug == "tech/phones"

    async def test_template_id_change_propagates_to_children(self):
        uow = FakeUnitOfWork()
        template = AttributeTemplateBuilder().build()
        uow.attribute_templates._store[template.id] = template

        root = Category.create_root(
            name_i18n={"en": "Electronics", "ru": "Электроника"},
            slug="electronics",
        )
        child = Category.create_child(
            name_i18n={"en": "Phones", "ru": "Телефоны"},
            slug="phones",
            parent=root,
        )
        uow.categories._store[root.id] = root
        uow.categories._store[child.id] = child

        handler = UpdateCategoryHandler(
            category_repo=uow.categories,
            template_repo=uow.attribute_templates,
            uow=uow,
            cache=make_cache(),
            logger=make_logger(),
        )

        # Explicit UUID = set new template (NOT Ellipsis)
        result = await handler.handle(
            UpdateCategoryCommand(
                category_id=root.id,
                template_id=template.id,
                _provided_fields=frozenset({"template_id"}),
            )
        )

        assert uow.committed is True
        assert result.template_id == template.id
        assert result.effective_template_id == template.id
        # Verify child's effective_template_id was propagated
        updated_child = uow.categories._store[child.id]
        assert updated_child.effective_template_id == template.id

    async def test_template_id_ellipsis_means_no_change(self):
        uow = FakeUnitOfWork()
        template = AttributeTemplateBuilder().build()
        uow.attribute_templates._store[template.id] = template

        cat = Category.create_root(
            name_i18n={"en": "Electronics", "ru": "Электроника"},
            slug="electronics",
            template_id=template.id,
        )
        uow.categories._store[cat.id] = cat

        handler = UpdateCategoryHandler(
            category_repo=uow.categories,
            template_repo=uow.attribute_templates,
            uow=uow,
            cache=make_cache(),
            logger=make_logger(),
        )

        # template_id omitted => defaults to ... (Ellipsis) => keep current
        result = await handler.handle(
            UpdateCategoryCommand(
                category_id=cat.id,
                name_i18n={
                    "en": "Updated Electronics",
                    "ru": "Обновленная электроника",
                },
                _provided_fields=frozenset({"name_i18n"}),
            )
        )

        assert uow.committed is True
        # Template should remain unchanged
        assert result.template_id == template.id
        assert result.effective_template_id == template.id

    async def test_template_id_none_clears_template(self):
        uow = FakeUnitOfWork()
        template = AttributeTemplateBuilder().build()
        uow.attribute_templates._store[template.id] = template

        cat = Category.create_root(
            name_i18n={"en": "Electronics", "ru": "Электроника"},
            slug="electronics",
            template_id=template.id,
        )
        uow.categories._store[cat.id] = cat

        handler = UpdateCategoryHandler(
            category_repo=uow.categories,
            template_repo=uow.attribute_templates,
            uow=uow,
            cache=make_cache(),
            logger=make_logger(),
        )

        # Explicit None = clear template
        result = await handler.handle(
            UpdateCategoryCommand(
                category_id=cat.id,
                template_id=None,
                _provided_fields=frozenset({"template_id"}),
            )
        )

        assert uow.committed is True
        assert result.template_id is None
        # Root has no parent, so effective_template_id should also be None
        assert result.effective_template_id is None

    async def test_emits_category_updated_event(self):
        uow = FakeUnitOfWork()
        cat = Category.create_root(
            name_i18n={"en": "Electronics", "ru": "Электроника"},
            slug="electronics",
        )
        uow.categories._store[cat.id] = cat

        handler = UpdateCategoryHandler(
            category_repo=uow.categories,
            template_repo=uow.attribute_templates,
            uow=uow,
            cache=make_cache(),
            logger=make_logger(),
        )

        await handler.handle(
            UpdateCategoryCommand(
                category_id=cat.id,
                name_i18n={"en": "Updated", "ru": "Обновлено"},
                _provided_fields=frozenset({"name_i18n"}),
            )
        )

        assert len(uow.collected_events) == 1
        event = uow.collected_events[0]
        assert isinstance(event, CategoryUpdatedEvent)
        assert event.category_id == cat.id


# ============================================================================
# TestDeleteCategory
# ============================================================================


class TestDeleteCategory:
    """Tests for DeleteCategoryHandler."""

    async def test_deletes_category_and_commits(self):
        uow = FakeUnitOfWork()
        cat = Category.create_root(
            name_i18n={"en": "Electronics", "ru": "Электроника"},
            slug="electronics",
        )
        uow.categories._store[cat.id] = cat

        handler = DeleteCategoryHandler(
            category_repo=uow.categories,
            uow=uow,
            cache=make_cache(),
            logger=make_logger(),
        )

        await handler.handle(DeleteCategoryCommand(category_id=cat.id))

        assert uow.committed is True
        assert cat.id not in uow.categories._store

    async def test_rejects_not_found(self):
        uow = FakeUnitOfWork()
        handler = DeleteCategoryHandler(
            category_repo=uow.categories,
            uow=uow,
            cache=make_cache(),
            logger=make_logger(),
        )

        with pytest.raises(CategoryNotFoundError):
            await handler.handle(DeleteCategoryCommand(category_id=uuid.uuid4()))

        assert uow.committed is False

    async def test_rejects_has_children(self):
        uow = FakeUnitOfWork()
        parent = Category.create_root(
            name_i18n={"en": "Electronics", "ru": "Электроника"},
            slug="electronics",
        )
        child = Category.create_child(
            name_i18n={"en": "Phones", "ru": "Телефоны"},
            slug="phones",
            parent=parent,
        )
        uow.categories._store[parent.id] = parent
        uow.categories._store[child.id] = child

        handler = DeleteCategoryHandler(
            category_repo=uow.categories,
            uow=uow,
            cache=make_cache(),
            logger=make_logger(),
        )

        with pytest.raises(CategoryHasChildrenError):
            await handler.handle(DeleteCategoryCommand(category_id=parent.id))

        assert uow.committed is False

    async def test_rejects_has_products(self):
        uow = FakeUnitOfWork()
        cat = Category.create_root(
            name_i18n={"en": "Electronics", "ru": "Электроника"},
            slug="electronics",
        )
        uow.categories._store[cat.id] = cat

        # Pre-seed a product referencing this category
        product = ProductBuilder().with_category_id(cat.id).build()
        uow.products._store[product.id] = product

        handler = DeleteCategoryHandler(
            category_repo=uow.categories,
            uow=uow,
            cache=make_cache(),
            logger=make_logger(),
        )

        with pytest.raises(CategoryHasProductsError):
            await handler.handle(DeleteCategoryCommand(category_id=cat.id))

        assert uow.committed is False

    async def test_emits_category_deleted_event(self):
        uow = FakeUnitOfWork()
        cat = Category.create_root(
            name_i18n={"en": "Electronics", "ru": "Электроника"},
            slug="electronics",
        )
        uow.categories._store[cat.id] = cat

        handler = DeleteCategoryHandler(
            category_repo=uow.categories,
            uow=uow,
            cache=make_cache(),
            logger=make_logger(),
        )

        await handler.handle(DeleteCategoryCommand(category_id=cat.id))

        assert len(uow.collected_events) == 1
        event = uow.collected_events[0]
        assert isinstance(event, CategoryDeletedEvent)
        assert event.category_id == cat.id
        assert event.slug == "electronics"


# ============================================================================
# TestBulkCreateCategories
# ============================================================================


class TestBulkCreateCategories:
    """Tests for BulkCreateCategoriesHandler.

    CRITICAL: intra-batch parent_ref resolution.
    """

    async def test_creates_flat_list(self):
        uow = FakeUnitOfWork()
        handler = BulkCreateCategoriesHandler(
            category_repo=uow.categories,
            template_repo=uow.attribute_templates,
            uow=uow,
            cache=make_cache(),
            logger=make_logger(),
        )

        result = await handler.handle(
            BulkCreateCategoriesCommand(
                items=[
                    BulkCategoryItem(
                        name_i18n={"en": "Electronics", "ru": "Электроника"},
                        slug="electronics",
                    ),
                    BulkCategoryItem(
                        name_i18n={"en": "Clothing", "ru": "Одежда"},
                        slug="clothing",
                    ),
                    BulkCategoryItem(
                        name_i18n={"en": "Sports", "ru": "Спорт"},
                        slug="sports",
                    ),
                ]
            )
        )

        assert uow.committed is True
        assert result.created_count == 3
        assert result.skipped_count == 0
        assert len(result.created) == 3

    async def test_creates_tree_with_parent_ref(self):
        uow = FakeUnitOfWork()
        handler = BulkCreateCategoriesHandler(
            category_repo=uow.categories,
            template_repo=uow.attribute_templates,
            uow=uow,
            cache=make_cache(),
            logger=make_logger(),
        )

        result = await handler.handle(
            BulkCreateCategoriesCommand(
                items=[
                    BulkCategoryItem(
                        name_i18n={"en": "Electronics", "ru": "Электроника"},
                        slug="electronics",
                        ref="electronics",
                    ),
                    BulkCategoryItem(
                        name_i18n={"en": "Phones", "ru": "Телефоны"},
                        slug="phones",
                        parent_ref="electronics",
                    ),
                ]
            )
        )

        assert uow.committed is True
        assert result.created_count == 2

        # The parent (electronics) is level 0
        parent_item = result.created[0]
        assert parent_item.level == 0
        assert parent_item.full_slug == "electronics"

        # The child (phones) is level 1 with parent's full_slug prefix
        child_item = result.created[1]
        assert child_item.level == 1
        assert child_item.full_slug == "electronics/phones"

        # Verify child's parent_id points to parent
        child_cat = uow.categories._store[child_item.id]
        parent_cat = uow.categories._store[parent_item.id]
        assert child_cat.parent_id == parent_cat.id

    async def test_skip_existing_mode(self):
        uow = FakeUnitOfWork()
        # Pre-seed a root category
        existing = Category.create_root(
            name_i18n={"en": "Electronics", "ru": "Электроника"},
            slug="electronics",
        )
        uow.categories._store[existing.id] = existing

        handler = BulkCreateCategoriesHandler(
            category_repo=uow.categories,
            template_repo=uow.attribute_templates,
            uow=uow,
            cache=make_cache(),
            logger=make_logger(),
        )

        result = await handler.handle(
            BulkCreateCategoriesCommand(
                items=[
                    BulkCategoryItem(
                        name_i18n={"en": "Electronics", "ru": "Электроника"},
                        slug="electronics",
                    ),
                    BulkCategoryItem(
                        name_i18n={"en": "Clothing", "ru": "Одежда"},
                        slug="clothing",
                    ),
                ],
                skip_existing=True,
            )
        )

        assert uow.committed is True
        assert result.created_count == 1
        assert result.skipped_count == 1
        assert "electronics" in result.skipped_slugs

    async def test_strict_mode_rejects_slug_conflict(self):
        uow = FakeUnitOfWork()
        existing = Category.create_root(
            name_i18n={"en": "Electronics", "ru": "Электроника"},
            slug="electronics",
        )
        uow.categories._store[existing.id] = existing

        handler = BulkCreateCategoriesHandler(
            category_repo=uow.categories,
            template_repo=uow.attribute_templates,
            uow=uow,
            cache=make_cache(),
            logger=make_logger(),
        )

        with pytest.raises(CategorySlugConflictError):
            await handler.handle(
                BulkCreateCategoriesCommand(
                    items=[
                        BulkCategoryItem(
                            name_i18n={"en": "Electronics", "ru": "Электроника"},
                            slug="electronics",
                        ),
                    ],
                    skip_existing=False,
                )
            )

        assert uow.committed is False

    async def test_rejects_batch_limit(self):
        uow = FakeUnitOfWork()
        handler = BulkCreateCategoriesHandler(
            category_repo=uow.categories,
            template_repo=uow.attribute_templates,
            uow=uow,
            cache=make_cache(),
            logger=make_logger(),
        )

        items = [
            BulkCategoryItem(
                name_i18n={"en": f"Cat {i}", "ru": f"Кат {i}"},
                slug=f"cat-{i}",
            )
            for i in range(MAX_BULK_CATEGORIES + 1)
        ]

        with pytest.raises(ValidationError) as exc_info:
            await handler.handle(BulkCreateCategoriesCommand(items=items))
        assert exc_info.value.error_code == "BULK_LIMIT_EXCEEDED"

    async def test_rejects_duplicate_refs(self):
        uow = FakeUnitOfWork()
        handler = BulkCreateCategoriesHandler(
            category_repo=uow.categories,
            template_repo=uow.attribute_templates,
            uow=uow,
            cache=make_cache(),
            logger=make_logger(),
        )

        with pytest.raises(ValidationError) as exc_info:
            await handler.handle(
                BulkCreateCategoriesCommand(
                    items=[
                        BulkCategoryItem(
                            name_i18n={"en": "Cat A", "ru": "Кат А"},
                            slug="cat-a",
                            ref="dup",
                        ),
                        BulkCategoryItem(
                            name_i18n={"en": "Cat B", "ru": "Кат Б"},
                            slug="cat-b",
                            ref="dup",
                        ),
                    ]
                )
            )
        assert exc_info.value.error_code == "BULK_DUPLICATE_REFS"

    async def test_rejects_parent_ref_not_found(self):
        uow = FakeUnitOfWork()
        handler = BulkCreateCategoriesHandler(
            category_repo=uow.categories,
            template_repo=uow.attribute_templates,
            uow=uow,
            cache=make_cache(),
            logger=make_logger(),
        )

        with pytest.raises(ValidationError) as exc_info:
            await handler.handle(
                BulkCreateCategoriesCommand(
                    items=[
                        BulkCategoryItem(
                            name_i18n={"en": "Child", "ru": "Ребенок"},
                            slug="child",
                            parent_ref="nonexistent",
                        ),
                    ]
                )
            )
        assert exc_info.value.error_code == "BULK_PARENT_REF_NOT_FOUND"

    async def test_validates_template_id(self):
        uow = FakeUnitOfWork()
        handler = BulkCreateCategoriesHandler(
            category_repo=uow.categories,
            template_repo=uow.attribute_templates,
            uow=uow,
            cache=make_cache(),
            logger=make_logger(),
        )

        with pytest.raises(AttributeTemplateNotFoundError):
            await handler.handle(
                BulkCreateCategoriesCommand(
                    items=[
                        BulkCategoryItem(
                            name_i18n={"en": "Electronics", "ru": "Электроника"},
                            slug="electronics",
                            template_id=uuid.uuid4(),
                        ),
                    ]
                )
            )
