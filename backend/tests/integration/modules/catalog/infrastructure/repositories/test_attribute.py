"""
Integration tests for AttributeRepository Data Mapper roundtrips.

Proves that Attribute entities survive full CRUD cycles through real
PostgreSQL, including BehaviorFlags VO decomposition (5 columns -> 1 VO),
JSONB i18n fields, enum mapping, and query methods.

Part of Phase 07 -- Repository & Data Integrity (REPO-02, REPO-05).
"""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.domain.entities import Attribute
from src.modules.catalog.domain.value_objects import (
    AttributeDataType,
    AttributeLevel,
    AttributeUIType,
    BehaviorFlags,
)
from src.modules.catalog.infrastructure.models import (
    AttributeGroup as OrmAttributeGroup,
)
from src.modules.catalog.infrastructure.repositories.attribute import (
    AttributeRepository,
)


@pytest.fixture()
async def _seed_group(db_session: AsyncSession) -> uuid.UUID:
    """Insert an AttributeGroup via ORM for FK satisfaction."""
    group_id = uuid.uuid4()
    group = OrmAttributeGroup(
        id=group_id,
        code="attr-test-group",
        name_i18n={"en": "Test Group", "ru": "Тестовая группа"},
        sort_order=0,
    )
    db_session.add(group)
    await db_session.flush()
    return group_id


class TestAttributeRoundtrip:
    """Verify Attribute entity survives full create-read roundtrip."""

    async def test_attribute_basic_roundtrip(
        self,
        db_session: AsyncSession,
        _seed_group: uuid.UUID,
    ) -> None:
        """All Attribute scalar and enum fields survive roundtrip."""
        repo = AttributeRepository(session=db_session)
        attr = Attribute.create(
            code="color",
            slug="color",
            name_i18n={"en": "Color", "ru": "Цвет"},
            description_i18n={"en": "Product color", "ru": "Цвет продукта"},
            data_type=AttributeDataType.STRING,
            ui_type=AttributeUIType.COLOR_SWATCH,
            is_dictionary=True,
            group_id=_seed_group,
            level=AttributeLevel.VARIANT,
        )
        await repo.add(attr)
        await db_session.flush()

        fetched = await repo.get(attr.id)

        assert fetched is not None
        assert fetched.code == "color"
        assert fetched.slug == "color"
        assert fetched.name_i18n == {"en": "Color", "ru": "Цвет"}
        assert fetched.description_i18n == {"en": "Product color", "ru": "Цвет продукта"}
        assert fetched.data_type == AttributeDataType.STRING
        assert fetched.ui_type == AttributeUIType.COLOR_SWATCH
        assert fetched.level == AttributeLevel.VARIANT
        assert fetched.is_dictionary is True
        assert fetched.group_id == _seed_group

    async def test_attribute_behavior_flags_roundtrip(
        self,
        db_session: AsyncSession,
        _seed_group: uuid.UUID,
    ) -> None:
        """BehaviorFlags VO with custom values survives roundtrip."""
        repo = AttributeRepository(session=db_session)
        attr = Attribute.create(
            code="size",
            slug="size",
            name_i18n={"en": "Size", "ru": "Размер"},
            data_type=AttributeDataType.STRING,
            ui_type=AttributeUIType.TEXT_BUTTON,
            is_dictionary=True,
            group_id=_seed_group,
            behavior=BehaviorFlags(
                is_filterable=True,
                is_searchable=True,
                search_weight=8,
                is_comparable=True,
                is_visible_on_card=True,
            ),
        )
        await repo.add(attr)
        await db_session.flush()

        fetched = await repo.get(attr.id)

        assert fetched is not None
        # Via VO
        assert fetched.behavior.is_filterable is True
        assert fetched.behavior.is_searchable is True
        assert fetched.behavior.search_weight == 8
        assert fetched.behavior.is_comparable is True
        assert fetched.behavior.is_visible_on_card is True
        # Via backward-compatible properties
        assert fetched.is_filterable is True
        assert fetched.is_searchable is True
        assert fetched.search_weight == 8
        assert fetched.is_comparable is True
        assert fetched.is_visible_on_card is True

    async def test_attribute_behavior_flags_defaults(
        self,
        db_session: AsyncSession,
        _seed_group: uuid.UUID,
    ) -> None:
        """Default BehaviorFlags (all False, weight=5) survives roundtrip."""
        repo = AttributeRepository(session=db_session)
        attr = Attribute.create(
            code="material",
            slug="material",
            name_i18n={"en": "Material", "ru": "Материал"},
            data_type=AttributeDataType.STRING,
            ui_type=AttributeUIType.DROPDOWN,
            is_dictionary=True,
            group_id=_seed_group,
        )
        await repo.add(attr)
        await db_session.flush()

        fetched = await repo.get(attr.id)

        assert fetched is not None
        assert fetched.behavior.is_filterable is False
        assert fetched.behavior.is_searchable is False
        assert fetched.behavior.search_weight == 5
        assert fetched.behavior.is_comparable is False
        assert fetched.behavior.is_visible_on_card is False

    async def test_attribute_validation_rules_roundtrip(
        self,
        db_session: AsyncSession,
        _seed_group: uuid.UUID,
    ) -> None:
        """JSONB validation_rules survives roundtrip."""
        repo = AttributeRepository(session=db_session)
        attr = Attribute.create(
            code="desc-length",
            slug="desc-length",
            name_i18n={"en": "Description Length", "ru": "Длина описания"},
            data_type=AttributeDataType.STRING,
            ui_type=AttributeUIType.TEXT_BUTTON,
            is_dictionary=False,
            group_id=_seed_group,
            validation_rules={"min_length": 1, "max_length": 255},
        )
        await repo.add(attr)
        await db_session.flush()

        fetched = await repo.get(attr.id)

        assert fetched is not None
        assert fetched.validation_rules == {"min_length": 1, "max_length": 255}

    async def test_attribute_validation_rules_none_roundtrip(
        self,
        db_session: AsyncSession,
        _seed_group: uuid.UUID,
    ) -> None:
        """validation_rules=None survives roundtrip as None."""
        repo = AttributeRepository(session=db_session)
        attr = Attribute.create(
            code="no-rules",
            slug="no-rules",
            name_i18n={"en": "No Rules", "ru": "Без правил"},
            data_type=AttributeDataType.STRING,
            ui_type=AttributeUIType.TEXT_BUTTON,
            is_dictionary=True,
            group_id=_seed_group,
            validation_rules=None,
        )
        await repo.add(attr)
        await db_session.flush()

        fetched = await repo.get(attr.id)

        assert fetched is not None
        assert fetched.validation_rules is None


