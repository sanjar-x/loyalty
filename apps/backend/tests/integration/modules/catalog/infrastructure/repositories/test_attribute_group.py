"""
Integration tests for AttributeGroupRepository Data Mapper roundtrips.

Proves that AttributeGroup entities survive CRUD cycles with JSONB i18n,
code uniqueness, has_attributes check, and move_attributes_to_group.

Part of Phase 07 -- Repository & Data Integrity (REPO-02, REPO-05).
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.domain.entities import AttributeGroup
from src.modules.catalog.domain.value_objects import (
    AttributeDataType,
    AttributeLevel,
    AttributeUIType,
)
from src.modules.catalog.infrastructure.models import Attribute as OrmAttribute
from src.modules.catalog.infrastructure.repositories.attribute_group import (
    AttributeGroupRepository,
)


class TestAttributeGroupRoundtrip:
    """Verify AttributeGroup entity survives full create-read roundtrip."""

    async def test_group_basic_roundtrip(
        self,
        db_session: AsyncSession,
    ) -> None:
        """All AttributeGroup fields survive roundtrip."""
        repo = AttributeGroupRepository(session=db_session)
        group = AttributeGroup.create(
            code="physical",
            name_i18n={"en": "Physical", "ru": "Физические"},
        )
        await repo.add(group)
        await db_session.flush()

        fetched = await repo.get(group.id)

        assert fetched is not None
        assert fetched.code == "physical"
        assert fetched.name_i18n == {"en": "Physical", "ru": "Физические"}

    async def test_group_check_code_exists(
        self,
        db_session: AsyncSession,
    ) -> None:
        """check_code_exists returns True/False correctly."""
        repo = AttributeGroupRepository(session=db_session)
        group = AttributeGroup.create(
            code="check-group",
            name_i18n={"en": "Check", "ru": "Проверка"},
        )
        await repo.add(group)
        await db_session.flush()

        assert await repo.check_code_exists("check-group") is True
        assert await repo.check_code_exists("missing-group") is False

    async def test_group_get_by_code(
        self,
        db_session: AsyncSession,
    ) -> None:
        """get_by_code returns correct entity or None."""
        repo = AttributeGroupRepository(session=db_session)
        group = AttributeGroup.create(
            code="by-code",
            name_i18n={"en": "By Code", "ru": "По коду"},
        )
        await repo.add(group)
        await db_session.flush()

        fetched = await repo.get_by_code("by-code")
        assert fetched is not None
        assert fetched.id == group.id

        missing = await repo.get_by_code("missing")
        assert missing is None

    async def test_group_has_attributes(
        self,
        db_session: AsyncSession,
    ) -> None:
        """has_attributes returns True when group has attributes, False when empty."""
        repo = AttributeGroupRepository(session=db_session)

        # Group with attributes
        group_with = AttributeGroup.create(
            code="has-attrs",
            name_i18n={"en": "Has Attrs", "ru": "С атрибутами"},
        )
        await repo.add(group_with)
        await db_session.flush()

        attr = OrmAttribute(
            id=uuid.uuid4(),
            code="ha-attr",
            slug="ha-attr",
            group_id=group_with.id,
            name_i18n={"en": "Test", "ru": "Тест"},
            description_i18n={},
            data_type=AttributeDataType.STRING,
            ui_type=AttributeUIType.TEXT_BUTTON,
            is_dictionary=True,
            level=AttributeLevel.PRODUCT,
            search_weight=5,
        )
        db_session.add(attr)
        await db_session.flush()

        assert await repo.has_attributes(group_with.id) is True

        # Empty group
        group_empty = AttributeGroup.create(
            code="no-attrs",
            name_i18n={"en": "No Attrs", "ru": "Без атрибутов"},
        )
        await repo.add(group_empty)
        await db_session.flush()

        assert await repo.has_attributes(group_empty.id) is False

    async def test_group_move_attributes(
        self,
        db_session: AsyncSession,
    ) -> None:
        """move_attributes_to_group moves all attributes from source to target."""
        repo = AttributeGroupRepository(session=db_session)

        group_a = AttributeGroup.create(
            code="source-grp",
            name_i18n={"en": "Source", "ru": "Источник"},
        )
        group_b = AttributeGroup.create(
            code="target-grp",
            name_i18n={"en": "Target", "ru": "Цель"},
        )
        await repo.add(group_a)
        await repo.add(group_b)
        await db_session.flush()

        for i in range(2):
            attr = OrmAttribute(
                id=uuid.uuid4(),
                code=f"move-attr-{i}",
                slug=f"move-attr-{i}",
                group_id=group_a.id,
                name_i18n={"en": f"Move {i}", "ru": f"Перемещение {i}"},
                description_i18n={},
                data_type=AttributeDataType.STRING,
                ui_type=AttributeUIType.TEXT_BUTTON,
                is_dictionary=True,
                level=AttributeLevel.PRODUCT,
                search_weight=5,
            )
            db_session.add(attr)
        await db_session.flush()

        # Pre-check
        assert await repo.has_attributes(group_a.id) is True
        assert await repo.has_attributes(group_b.id) is False

        # Act
        await repo.move_attributes_to_group(group_a.id, group_b.id)
        await db_session.flush()

        # Assert
        assert await repo.has_attributes(group_a.id) is False
        assert await repo.has_attributes(group_b.id) is True
