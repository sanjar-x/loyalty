"""Unit tests for Attribute/Template/Binding command handlers (CMD-03).

Tests all 12 command handlers:
- CreateAttributeTemplateHandler
- UpdateAttributeTemplateHandler
- DeleteAttributeTemplateHandler
- CloneAttributeTemplateHandler
- CreateAttributeHandler
- UpdateAttributeHandler
- DeleteAttributeHandler
- BulkCreateAttributesHandler
- BindAttributeToTemplateHandler
- UnbindAttributeFromTemplateHandler
- UpdateTemplateAttributeBindingHandler
- ReorderTemplateBindingsHandler

Per D-01: one test class per handler.
Per D-02: one test file per entity domain.
Per D-03: uses FakeUnitOfWork for all repository interactions.
Per D-04: AsyncMock only for ICacheService (8 handlers need it).
Per D-07: asserts uow.committed on happy path, uow.committed is False on rejection.
Per D-08: asserts events via uow.collected_events (not entity.domain_events).
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.modules.catalog.application.commands.bind_attribute_to_template import (
    BindAttributeToTemplateCommand,
    BindAttributeToTemplateHandler,
)
from src.modules.catalog.application.commands.bulk_create_attributes import (
    BulkAttributeItem,
    BulkCreateAttributesCommand,
    BulkCreateAttributesHandler,
)
from src.modules.catalog.application.commands.clone_attribute_template import (
    CloneAttributeTemplateCommand,
    CloneAttributeTemplateHandler,
)
from src.modules.catalog.application.commands.create_attribute import (
    CreateAttributeCommand,
    CreateAttributeHandler,
)
from src.modules.catalog.application.commands.create_attribute_template import (
    CreateAttributeTemplateCommand,
    CreateAttributeTemplateHandler,
)
from src.modules.catalog.application.commands.delete_attribute import (
    DeleteAttributeCommand,
    DeleteAttributeHandler,
)
from src.modules.catalog.application.commands.delete_attribute_template import (
    DeleteAttributeTemplateCommand,
    DeleteAttributeTemplateHandler,
)
from src.modules.catalog.application.commands.reorder_template_bindings import (
    BindingReorderItem,
    ReorderTemplateBindingsCommand,
    ReorderTemplateBindingsHandler,
)
from src.modules.catalog.application.commands.unbind_attribute_from_template import (
    UnbindAttributeFromTemplateCommand,
    UnbindAttributeFromTemplateHandler,
)
from src.modules.catalog.application.commands.update_attribute import (
    UpdateAttributeCommand,
    UpdateAttributeHandler,
)
from src.modules.catalog.application.commands.update_attribute_template import (
    UpdateAttributeTemplateCommand,
    UpdateAttributeTemplateHandler,
)
from src.modules.catalog.application.commands.update_template_attribute_binding import (
    UpdateTemplateAttributeBindingCommand,
    UpdateTemplateAttributeBindingHandler,
)
from src.modules.catalog.domain.events import (
    AttributeCreatedEvent,
    AttributeDeletedEvent,
    AttributeTemplateCreatedEvent,
    AttributeTemplateDeletedEvent,
    AttributeTemplateUpdatedEvent,
    AttributeUpdatedEvent,
    TemplateAttributeBindingCreatedEvent,
    TemplateAttributeBindingDeletedEvent,
    TemplateAttributeBindingUpdatedEvent,
)
from src.modules.catalog.domain.exceptions import (
    AttributeCodeConflictError,
    AttributeGroupNotFoundError,
    AttributeHasTemplateBindingsError,
    AttributeInUseByProductsError,
    AttributeNotFoundError,
    AttributeSlugConflictError,
    AttributeTemplateCodeAlreadyExistsError,
    AttributeTemplateHasCategoryReferencesError,
    AttributeTemplateNotFoundError,
    TemplateAttributeBindingAlreadyExistsError,
    TemplateAttributeBindingNotFoundError,
)
from src.modules.catalog.domain.value_objects import (
    AttributeDataType,
    AttributeUIType,
    RequirementLevel,
)
from src.shared.exceptions import ValidationError
from tests.factories.attribute_builder import AttributeBuilder
from tests.factories.attribute_group_builder import AttributeGroupBuilder
from tests.factories.attribute_template_builder import (
    AttributeTemplateBuilder,
    TemplateAttributeBindingBuilder,
)
from tests.fakes.fake_uow import FakeUnitOfWork

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def make_logger():
    """Create a mock logger that supports .bind() chaining."""
    logger = MagicMock()
    logger.bind = MagicMock(return_value=logger)
    return logger


def make_cache():
    """AsyncMock for ICacheService. Needed by 8 handlers."""
    return AsyncMock()


I18N = {"en": "Test", "ru": "Тест"}
"""Shortcut for valid bilingual i18n dict (required locales: en, ru)."""


# ============================================================================
# TestCreateAttributeTemplate
# ============================================================================


class TestCreateAttributeTemplate:
    """Tests for CreateAttributeTemplateHandler."""

    async def test_creates_template_and_commits(self):
        uow = FakeUnitOfWork()
        handler = CreateAttributeTemplateHandler(
            template_repo=uow.attribute_templates,
            uow=uow,
            logger=make_logger(),
        )
        cmd = CreateAttributeTemplateCommand(
            code="clothing",
            name_i18n={"en": "Clothing", "ru": "Одежда"},
        )

        result = await handler.handle(cmd)

        assert result.id in uow.attribute_templates._store
        assert uow.committed is True

    async def test_rejects_code_conflict(self):
        uow = FakeUnitOfWork()
        existing = AttributeTemplateBuilder().with_code("clothing").build()
        await uow.attribute_templates.add(existing)

        handler = CreateAttributeTemplateHandler(
            template_repo=uow.attribute_templates,
            uow=uow,
            logger=make_logger(),
        )
        cmd = CreateAttributeTemplateCommand(
            code="clothing",
            name_i18n={"en": "Clothing", "ru": "Одежда"},
        )

        with pytest.raises(AttributeTemplateCodeAlreadyExistsError):
            await handler.handle(cmd)
        assert uow.committed is False

    async def test_emits_template_created_event(self):
        uow = FakeUnitOfWork()
        handler = CreateAttributeTemplateHandler(
            template_repo=uow.attribute_templates,
            uow=uow,
            logger=make_logger(),
        )
        cmd = CreateAttributeTemplateCommand(
            code="electronics",
            name_i18n={"en": "Electronics", "ru": "Электроника"},
        )

        result = await handler.handle(cmd)

        events = [
            e
            for e in uow.collected_events
            if isinstance(e, AttributeTemplateCreatedEvent)
        ]
        assert len(events) == 1
        assert events[0].template_id == result.id


# ============================================================================
# TestUpdateAttributeTemplate
# ============================================================================


class TestUpdateAttributeTemplate:
    """Tests for UpdateAttributeTemplateHandler (CRITICAL: _provided_fields)."""

    async def test_updates_template_and_commits(self):
        uow = FakeUnitOfWork()
        template = AttributeTemplateBuilder().with_code("shoes").build()
        await uow.attribute_templates.add(template)

        handler = UpdateAttributeTemplateHandler(
            template_repo=uow.attribute_templates,
            uow=uow,
            logger=make_logger(),
        )
        cmd = UpdateAttributeTemplateCommand(
            template_id=template.id,
            name_i18n={"en": "Updated Shoes", "ru": "Обувь обновленная"},
            _provided_fields=frozenset({"name_i18n"}),
        )

        result = await handler.handle(cmd)

        assert result.name_i18n == {"en": "Updated Shoes", "ru": "Обувь обновленная"}
        assert uow.committed is True

    async def test_rejects_not_found(self):
        uow = FakeUnitOfWork()
        handler = UpdateAttributeTemplateHandler(
            template_repo=uow.attribute_templates,
            uow=uow,
            logger=make_logger(),
        )
        cmd = UpdateAttributeTemplateCommand(
            template_id=uuid.uuid4(),
            name_i18n={"en": "X", "ru": "Х"},
            _provided_fields=frozenset({"name_i18n"}),
        )

        with pytest.raises(AttributeTemplateNotFoundError):
            await handler.handle(cmd)
        assert uow.committed is False

    async def test_emits_template_updated_event(self):
        uow = FakeUnitOfWork()
        template = AttributeTemplateBuilder().with_code("hats").build()
        await uow.attribute_templates.add(template)

        handler = UpdateAttributeTemplateHandler(
            template_repo=uow.attribute_templates,
            uow=uow,
            logger=make_logger(),
        )
        cmd = UpdateAttributeTemplateCommand(
            template_id=template.id,
            sort_order=5,
            _provided_fields=frozenset({"sort_order"}),
        )

        await handler.handle(cmd)

        events = [
            e
            for e in uow.collected_events
            if isinstance(e, AttributeTemplateUpdatedEvent)
        ]
        assert len(events) == 1
        assert events[0].template_id == template.id


# ============================================================================
# TestDeleteAttributeTemplate
# ============================================================================


class TestDeleteAttributeTemplate:
    """Tests for DeleteAttributeTemplateHandler."""

    async def test_deletes_template_and_commits(self):
        uow = FakeUnitOfWork()
        template = AttributeTemplateBuilder().with_code("obsolete").build()
        await uow.attribute_templates.add(template)

        handler = DeleteAttributeTemplateHandler(
            template_repo=uow.attribute_templates,
            uow=uow,
            logger=make_logger(),
        )
        cmd = DeleteAttributeTemplateCommand(template_id=template.id)

        await handler.handle(cmd)

        assert template.id not in uow.attribute_templates._store
        assert uow.committed is True

    async def test_rejects_not_found(self):
        uow = FakeUnitOfWork()
        handler = DeleteAttributeTemplateHandler(
            template_repo=uow.attribute_templates,
            uow=uow,
            logger=make_logger(),
        )
        cmd = DeleteAttributeTemplateCommand(template_id=uuid.uuid4())

        with pytest.raises(AttributeTemplateNotFoundError):
            await handler.handle(cmd)
        assert uow.committed is False

    async def test_rejects_has_category_references(self):
        uow = FakeUnitOfWork()
        template = AttributeTemplateBuilder().with_code("referenced").build()
        await uow.attribute_templates.add(template)

        # Pre-seed a category referencing this template via _category_store
        from src.modules.catalog.domain.entities import Category

        cat = Category.create_root(
            name_i18n={"en": "Cat", "ru": "Кат"},
            slug="cat",
            sort_order=0,
            template_id=template.id,
        )
        uow.categories._store[cat.id] = cat

        handler = DeleteAttributeTemplateHandler(
            template_repo=uow.attribute_templates,
            uow=uow,
            logger=make_logger(),
        )
        cmd = DeleteAttributeTemplateCommand(template_id=template.id)

        with pytest.raises(AttributeTemplateHasCategoryReferencesError):
            await handler.handle(cmd)
        assert uow.committed is False

    async def test_emits_template_deleted_event(self):
        uow = FakeUnitOfWork()
        template = AttributeTemplateBuilder().with_code("to-delete").build()
        await uow.attribute_templates.add(template)

        handler = DeleteAttributeTemplateHandler(
            template_repo=uow.attribute_templates,
            uow=uow,
            logger=make_logger(),
        )
        cmd = DeleteAttributeTemplateCommand(template_id=template.id)

        await handler.handle(cmd)

        events = [
            e
            for e in uow.collected_events
            if isinstance(e, AttributeTemplateDeletedEvent)
        ]
        assert len(events) == 1
        assert events[0].template_id == template.id


# ============================================================================
# TestCloneAttributeTemplate
# ============================================================================


class TestCloneAttributeTemplate:
    """Tests for CloneAttributeTemplateHandler."""

    async def test_clones_template_with_bindings(self):
        uow = FakeUnitOfWork()
        source = AttributeTemplateBuilder().with_code("source").build()
        await uow.attribute_templates.add(source)

        # Pre-seed 2 bindings for the source template
        b1 = (
            TemplateAttributeBindingBuilder()
            .with_template_id(source.id)
            .with_attribute_id(uuid.uuid4())
            .with_sort_order(0)
            .build()
        )
        b2 = (
            TemplateAttributeBindingBuilder()
            .with_template_id(source.id)
            .with_attribute_id(uuid.uuid4())
            .with_sort_order(1)
            .build()
        )
        await uow.template_bindings.add(b1)
        await uow.template_bindings.add(b2)

        handler = CloneAttributeTemplateHandler(
            template_repo=uow.attribute_templates,
            binding_repo=uow.template_bindings,
            uow=uow,
            logger=make_logger(),
        )
        cmd = CloneAttributeTemplateCommand(
            source_template_id=source.id,
            new_code="cloned",
            new_name_i18n={"en": "Cloned", "ru": "Клон"},
        )

        result = await handler.handle(cmd)

        assert result.bindings_copied == 2
        assert result.id in uow.attribute_templates._store
        # 2 old + 2 new bindings = 4 total
        assert len(uow.template_bindings._store) == 4
        assert uow.committed is True

    async def test_rejects_source_not_found(self):
        uow = FakeUnitOfWork()
        handler = CloneAttributeTemplateHandler(
            template_repo=uow.attribute_templates,
            binding_repo=uow.template_bindings,
            uow=uow,
            logger=make_logger(),
        )
        cmd = CloneAttributeTemplateCommand(
            source_template_id=uuid.uuid4(),
            new_code="clone",
            new_name_i18n={"en": "Clone", "ru": "Клон"},
        )

        with pytest.raises(AttributeTemplateNotFoundError):
            await handler.handle(cmd)
        assert uow.committed is False

    async def test_rejects_code_conflict(self):
        uow = FakeUnitOfWork()
        source = AttributeTemplateBuilder().with_code("src").build()
        existing = AttributeTemplateBuilder().with_code("taken").build()
        await uow.attribute_templates.add(source)
        await uow.attribute_templates.add(existing)

        handler = CloneAttributeTemplateHandler(
            template_repo=uow.attribute_templates,
            binding_repo=uow.template_bindings,
            uow=uow,
            logger=make_logger(),
        )
        cmd = CloneAttributeTemplateCommand(
            source_template_id=source.id,
            new_code="taken",
            new_name_i18n={"en": "Taken", "ru": "Занят"},
        )

        with pytest.raises(AttributeTemplateCodeAlreadyExistsError):
            await handler.handle(cmd)
        assert uow.committed is False

    async def test_emits_template_created_event(self):
        uow = FakeUnitOfWork()
        source = AttributeTemplateBuilder().with_code("src-evt").build()
        await uow.attribute_templates.add(source)

        handler = CloneAttributeTemplateHandler(
            template_repo=uow.attribute_templates,
            binding_repo=uow.template_bindings,
            uow=uow,
            logger=make_logger(),
        )
        cmd = CloneAttributeTemplateCommand(
            source_template_id=source.id,
            new_code="clone-evt",
            new_name_i18n={"en": "Clone", "ru": "Клон"},
        )

        result = await handler.handle(cmd)

        events = [
            e
            for e in uow.collected_events
            if isinstance(e, AttributeTemplateCreatedEvent)
        ]
        assert len(events) == 1
        assert events[0].template_id == result.id


# ============================================================================
# TestCreateAttribute
# ============================================================================


class TestCreateAttribute:
    """Tests for CreateAttributeHandler."""

    async def test_creates_attribute_and_commits(self):
        uow = FakeUnitOfWork()
        handler = CreateAttributeHandler(
            attribute_repo=uow.attributes,
            group_repo=uow.attribute_groups,
            uow=uow,
            logger=make_logger(),
        )
        cmd = CreateAttributeCommand(
            code="color",
            slug="color",
            name_i18n={"en": "Color", "ru": "Цвет"},
            data_type=AttributeDataType.STRING,
            ui_type=AttributeUIType.DROPDOWN,
            is_dictionary=True,
        )

        result = await handler.handle(cmd)

        assert result.attribute_id in uow.attributes._store
        assert uow.committed is True

    async def test_rejects_code_conflict(self):
        uow = FakeUnitOfWork()
        existing = AttributeBuilder().with_code("color").build()
        await uow.attributes.add(existing)

        handler = CreateAttributeHandler(
            attribute_repo=uow.attributes,
            group_repo=uow.attribute_groups,
            uow=uow,
            logger=make_logger(),
        )
        cmd = CreateAttributeCommand(
            code="color",
            slug="new-color",
            name_i18n={"en": "Color", "ru": "Цвет"},
            data_type=AttributeDataType.STRING,
            ui_type=AttributeUIType.DROPDOWN,
            is_dictionary=True,
        )

        with pytest.raises(AttributeCodeConflictError):
            await handler.handle(cmd)
        assert uow.committed is False

    async def test_rejects_slug_conflict(self):
        uow = FakeUnitOfWork()
        existing = AttributeBuilder().with_slug("color").build()
        await uow.attributes.add(existing)

        handler = CreateAttributeHandler(
            attribute_repo=uow.attributes,
            group_repo=uow.attribute_groups,
            uow=uow,
            logger=make_logger(),
        )
        cmd = CreateAttributeCommand(
            code="new-color",
            slug="color",
            name_i18n={"en": "Color", "ru": "Цвет"},
            data_type=AttributeDataType.STRING,
            ui_type=AttributeUIType.DROPDOWN,
            is_dictionary=True,
        )

        with pytest.raises(AttributeSlugConflictError):
            await handler.handle(cmd)
        assert uow.committed is False

    async def test_rejects_group_not_found(self):
        uow = FakeUnitOfWork()
        handler = CreateAttributeHandler(
            attribute_repo=uow.attributes,
            group_repo=uow.attribute_groups,
            uow=uow,
            logger=make_logger(),
        )
        cmd = CreateAttributeCommand(
            code="material",
            slug="material",
            name_i18n={"en": "Material", "ru": "Материал"},
            data_type=AttributeDataType.STRING,
            ui_type=AttributeUIType.DROPDOWN,
            is_dictionary=True,
            group_id=uuid.uuid4(),
        )

        with pytest.raises(AttributeGroupNotFoundError):
            await handler.handle(cmd)
        assert uow.committed is False

    async def test_creates_with_group(self):
        uow = FakeUnitOfWork()
        group = AttributeGroupBuilder().with_code("physical").build()
        await uow.attribute_groups.add(group)

        handler = CreateAttributeHandler(
            attribute_repo=uow.attributes,
            group_repo=uow.attribute_groups,
            uow=uow,
            logger=make_logger(),
        )
        cmd = CreateAttributeCommand(
            code="weight",
            slug="weight",
            name_i18n={"en": "Weight", "ru": "Вес"},
            data_type=AttributeDataType.INTEGER,
            ui_type=AttributeUIType.DROPDOWN,
            is_dictionary=False,
            group_id=group.id,
        )

        result = await handler.handle(cmd)

        created = uow.attributes._store[result.attribute_id]
        assert created.group_id == group.id
        assert uow.committed is True

    async def test_emits_attribute_created_event(self):
        uow = FakeUnitOfWork()
        handler = CreateAttributeHandler(
            attribute_repo=uow.attributes,
            group_repo=uow.attribute_groups,
            uow=uow,
            logger=make_logger(),
        )
        cmd = CreateAttributeCommand(
            code="size",
            slug="size",
            name_i18n={"en": "Size", "ru": "Размер"},
            data_type=AttributeDataType.STRING,
            ui_type=AttributeUIType.TEXT_BUTTON,
            is_dictionary=True,
        )

        result = await handler.handle(cmd)

        events = [
            e for e in uow.collected_events if isinstance(e, AttributeCreatedEvent)
        ]
        assert len(events) == 1
        assert events[0].attribute_id == result.attribute_id


# ============================================================================
# TestUpdateAttribute
# ============================================================================


class TestUpdateAttribute:
    """Tests for UpdateAttributeHandler (CRITICAL: _provided_fields + ICacheService)."""

    async def test_updates_attribute_and_commits(self):
        uow = FakeUnitOfWork()
        attr = AttributeBuilder().with_code("color").with_slug("color").build()
        await uow.attributes.add(attr)

        handler = UpdateAttributeHandler(
            attribute_repo=uow.attributes,
            group_repo=uow.attribute_groups,
            binding_repo=uow.template_bindings,
            template_repo=uow.attribute_templates,
            cache=make_cache(),
            uow=uow,
            logger=make_logger(),
        )
        cmd = UpdateAttributeCommand(
            attribute_id=attr.id,
            name_i18n={"en": "Updated Color", "ru": "Обновленный цвет"},
            _provided_fields=frozenset({"name_i18n"}),
        )

        result = await handler.handle(cmd)

        updated = uow.attributes._store[attr.id]
        assert updated.name_i18n == {"en": "Updated Color", "ru": "Обновленный цвет"}
        assert result.id == attr.id
        assert uow.committed is True

    async def test_rejects_not_found(self):
        uow = FakeUnitOfWork()
        handler = UpdateAttributeHandler(
            attribute_repo=uow.attributes,
            group_repo=uow.attribute_groups,
            binding_repo=uow.template_bindings,
            template_repo=uow.attribute_templates,
            cache=make_cache(),
            uow=uow,
            logger=make_logger(),
        )
        cmd = UpdateAttributeCommand(
            attribute_id=uuid.uuid4(),
            name_i18n=I18N,
            _provided_fields=frozenset({"name_i18n"}),
        )

        with pytest.raises(AttributeNotFoundError):
            await handler.handle(cmd)
        assert uow.committed is False

    async def test_rejects_group_not_found(self):
        uow = FakeUnitOfWork()
        attr = AttributeBuilder().with_code("mat").with_slug("mat").build()
        await uow.attributes.add(attr)

        handler = UpdateAttributeHandler(
            attribute_repo=uow.attributes,
            group_repo=uow.attribute_groups,
            binding_repo=uow.template_bindings,
            template_repo=uow.attribute_templates,
            cache=make_cache(),
            uow=uow,
            logger=make_logger(),
        )
        cmd = UpdateAttributeCommand(
            attribute_id=attr.id,
            group_id=uuid.uuid4(),
            _provided_fields=frozenset({"group_id"}),
        )

        with pytest.raises(AttributeGroupNotFoundError):
            await handler.handle(cmd)
        assert uow.committed is False

    async def test_emits_attribute_updated_event(self):
        uow = FakeUnitOfWork()
        attr = AttributeBuilder().with_code("ev").with_slug("ev").build()
        await uow.attributes.add(attr)

        handler = UpdateAttributeHandler(
            attribute_repo=uow.attributes,
            group_repo=uow.attribute_groups,
            binding_repo=uow.template_bindings,
            template_repo=uow.attribute_templates,
            cache=make_cache(),
            uow=uow,
            logger=make_logger(),
        )
        cmd = UpdateAttributeCommand(
            attribute_id=attr.id,
            description_i18n={"en": "Desc", "ru": "Описание"},
            _provided_fields=frozenset({"description_i18n"}),
        )

        await handler.handle(cmd)

        events = [
            e for e in uow.collected_events if isinstance(e, AttributeUpdatedEvent)
        ]
        assert len(events) == 1
        assert events[0].attribute_id == attr.id


# ============================================================================
# TestDeleteAttribute
# ============================================================================


class TestDeleteAttribute:
    """Tests for DeleteAttributeHandler (ICacheService mock needed)."""

    async def test_deletes_attribute_and_commits(self):
        uow = FakeUnitOfWork()
        attr = AttributeBuilder().with_code("old").with_slug("old").build()
        await uow.attributes.add(attr)

        handler = DeleteAttributeHandler(
            attribute_repo=uow.attributes,
            template_binding_repo=uow.template_bindings,
            template_repo=uow.attribute_templates,
            cache=make_cache(),
            uow=uow,
            logger=make_logger(),
        )
        cmd = DeleteAttributeCommand(attribute_id=attr.id)

        await handler.handle(cmd)

        assert attr.id not in uow.attributes._store
        assert uow.committed is True

    async def test_rejects_not_found(self):
        uow = FakeUnitOfWork()
        handler = DeleteAttributeHandler(
            attribute_repo=uow.attributes,
            template_binding_repo=uow.template_bindings,
            template_repo=uow.attribute_templates,
            cache=make_cache(),
            uow=uow,
            logger=make_logger(),
        )
        cmd = DeleteAttributeCommand(attribute_id=uuid.uuid4())

        with pytest.raises(AttributeNotFoundError):
            await handler.handle(cmd)
        assert uow.committed is False

    async def test_rejects_has_template_bindings(self):
        uow = FakeUnitOfWork()
        attr = AttributeBuilder().with_code("bound").with_slug("bound").build()
        await uow.attributes.add(attr)

        # Pre-seed a binding referencing this attribute
        binding = (
            TemplateAttributeBindingBuilder()
            .with_template_id(uuid.uuid4())
            .with_attribute_id(attr.id)
            .build()
        )
        await uow.template_bindings.add(binding)

        handler = DeleteAttributeHandler(
            attribute_repo=uow.attributes,
            template_binding_repo=uow.template_bindings,
            template_repo=uow.attribute_templates,
            cache=make_cache(),
            uow=uow,
            logger=make_logger(),
        )
        cmd = DeleteAttributeCommand(attribute_id=attr.id)

        with pytest.raises(AttributeHasTemplateBindingsError):
            await handler.handle(cmd)
        assert uow.committed is False

    async def test_rejects_in_use_by_products(self):
        uow = FakeUnitOfWork()
        attr = AttributeBuilder().with_code("used").with_slug("used").build()
        await uow.attributes.add(attr)

        # Monkeypatch has_product_attribute_values to return True
        uow.attributes.has_product_attribute_values = AsyncMock(return_value=True)  # ty:ignore[invalid-assignment]

        handler = DeleteAttributeHandler(
            attribute_repo=uow.attributes,
            template_binding_repo=uow.template_bindings,
            template_repo=uow.attribute_templates,
            cache=make_cache(),
            uow=uow,
            logger=make_logger(),
        )
        cmd = DeleteAttributeCommand(attribute_id=attr.id)

        with pytest.raises(AttributeInUseByProductsError):
            await handler.handle(cmd)
        assert uow.committed is False

    async def test_emits_attribute_deleted_event(self):
        uow = FakeUnitOfWork()
        attr = AttributeBuilder().with_code("del-evt").with_slug("del-evt").build()
        await uow.attributes.add(attr)

        handler = DeleteAttributeHandler(
            attribute_repo=uow.attributes,
            template_binding_repo=uow.template_bindings,
            template_repo=uow.attribute_templates,
            cache=make_cache(),
            uow=uow,
            logger=make_logger(),
        )
        cmd = DeleteAttributeCommand(attribute_id=attr.id)

        await handler.handle(cmd)

        events = [
            e for e in uow.collected_events if isinstance(e, AttributeDeletedEvent)
        ]
        assert len(events) == 1
        assert events[0].attribute_id == attr.id


# ============================================================================
# TestBulkCreateAttributes
# ============================================================================


def _make_bulk_item(
    code: str,
    slug: str,
    group_id: uuid.UUID | None = None,
) -> BulkAttributeItem:
    """Helper to create a BulkAttributeItem with required fields."""
    return BulkAttributeItem(
        code=code,
        slug=slug,
        name_i18n={"en": f"Attr {code}", "ru": f"Атрибут {code}"},
        data_type=AttributeDataType.STRING,
        ui_type=AttributeUIType.DROPDOWN,
        is_dictionary=True,
        group_id=group_id,
    )


class TestBulkCreateAttributes:
    """Tests for BulkCreateAttributesHandler."""

    async def test_creates_multiple_attributes(self):
        uow = FakeUnitOfWork()
        handler = BulkCreateAttributesHandler(
            attribute_repo=uow.attributes,
            group_repo=uow.attribute_groups,
            uow=uow,
            logger=make_logger(),
        )
        cmd = BulkCreateAttributesCommand(
            items=[
                _make_bulk_item("a1", "a1"),
                _make_bulk_item("a2", "a2"),
                _make_bulk_item("a3", "a3"),
            ],
        )

        result = await handler.handle(cmd)

        assert result.created_count == 3
        assert len(result.ids) == 3
        for aid in result.ids:
            assert aid in uow.attributes._store
        assert uow.committed is True

    async def test_skip_existing_mode(self):
        uow = FakeUnitOfWork()
        existing = (
            AttributeBuilder().with_code("existing").with_slug("existing").build()
        )
        await uow.attributes.add(existing)

        handler = BulkCreateAttributesHandler(
            attribute_repo=uow.attributes,
            group_repo=uow.attribute_groups,
            uow=uow,
            logger=make_logger(),
        )
        cmd = BulkCreateAttributesCommand(
            items=[
                _make_bulk_item("existing", "existing"),
                _make_bulk_item("new-one", "new-one"),
            ],
            skip_existing=True,
        )

        result = await handler.handle(cmd)

        assert result.skipped_count == 1
        assert "existing" in result.skipped_codes
        assert result.created_count == 1
        assert uow.committed is True

    async def test_strict_mode_rejects_code_conflict(self):
        uow = FakeUnitOfWork()
        existing = AttributeBuilder().with_code("taken").with_slug("taken-s").build()
        await uow.attributes.add(existing)

        handler = BulkCreateAttributesHandler(
            attribute_repo=uow.attributes,
            group_repo=uow.attribute_groups,
            uow=uow,
            logger=make_logger(),
        )
        cmd = BulkCreateAttributesCommand(
            items=[_make_bulk_item("taken", "new-slug")],
            skip_existing=False,
        )

        with pytest.raises(AttributeCodeConflictError):
            await handler.handle(cmd)
        assert uow.committed is False

    async def test_strict_mode_rejects_slug_conflict(self):
        uow = FakeUnitOfWork()
        existing = AttributeBuilder().with_code("diff-code").with_slug("taken").build()
        await uow.attributes.add(existing)

        handler = BulkCreateAttributesHandler(
            attribute_repo=uow.attributes,
            group_repo=uow.attribute_groups,
            uow=uow,
            logger=make_logger(),
        )
        cmd = BulkCreateAttributesCommand(
            items=[_make_bulk_item("new-code", "taken")],
            skip_existing=False,
        )

        with pytest.raises(AttributeSlugConflictError):
            await handler.handle(cmd)
        assert uow.committed is False

    async def test_rejects_batch_limit_exceeded(self):
        uow = FakeUnitOfWork()
        handler = BulkCreateAttributesHandler(
            attribute_repo=uow.attributes,
            group_repo=uow.attribute_groups,
            uow=uow,
            logger=make_logger(),
        )
        items = [_make_bulk_item(f"code-{i}", f"slug-{i}") for i in range(101)]
        cmd = BulkCreateAttributesCommand(items=items)

        with pytest.raises(ValidationError) as exc_info:
            await handler.handle(cmd)
        assert exc_info.value.error_code == "BULK_LIMIT_EXCEEDED"

    async def test_rejects_duplicate_codes_in_batch(self):
        uow = FakeUnitOfWork()
        handler = BulkCreateAttributesHandler(
            attribute_repo=uow.attributes,
            group_repo=uow.attribute_groups,
            uow=uow,
            logger=make_logger(),
        )
        cmd = BulkCreateAttributesCommand(
            items=[
                _make_bulk_item("dup", "slug-1"),
                _make_bulk_item("dup", "slug-2"),
            ],
        )

        with pytest.raises(ValidationError) as exc_info:
            await handler.handle(cmd)
        assert exc_info.value.error_code == "BULK_DUPLICATE_CODES"

    async def test_rejects_duplicate_slugs_in_batch(self):
        uow = FakeUnitOfWork()
        handler = BulkCreateAttributesHandler(
            attribute_repo=uow.attributes,
            group_repo=uow.attribute_groups,
            uow=uow,
            logger=make_logger(),
        )
        cmd = BulkCreateAttributesCommand(
            items=[
                _make_bulk_item("code-1", "dup-slug"),
                _make_bulk_item("code-2", "dup-slug"),
            ],
        )

        with pytest.raises(ValidationError) as exc_info:
            await handler.handle(cmd)
        assert exc_info.value.error_code == "BULK_DUPLICATE_SLUGS"

    async def test_rejects_group_not_found(self):
        uow = FakeUnitOfWork()
        handler = BulkCreateAttributesHandler(
            attribute_repo=uow.attributes,
            group_repo=uow.attribute_groups,
            uow=uow,
            logger=make_logger(),
        )
        cmd = BulkCreateAttributesCommand(
            items=[_make_bulk_item("grp", "grp", group_id=uuid.uuid4())],
        )

        with pytest.raises(AttributeGroupNotFoundError):
            await handler.handle(cmd)
        assert uow.committed is False

    async def test_emits_events_for_each_created(self):
        uow = FakeUnitOfWork()
        handler = BulkCreateAttributesHandler(
            attribute_repo=uow.attributes,
            group_repo=uow.attribute_groups,
            uow=uow,
            logger=make_logger(),
        )
        cmd = BulkCreateAttributesCommand(
            items=[
                _make_bulk_item("evt-1", "evt-1"),
                _make_bulk_item("evt-2", "evt-2"),
            ],
        )

        await handler.handle(cmd)

        events = [
            e for e in uow.collected_events if isinstance(e, AttributeCreatedEvent)
        ]
        assert len(events) == 2


# ============================================================================
# TestBindAttributeToTemplate
# ============================================================================


class TestBindAttributeToTemplate:
    """Tests for BindAttributeToTemplateHandler (ICacheService mock needed)."""

    async def test_binds_attribute_and_commits(self):
        uow = FakeUnitOfWork()
        template = AttributeTemplateBuilder().with_code("tmpl").build()
        attr = AttributeBuilder().with_code("a").with_slug("a").build()
        await uow.attribute_templates.add(template)
        await uow.attributes.add(attr)

        handler = BindAttributeToTemplateHandler(
            template_repo=uow.attribute_templates,
            attribute_repo=uow.attributes,
            binding_repo=uow.template_bindings,
            uow=uow,
            cache=make_cache(),
            logger=make_logger(),
        )
        cmd = BindAttributeToTemplateCommand(
            template_id=template.id,
            attribute_id=attr.id,
        )

        result = await handler.handle(cmd)

        assert result.binding_id in uow.template_bindings._store
        assert uow.committed is True

    async def test_rejects_template_not_found(self):
        uow = FakeUnitOfWork()
        attr = AttributeBuilder().with_code("a").with_slug("a").build()
        await uow.attributes.add(attr)

        handler = BindAttributeToTemplateHandler(
            template_repo=uow.attribute_templates,
            attribute_repo=uow.attributes,
            binding_repo=uow.template_bindings,
            uow=uow,
            cache=make_cache(),
            logger=make_logger(),
        )
        cmd = BindAttributeToTemplateCommand(
            template_id=uuid.uuid4(),
            attribute_id=attr.id,
        )

        with pytest.raises(AttributeTemplateNotFoundError):
            await handler.handle(cmd)
        assert uow.committed is False

    async def test_rejects_attribute_not_found(self):
        uow = FakeUnitOfWork()
        template = AttributeTemplateBuilder().with_code("tmpl").build()
        await uow.attribute_templates.add(template)

        handler = BindAttributeToTemplateHandler(
            template_repo=uow.attribute_templates,
            attribute_repo=uow.attributes,
            binding_repo=uow.template_bindings,
            uow=uow,
            cache=make_cache(),
            logger=make_logger(),
        )
        cmd = BindAttributeToTemplateCommand(
            template_id=template.id,
            attribute_id=uuid.uuid4(),
        )

        with pytest.raises(AttributeNotFoundError):
            await handler.handle(cmd)
        assert uow.committed is False

    async def test_rejects_already_bound(self):
        uow = FakeUnitOfWork()
        template = AttributeTemplateBuilder().with_code("tmpl").build()
        attr = AttributeBuilder().with_code("a").with_slug("a").build()
        await uow.attribute_templates.add(template)
        await uow.attributes.add(attr)

        # Pre-seed existing binding
        existing_binding = (
            TemplateAttributeBindingBuilder()
            .with_template_id(template.id)
            .with_attribute_id(attr.id)
            .build()
        )
        await uow.template_bindings.add(existing_binding)

        handler = BindAttributeToTemplateHandler(
            template_repo=uow.attribute_templates,
            attribute_repo=uow.attributes,
            binding_repo=uow.template_bindings,
            uow=uow,
            cache=make_cache(),
            logger=make_logger(),
        )
        cmd = BindAttributeToTemplateCommand(
            template_id=template.id,
            attribute_id=attr.id,
        )

        with pytest.raises(TemplateAttributeBindingAlreadyExistsError):
            await handler.handle(cmd)
        assert uow.committed is False

    async def test_emits_binding_created_event(self):
        uow = FakeUnitOfWork()
        template = AttributeTemplateBuilder().with_code("tmpl-evt").build()
        attr = AttributeBuilder().with_code("a-evt").with_slug("a-evt").build()
        await uow.attribute_templates.add(template)
        await uow.attributes.add(attr)

        handler = BindAttributeToTemplateHandler(
            template_repo=uow.attribute_templates,
            attribute_repo=uow.attributes,
            binding_repo=uow.template_bindings,
            uow=uow,
            cache=make_cache(),
            logger=make_logger(),
        )
        cmd = BindAttributeToTemplateCommand(
            template_id=template.id,
            attribute_id=attr.id,
        )

        result = await handler.handle(cmd)

        events = [
            e
            for e in uow.collected_events
            if isinstance(e, TemplateAttributeBindingCreatedEvent)
        ]
        assert len(events) == 1
        assert events[0].binding_id == result.binding_id


# ============================================================================
# TestUnbindAttributeFromTemplate
# ============================================================================


class TestUnbindAttributeFromTemplate:
    """Tests for UnbindAttributeFromTemplateHandler (ICacheService mock needed)."""

    async def test_unbinds_and_commits(self):
        uow = FakeUnitOfWork()
        template = AttributeTemplateBuilder().with_code("tmpl").build()
        await uow.attribute_templates.add(template)

        binding = (
            TemplateAttributeBindingBuilder()
            .with_template_id(template.id)
            .with_attribute_id(uuid.uuid4())
            .build()
        )
        await uow.template_bindings.add(binding)

        handler = UnbindAttributeFromTemplateHandler(
            template_repo=uow.attribute_templates,
            binding_repo=uow.template_bindings,
            uow=uow,
            cache=make_cache(),
            logger=make_logger(),
        )
        cmd = UnbindAttributeFromTemplateCommand(
            binding_id=binding.id,
            template_id=template.id,
        )

        await handler.handle(cmd)

        assert binding.id not in uow.template_bindings._store
        assert uow.committed is True

    async def test_rejects_not_found(self):
        uow = FakeUnitOfWork()
        handler = UnbindAttributeFromTemplateHandler(
            template_repo=uow.attribute_templates,
            binding_repo=uow.template_bindings,
            uow=uow,
            cache=make_cache(),
            logger=make_logger(),
        )
        cmd = UnbindAttributeFromTemplateCommand(
            binding_id=uuid.uuid4(),
            template_id=uuid.uuid4(),
        )

        with pytest.raises(TemplateAttributeBindingNotFoundError):
            await handler.handle(cmd)
        assert uow.committed is False

    async def test_rejects_wrong_template_ownership(self):
        uow = FakeUnitOfWork()
        template_a = AttributeTemplateBuilder().with_code("a").build()
        template_b = AttributeTemplateBuilder().with_code("b").build()
        await uow.attribute_templates.add(template_a)
        await uow.attribute_templates.add(template_b)

        binding = (
            TemplateAttributeBindingBuilder()
            .with_template_id(template_a.id)
            .with_attribute_id(uuid.uuid4())
            .build()
        )
        await uow.template_bindings.add(binding)

        handler = UnbindAttributeFromTemplateHandler(
            template_repo=uow.attribute_templates,
            binding_repo=uow.template_bindings,
            uow=uow,
            cache=make_cache(),
            logger=make_logger(),
        )
        # Use template_b's ID with binding that belongs to template_a
        cmd = UnbindAttributeFromTemplateCommand(
            binding_id=binding.id,
            template_id=template_b.id,
        )

        with pytest.raises(TemplateAttributeBindingNotFoundError):
            await handler.handle(cmd)
        assert uow.committed is False

    async def test_emits_binding_deleted_event(self):
        uow = FakeUnitOfWork()
        template = AttributeTemplateBuilder().with_code("tmpl-del").build()
        await uow.attribute_templates.add(template)

        binding = (
            TemplateAttributeBindingBuilder()
            .with_template_id(template.id)
            .with_attribute_id(uuid.uuid4())
            .build()
        )
        await uow.template_bindings.add(binding)

        handler = UnbindAttributeFromTemplateHandler(
            template_repo=uow.attribute_templates,
            binding_repo=uow.template_bindings,
            uow=uow,
            cache=make_cache(),
            logger=make_logger(),
        )
        cmd = UnbindAttributeFromTemplateCommand(
            binding_id=binding.id,
            template_id=template.id,
        )

        await handler.handle(cmd)

        events = [
            e
            for e in uow.collected_events
            if isinstance(e, TemplateAttributeBindingDeletedEvent)
        ]
        assert len(events) == 1
        assert events[0].binding_id == binding.id


# ============================================================================
# TestUpdateTemplateAttributeBinding
# ============================================================================


class TestUpdateTemplateAttributeBinding:
    """Tests for UpdateTemplateAttributeBindingHandler (CRITICAL: _provided_fields + ICacheService)."""

    async def test_updates_binding_and_commits(self):
        uow = FakeUnitOfWork()
        template = AttributeTemplateBuilder().with_code("tmpl").build()
        await uow.attribute_templates.add(template)

        binding = (
            TemplateAttributeBindingBuilder()
            .with_template_id(template.id)
            .with_attribute_id(uuid.uuid4())
            .with_sort_order(0)
            .build()
        )
        await uow.template_bindings.add(binding)

        handler = UpdateTemplateAttributeBindingHandler(
            template_repo=uow.attribute_templates,
            binding_repo=uow.template_bindings,
            uow=uow,
            cache=make_cache(),
            logger=make_logger(),
        )
        cmd = UpdateTemplateAttributeBindingCommand(
            binding_id=binding.id,
            template_id=template.id,
            sort_order=10,
            _provided_fields=frozenset({"sort_order"}),
        )

        result = await handler.handle(cmd)

        assert result.sort_order == 10
        assert uow.committed is True

    async def test_rejects_not_found(self):
        uow = FakeUnitOfWork()
        handler = UpdateTemplateAttributeBindingHandler(
            template_repo=uow.attribute_templates,
            binding_repo=uow.template_bindings,
            uow=uow,
            cache=make_cache(),
            logger=make_logger(),
        )
        cmd = UpdateTemplateAttributeBindingCommand(
            binding_id=uuid.uuid4(),
            template_id=uuid.uuid4(),
            sort_order=1,
            _provided_fields=frozenset({"sort_order"}),
        )

        with pytest.raises(TemplateAttributeBindingNotFoundError):
            await handler.handle(cmd)
        assert uow.committed is False

    async def test_rejects_wrong_template_ownership(self):
        uow = FakeUnitOfWork()
        template_a = AttributeTemplateBuilder().with_code("a").build()
        template_b = AttributeTemplateBuilder().with_code("b").build()
        await uow.attribute_templates.add(template_a)
        await uow.attribute_templates.add(template_b)

        binding = (
            TemplateAttributeBindingBuilder()
            .with_template_id(template_a.id)
            .with_attribute_id(uuid.uuid4())
            .build()
        )
        await uow.template_bindings.add(binding)

        handler = UpdateTemplateAttributeBindingHandler(
            template_repo=uow.attribute_templates,
            binding_repo=uow.template_bindings,
            uow=uow,
            cache=make_cache(),
            logger=make_logger(),
        )
        cmd = UpdateTemplateAttributeBindingCommand(
            binding_id=binding.id,
            template_id=template_b.id,
            sort_order=5,
            _provided_fields=frozenset({"sort_order"}),
        )

        with pytest.raises(TemplateAttributeBindingNotFoundError):
            await handler.handle(cmd)
        assert uow.committed is False

    async def test_emits_binding_updated_event(self):
        uow = FakeUnitOfWork()
        template = AttributeTemplateBuilder().with_code("tmpl-evt").build()
        await uow.attribute_templates.add(template)

        binding = (
            TemplateAttributeBindingBuilder()
            .with_template_id(template.id)
            .with_attribute_id(uuid.uuid4())
            .build()
        )
        await uow.template_bindings.add(binding)

        handler = UpdateTemplateAttributeBindingHandler(
            template_repo=uow.attribute_templates,
            binding_repo=uow.template_bindings,
            uow=uow,
            cache=make_cache(),
            logger=make_logger(),
        )
        cmd = UpdateTemplateAttributeBindingCommand(
            binding_id=binding.id,
            template_id=template.id,
            requirement_level=RequirementLevel.REQUIRED,
            _provided_fields=frozenset({"requirement_level"}),
        )

        await handler.handle(cmd)

        events = [
            e
            for e in uow.collected_events
            if isinstance(e, TemplateAttributeBindingUpdatedEvent)
        ]
        assert len(events) == 1
        assert events[0].binding_id == binding.id


# ============================================================================
# TestReorderTemplateBindings
# ============================================================================


class TestReorderTemplateBindings:
    """Tests for ReorderTemplateBindingsHandler (ICacheService mock needed)."""

    async def test_reorders_bindings_and_commits(self):
        uow = FakeUnitOfWork()
        template = AttributeTemplateBuilder().with_code("tmpl").build()
        await uow.attribute_templates.add(template)

        b1 = (
            TemplateAttributeBindingBuilder()
            .with_template_id(template.id)
            .with_attribute_id(uuid.uuid4())
            .with_sort_order(0)
            .build()
        )
        b2 = (
            TemplateAttributeBindingBuilder()
            .with_template_id(template.id)
            .with_attribute_id(uuid.uuid4())
            .with_sort_order(1)
            .build()
        )
        await uow.template_bindings.add(b1)
        await uow.template_bindings.add(b2)

        handler = ReorderTemplateBindingsHandler(
            template_repo=uow.attribute_templates,
            binding_repo=uow.template_bindings,
            uow=uow,
            cache=make_cache(),
            logger=make_logger(),
        )
        # Swap sort orders
        cmd = ReorderTemplateBindingsCommand(
            template_id=template.id,
            items=[
                BindingReorderItem(binding_id=b1.id, sort_order=1),
                BindingReorderItem(binding_id=b2.id, sort_order=0),
            ],
        )

        await handler.handle(cmd)

        assert uow.committed is True
        assert uow.template_bindings._store[b1.id].sort_order == 1
        assert uow.template_bindings._store[b2.id].sort_order == 0

    async def test_rejects_template_not_found(self):
        uow = FakeUnitOfWork()
        handler = ReorderTemplateBindingsHandler(
            template_repo=uow.attribute_templates,
            binding_repo=uow.template_bindings,
            uow=uow,
            cache=make_cache(),
            logger=make_logger(),
        )
        cmd = ReorderTemplateBindingsCommand(
            template_id=uuid.uuid4(),
            items=[
                BindingReorderItem(binding_id=uuid.uuid4(), sort_order=0),
            ],
        )

        with pytest.raises(AttributeTemplateNotFoundError):
            await handler.handle(cmd)
        assert uow.committed is False

    async def test_rejects_binding_not_in_template(self):
        uow = FakeUnitOfWork()
        template = AttributeTemplateBuilder().with_code("tmpl").build()
        await uow.attribute_templates.add(template)

        # Create a binding belonging to a DIFFERENT template
        other_template_id = uuid.uuid4()
        foreign_binding = (
            TemplateAttributeBindingBuilder()
            .with_template_id(other_template_id)
            .with_attribute_id(uuid.uuid4())
            .build()
        )
        await uow.template_bindings.add(foreign_binding)

        handler = ReorderTemplateBindingsHandler(
            template_repo=uow.attribute_templates,
            binding_repo=uow.template_bindings,
            uow=uow,
            cache=make_cache(),
            logger=make_logger(),
        )
        cmd = ReorderTemplateBindingsCommand(
            template_id=template.id,
            items=[
                BindingReorderItem(binding_id=foreign_binding.id, sort_order=0),
            ],
        )

        with pytest.raises(TemplateAttributeBindingNotFoundError):
            await handler.handle(cmd)
        assert uow.committed is False

    async def test_rejects_duplicate_binding_ids(self):
        uow = FakeUnitOfWork()
        template = AttributeTemplateBuilder().with_code("tmpl").build()
        await uow.attribute_templates.add(template)

        binding = (
            TemplateAttributeBindingBuilder()
            .with_template_id(template.id)
            .with_attribute_id(uuid.uuid4())
            .build()
        )
        await uow.template_bindings.add(binding)

        handler = ReorderTemplateBindingsHandler(
            template_repo=uow.attribute_templates,
            binding_repo=uow.template_bindings,
            uow=uow,
            cache=make_cache(),
            logger=make_logger(),
        )
        # Same binding_id repeated
        cmd = ReorderTemplateBindingsCommand(
            template_id=template.id,
            items=[
                BindingReorderItem(binding_id=binding.id, sort_order=0),
                BindingReorderItem(binding_id=binding.id, sort_order=1),
            ],
        )

        with pytest.raises(TemplateAttributeBindingNotFoundError):
            await handler.handle(cmd)
        assert uow.committed is False