class TestAttributeQueries:
    """Verify Attribute query helper methods."""

    async def test_get_many(
        self,
        db_session: AsyncSession,
        _seed_group: uuid.UUID,
    ) -> None:
        """get_many returns correct subset of attributes."""
        repo = AttributeRepository(session=db_session)
        attrs = []
        for i in range(3):
            attr = Attribute.create(
                code=f"many-{i}",
                slug=f"many-{i}",
                name_i18n={"en": f"Many {i}", "ru": f"Много {i}"},
                data_type=AttributeDataType.STRING,
                ui_type=AttributeUIType.TEXT_BUTTON,
                is_dictionary=True,
                group_id=_seed_group,
            )
            await repo.add(attr)
            attrs.append(attr)
        await db_session.flush()

        result = await repo.get_many([attrs[0].id, attrs[1].id])
        assert len(result) == 2
        assert attrs[0].id in result
        assert attrs[1].id in result

    async def test_check_code_exists(
        self,
        db_session: AsyncSession,
        _seed_group: uuid.UUID,
    ) -> None:
        """check_code_exists returns True/False correctly."""
        repo = AttributeRepository(session=db_session)
        attr = Attribute.create(
            code="exists-code",
            slug="exists-code",
            name_i18n={"en": "Exists Code", "ru": "Существующий код"},
            data_type=AttributeDataType.STRING,
            ui_type=AttributeUIType.TEXT_BUTTON,
            is_dictionary=True,
            group_id=_seed_group,
        )
        await repo.add(attr)
        await db_session.flush()

        assert await repo.check_code_exists("exists-code") is True
        assert await repo.check_code_exists("missing-code") is False

    async def test_check_slug_exists(
        self,
        db_session: AsyncSession,
        _seed_group: uuid.UUID,
    ) -> None:
        """check_slug_exists returns True/False correctly."""
        repo = AttributeRepository(session=db_session)
        attr = Attribute.create(
            code="slug-exists",
            slug="slug-exists",
            name_i18n={"en": "Slug Exists", "ru": "Слаг существует"},
            data_type=AttributeDataType.STRING,
            ui_type=AttributeUIType.TEXT_BUTTON,
            is_dictionary=True,
            group_id=_seed_group,
        )
        await repo.add(attr)
        await db_session.flush()

        assert await repo.check_slug_exists("slug-exists") is True
        assert await repo.check_slug_exists("no-slug") is False

    async def test_has_product_attribute_values_false(
        self,
        db_session: AsyncSession,
        _seed_group: uuid.UUID,
    ) -> None:
        """has_product_attribute_values returns False when no PAV references exist."""
        repo = AttributeRepository(session=db_session)
        attr = Attribute.create(
            code="no-pav",
            slug="no-pav",
            name_i18n={"en": "No PAV", "ru": "Без PAV"},
            data_type=AttributeDataType.STRING,
            ui_type=AttributeUIType.TEXT_BUTTON,
            is_dictionary=True,
            group_id=_seed_group,
        )
        await repo.add(attr)
        await db_session.flush()

        assert await repo.has_product_attribute_values(attr.id) is False
