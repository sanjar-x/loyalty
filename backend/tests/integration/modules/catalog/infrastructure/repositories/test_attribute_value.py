"""
Integration tests for AttributeValueRepository Data Mapper roundtrips.

Proves that AttributeValue entities survive CRUD cycles with JSONB
(value_i18n, meta_data), ARRAY (search_aliases), and scoped uniqueness
checks.

Part of Phase 07 -- Repository & Data Integrity (REPO-02, REPO-05).
"""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.domain.entities import AttributeValue
from src.modules.catalog.domain.value_objects import (
    AttributeDataType,
    AttributeLevel,
    AttributeUIType,
)
from src.modules.catalog.infrastructure.models import (
    Attribute as OrmAttribute,
)
from src.modules.catalog.infrastructure.models import (
    AttributeGroup as OrmAttributeGroup,
)
from src.modules.catalog.infrastructure.repositories.attribute_value import (
    AttributeValueRepository,
)


@pytest.fixture()
async def _seed_attrs(db_session: AsyncSession) -> dict[str, uuid.UUID]:
    """Insert an AttributeGroup + two Attributes for scoped uniqueness tests."""
    group_id = uuid.uuid4()
    group = OrmAttributeGroup(
        id=group_id,
        code="av-test-group",
        name_i18n={"en": "AV Group", "ru": "Группа AV"},
        sort_order=0,
    )
    db_session.add(group)
    await db_session.flush()

    attr1_id = uuid.uuid4()
    attr1 = OrmAttribute(
        id=attr1_id,
        code="av-attr-1",
        slug="av-attr-1",
        group_id=group_id,
        name_i18n={"en": "Attr 1", "ru": "Атрибут 1"},
        description_i18n={},
        data_type=AttributeDataType.STRING,
        ui_type=AttributeUIType.TEXT_BUTTON,
        is_dictionary=True,
        level=AttributeLevel.PRODUCT,
        search_weight=5,
    )
    attr2_id = uuid.uuid4()
    attr2 = OrmAttribute(
        id=attr2_id,
        code="av-attr-2",
        slug="av-attr-2",
        group_id=group_id,
        name_i18n={"en": "Attr 2", "ru": "Атрибут 2"},
        description_i18n={},
        data_type=AttributeDataType.STRING,
        ui_type=AttributeUIType.TEXT_BUTTON,
        is_dictionary=True,
        level=AttributeLevel.PRODUCT,
        search_weight=5,
    )
    db_session.add_all([attr1, attr2])
    await db_session.flush()
    return {"attr1_id": attr1_id, "attr2_id": attr2_id}


class TestAttributeValueRoundtrip:
    """Verify AttributeValue entity survives full create-read roundtrip."""

    async def test_attribute_value_basic_roundtrip(
        self,
        db_session: AsyncSession,
        _seed_attrs: dict[str, uuid.UUID],
    ) -> None:
        """All AttributeValue fields including JSONB/ARRAY survive roundtrip."""
        repo = AttributeValueRepository(session=db_session)
        val = AttributeValue.create(
            attribute_id=_seed_attrs["attr1_id"],
            code="red",
            slug="red",
            value_i18n={"en": "Red", "ru": "Красный"},
            search_aliases=["scarlet", "crimson"],
            meta_data={"hex": "#FF0000"},
            value_group="warm",
            sort_order=1,
            is_active=True,
        )
        await repo.add(val)
        await db_session.flush()

        fetched = await repo.get(val.id)

        assert fetched is not None
        assert fetched.value_i18n == {"en": "Red", "ru": "Красный"}
        assert fetched.search_aliases == ["scarlet", "crimson"]
        assert fetched.meta_data == {"hex": "#FF0000"}
        assert fetched.value_group == "warm"
        assert fetched.sort_order == 1
        assert fetched.is_active is True

    async def test_attribute_value_empty_collections_roundtrip(
        self,
        db_session: AsyncSession,
        _seed_attrs: dict[str, uuid.UUID],
    ) -> None:
        """Empty search_aliases and meta_data survive roundtrip."""
        repo = AttributeValueRepository(session=db_session)
        val = AttributeValue.create(
            attribute_id=_seed_attrs["attr1_id"],
            code="basic",
            slug="basic",
            value_i18n={"en": "Basic", "ru": "Базовый"},
            search_aliases=[],
            meta_data={},
        )
        await repo.add(val)
        await db_session.flush()

        fetched = await repo.get(val.id)

        assert fetched is not None
        assert fetched.search_aliases == []
        assert fetched.meta_data == {}


