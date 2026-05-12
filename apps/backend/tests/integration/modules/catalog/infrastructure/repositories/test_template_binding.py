"""
Integration tests for TemplateAttributeBindingRepository Data Mapper roundtrips.

Proves that TemplateAttributeBinding entities survive CRUD cycles with
RequirementLevel enum, JSONB filter_settings, pair-uniqueness checks,
batch loading, and list_ids_by_template.

Part of Phase 07 -- Repository & Data Integrity (REPO-02, REPO-05).
"""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.domain.entities import (
    Attribute,
    AttributeTemplate,
    TemplateAttributeBinding,
)
from src.modules.catalog.domain.value_objects import (
    AttributeDataType,
    AttributeUIType,
    RequirementLevel,
)
from src.modules.catalog.infrastructure.models import (
    AttributeGroup as OrmAttributeGroup,
)
from src.modules.catalog.infrastructure.repositories.attribute import (
    AttributeRepository,
)
from src.modules.catalog.infrastructure.repositories.attribute_template import (
    AttributeTemplateRepository,
)
from src.modules.catalog.infrastructure.repositories.template_attribute_binding import (
    TemplateAttributeBindingRepository,
)


@pytest.fixture()
async def _seed_binding_deps(
    db_session: AsyncSession,
) -> dict[str, uuid.UUID]:
    """Create a template and two attributes for binding tests."""
    # Group
    group_id = uuid.uuid4()
    group = OrmAttributeGroup(
        id=group_id,
        code="binding-test-group",
        name_i18n={"en": "Binding Group", "ru": "Группа привязок"},
        sort_order=0,
    )
    db_session.add(group)
    await db_session.flush()

    # Template
    template_repo = AttributeTemplateRepository(session=db_session)
    t1 = AttributeTemplate.create(
        code="binding-template-1",
        name_i18n={"en": "Template 1", "ru": "Шаблон 1"},
    )
    t2 = AttributeTemplate.create(
        code="binding-template-2",
        name_i18n={"en": "Template 2", "ru": "Шаблон 2"},
    )
    await template_repo.add(t1)
    await template_repo.add(t2)
    await db_session.flush()

    # Attributes
    attr_repo = AttributeRepository(session=db_session)
    a1 = Attribute.create(
        code="binding-attr-1",
        slug="binding-attr-1",
        name_i18n={"en": "Attr 1", "ru": "Атрибут 1"},
        data_type=AttributeDataType.STRING,
        ui_type=AttributeUIType.TEXT_BUTTON,
        is_dictionary=True,
        group_id=group_id,
    )
    a2 = Attribute.create(
        code="binding-attr-2",
        slug="binding-attr-2",
        name_i18n={"en": "Attr 2", "ru": "Атрибут 2"},
        data_type=AttributeDataType.INTEGER,
        ui_type=AttributeUIType.RANGE_SLIDER,
        is_dictionary=False,
        group_id=group_id,
    )
    a3 = Attribute.create(
        code="binding-attr-3",
        slug="binding-attr-3",
        name_i18n={"en": "Attr 3", "ru": "Атрибут 3"},
        data_type=AttributeDataType.STRING,
        ui_type=AttributeUIType.CHECKBOX,
        is_dictionary=True,
        group_id=group_id,
    )
    await attr_repo.add(a1)
    await attr_repo.add(a2)
    await attr_repo.add(a3)
    await db_session.flush()

    return {
        "template_1_id": t1.id,
        "template_2_id": t2.id,
        "attr_1_id": a1.id,
        "attr_2_id": a2.id,
        "attr_3_id": a3.id,
    }


