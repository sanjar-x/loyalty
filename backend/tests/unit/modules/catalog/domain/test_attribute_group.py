"""Unit tests for AttributeGroup entity.

Covers factory method, explicit-kwargs update, guarded-field __setattr__
guard, and i18n/sort_order validation for the attribute group aggregate.
"""

from __future__ import annotations

import uuid

import pytest

from src.modules.catalog.domain.entities import AttributeGroup
from src.modules.catalog.domain.exceptions import MissingRequiredLocalesError
from tests.factories.attribute_group_builder import AttributeGroupBuilder


def _i18n(en: str, ru: str | None = None) -> dict[str, str]:
    return {"en": en, "ru": ru or en}


# ============================================================================
# AttributeGroup -- create
# ============================================================================


class TestAttributeGroupCreate:
    def test_create_valid(self):
        group = AttributeGroupBuilder().build()
        assert isinstance(group.id, uuid.UUID)
        assert group.sort_order == 0

    def test_create_rejects_missing_locale(self):
        with pytest.raises(MissingRequiredLocalesError):
            AttributeGroup.create(
                code="physical",
                name_i18n={"en": "Only English"},
            )

    def test_create_rejects_blank_i18n_values(self):
        with pytest.raises(ValueError):
            AttributeGroup.create(
                code="physical",
                name_i18n={"en": "", "ru": "Valid"},
            )

    def test_create_rejects_negative_sort_order(self):
        with pytest.raises(ValueError, match="sort_order must be non-negative"):
            AttributeGroup.create(
                code="physical",
                name_i18n=_i18n("Physical"),
                sort_order=-1,
            )

    def test_create_custom_sort_order(self):
        group = AttributeGroupBuilder().with_sort_order(3).build()
        assert group.sort_order == 3

    def test_create_with_explicit_group_id(self):
        gid = uuid.uuid4()
        group = AttributeGroup.create(
            code="tech",
            name_i18n=_i18n("Technical"),
            group_id=gid,
        )
        assert group.id == gid


# ============================================================================
# AttributeGroup -- update (explicit kwargs, not **kwargs)
# ============================================================================


class TestAttributeGroupUpdate:
    def test_update_name_i18n(self):
        group = AttributeGroupBuilder().build()
        group.update(name_i18n=_i18n("New"))
        assert group.name_i18n == _i18n("New")

    def test_update_sort_order(self):
        group = AttributeGroupBuilder().build()
        group.update(sort_order=10)
        assert group.sort_order == 10

    def test_update_rejects_empty_name_i18n(self):
        group = AttributeGroupBuilder().build()
        with pytest.raises(ValueError):
            group.update(name_i18n={"en": "", "ru": ""})

    def test_update_name_i18n_omitted_keeps_current(self):
        """When name_i18n is not provided (None default), the current value is kept."""
        group = AttributeGroupBuilder().with_name_i18n(_i18n("Original")).build()
        original_name = group.name_i18n.copy()
        group.update(sort_order=5)
        assert group.name_i18n == original_name
        assert group.sort_order == 5


# ============================================================================
# AttributeGroup -- __setattr__ guard
# ============================================================================


class TestAttributeGroupGuard:
    def test_direct_code_assignment_raises(self):
        group = AttributeGroupBuilder().build()
        with pytest.raises(AttributeError, match="Cannot set 'code' directly"):
            group.code = "new-code"