class TestAttributeValueQueries:
    """Verify AttributeValue query helper methods."""

    async def test_check_code_exists_scoped(
        self,
        db_session: AsyncSession,
        _seed_attrs: dict[str, uuid.UUID],
    ) -> None:
        """check_code_exists is scoped to attribute_id."""
        repo = AttributeValueRepository(session=db_session)
        val1 = AttributeValue.create(
            attribute_id=_seed_attrs["attr1_id"],
            code="red",
            slug="red-1",
            value_i18n={"en": "Red", "ru": "Красный"},
        )
        val2 = AttributeValue.create(
            attribute_id=_seed_attrs["attr2_id"],
            code="red",
            slug="red-2",
            value_i18n={"en": "Red", "ru": "Красный"},
        )
        await repo.add(val1)
        await repo.add(val2)
        await db_session.flush()

        assert await repo.check_code_exists(_seed_attrs["attr1_id"], "red") is True
        assert await repo.check_code_exists(_seed_attrs["attr2_id"], "red") is True
        assert await repo.check_code_exists(_seed_attrs["attr1_id"], "blue") is False

    async def test_check_slug_exists_scoped(
        self,
        db_session: AsyncSession,
        _seed_attrs: dict[str, uuid.UUID],
    ) -> None:
        """check_slug_exists is scoped to attribute_id."""
        repo = AttributeValueRepository(session=db_session)
        val1 = AttributeValue.create(
            attribute_id=_seed_attrs["attr1_id"],
            code="slug-a",
            slug="same-slug",
            value_i18n={"en": "A", "ru": "А"},
        )
        val2 = AttributeValue.create(
            attribute_id=_seed_attrs["attr2_id"],
            code="slug-b",
            slug="same-slug",
            value_i18n={"en": "B", "ru": "Б"},
        )
        await repo.add(val1)
        await repo.add(val2)
        await db_session.flush()

        assert (
            await repo.check_slug_exists(_seed_attrs["attr1_id"], "same-slug") is True
        )
        assert (
            await repo.check_slug_exists(_seed_attrs["attr1_id"], "other-slug") is False
        )

    async def test_get_many(
        self,
        db_session: AsyncSession,
        _seed_attrs: dict[str, uuid.UUID],
    ) -> None:
        """get_many returns correct subset of values."""
        repo = AttributeValueRepository(session=db_session)
        vals = []
        for i in range(3):
            val = AttributeValue.create(
                attribute_id=_seed_attrs["attr1_id"],
                code=f"gm-{i}",
                slug=f"gm-{i}",
                value_i18n={"en": f"GM {i}", "ru": f"ГМ {i}"},
            )
            await repo.add(val)
            vals.append(val)
        await db_session.flush()

        result = await repo.get_many([vals[0].id, vals[1].id])
        assert len(result) == 2

    async def test_list_ids_by_attribute(
        self,
        db_session: AsyncSession,
        _seed_attrs: dict[str, uuid.UUID],
    ) -> None:
        """list_ids_by_attribute returns correct UUID set."""
        repo = AttributeValueRepository(session=db_session)
        ids = set()
        for i in range(3):
            val = AttributeValue.create(
                attribute_id=_seed_attrs["attr1_id"],
                code=f"li-{i}",
                slug=f"li-{i}",
                value_i18n={"en": f"LI {i}", "ru": f"ЛИ {i}"},
            )
            await repo.add(val)
            ids.add(val.id)
        await db_session.flush()

        result = await repo.list_ids_by_attribute(_seed_attrs["attr1_id"])
        assert ids.issubset(result)

    async def test_has_product_references_false(
        self,
        db_session: AsyncSession,
        _seed_attrs: dict[str, uuid.UUID],
    ) -> None:
        """has_product_references returns False when no references exist."""
        repo = AttributeValueRepository(session=db_session)
        val = AttributeValue.create(
            attribute_id=_seed_attrs["attr1_id"],
            code="no-ref",
            slug="no-ref",
            value_i18n={"en": "No Ref", "ru": "Без ссылок"},
        )
        await repo.add(val)
        await db_session.flush()

        assert await repo.has_product_references(val.id) is False