class TestBindingRoundtrip:
    """Verify TemplateAttributeBinding entity survives full create-read roundtrip."""

    async def test_binding_basic_roundtrip(
        self,
        db_session: AsyncSession,
        _seed_binding_deps: dict[str, uuid.UUID],
    ) -> None:
        """All binding fields including RequirementLevel enum and JSONB survive roundtrip."""
        repo = TemplateAttributeBindingRepository(session=db_session)
        binding = TemplateAttributeBinding.create(
            template_id=_seed_binding_deps["template_1_id"],
            attribute_id=_seed_binding_deps["attr_1_id"],
            sort_order=5,
            requirement_level=RequirementLevel.REQUIRED,
            filter_settings={"widget": "checkbox"},
        )
        await repo.add(binding)
        await db_session.flush()

        fetched = await repo.get(binding.id)

        assert fetched is not None
        assert fetched.requirement_level == RequirementLevel.REQUIRED
        assert isinstance(fetched.requirement_level, RequirementLevel)
        assert fetched.filter_settings == {"widget": "checkbox"}
        assert fetched.sort_order == 5

    async def test_binding_filter_settings_none(
        self,
        db_session: AsyncSession,
        _seed_binding_deps: dict[str, uuid.UUID],
    ) -> None:
        """filter_settings=None survives roundtrip."""
        repo = TemplateAttributeBindingRepository(session=db_session)
        binding = TemplateAttributeBinding.create(
            template_id=_seed_binding_deps["template_1_id"],
            attribute_id=_seed_binding_deps["attr_2_id"],
            filter_settings=None,
        )
        await repo.add(binding)
        await db_session.flush()

        fetched = await repo.get(binding.id)

        assert fetched is not None
        assert fetched.filter_settings is None

    async def test_check_binding_exists(
        self,
        db_session: AsyncSession,
        _seed_binding_deps: dict[str, uuid.UUID],
    ) -> None:
        """check_binding_exists returns True/False correctly."""
        repo = TemplateAttributeBindingRepository(session=db_session)
        binding = TemplateAttributeBinding.create(
            template_id=_seed_binding_deps["template_1_id"],
            attribute_id=_seed_binding_deps["attr_3_id"],
        )
        await repo.add(binding)
        await db_session.flush()

        assert (
            await repo.check_binding_exists(
                _seed_binding_deps["template_1_id"],
                _seed_binding_deps["attr_3_id"],
            )
            is True
        )
        assert (
            await repo.check_binding_exists(
                _seed_binding_deps["template_1_id"],
                uuid.uuid4(),
            )
            is False
        )

    async def test_get_bindings_for_templates(
        self,
        db_session: AsyncSession,
        _seed_binding_deps: dict[str, uuid.UUID],
    ) -> None:
        """get_bindings_for_templates returns correctly grouped dict."""
        repo = TemplateAttributeBindingRepository(session=db_session)

        # 2 bindings for template_1, 1 for template_2
        b1 = TemplateAttributeBinding.create(
            template_id=_seed_binding_deps["template_1_id"],
            attribute_id=_seed_binding_deps["attr_1_id"],
            sort_order=1,
        )
        b2 = TemplateAttributeBinding.create(
            template_id=_seed_binding_deps["template_1_id"],
            attribute_id=_seed_binding_deps["attr_2_id"],
            sort_order=2,
        )
        b3 = TemplateAttributeBinding.create(
            template_id=_seed_binding_deps["template_2_id"],
            attribute_id=_seed_binding_deps["attr_1_id"],
            sort_order=0,
        )
        await repo.add(b1)
        await repo.add(b2)
        await repo.add(b3)
        await db_session.flush()

        result = await repo.get_bindings_for_templates(
            [
                _seed_binding_deps["template_1_id"],
                _seed_binding_deps["template_2_id"],
            ]
        )

        assert _seed_binding_deps["template_1_id"] in result
        assert _seed_binding_deps["template_2_id"] in result
        assert len(result[_seed_binding_deps["template_1_id"]]) == 2
        assert len(result[_seed_binding_deps["template_2_id"]]) == 1

    async def test_list_ids_by_template(
        self,
        db_session: AsyncSession,
        _seed_binding_deps: dict[str, uuid.UUID],
    ) -> None:
        """list_ids_by_template returns correct UUID set."""
        repo = TemplateAttributeBindingRepository(session=db_session)

        binding_ids = set()
        for i, attr_key in enumerate(["attr_1_id", "attr_2_id", "attr_3_id"]):
            b = TemplateAttributeBinding.create(
                template_id=_seed_binding_deps["template_2_id"],
                attribute_id=_seed_binding_deps[attr_key],
                sort_order=i,
            )
            await repo.add(b)
            binding_ids.add(b.id)
        await db_session.flush()

        result = await repo.list_ids_by_template(_seed_binding_deps["template_2_id"])
        assert result == binding_ids
