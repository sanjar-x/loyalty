"""Unit tests for the Category aggregate root.

Covers Category.create_root(), create_child(), update(), __setattr__ guard,
validate_deletable(), and set_effective_template_id(). Complements the
existing test_category_effective_family.py with broader lifecycle coverage.
Part of the unit test layer -- no I/O or infrastructure dependencies.
"""

import uuid

import pytest

from src.modules.catalog.domain.entities import Category
from src.modules.catalog.domain.exceptions import (
    CategoryHasChildrenError,
    CategoryHasProductsError,
    CategoryMaxDepthError,
    MissingRequiredLocalesError,
)


def _i18n(en: str, ru: str | None = None) -> dict[str, str]:
    """Build a valid i18n dict with both required locales."""
    return {"en": en, "ru": ru or en}


class TestCategoryCreateRoot:
    """Factory method tests for Category.create_root() per D-03."""

    def test_create_root_valid(self):
        cat = Category.create_root(
            name_i18n=_i18n("Electronics"), slug="electronics"
        )
        assert cat.name_i18n["en"] == "Electronics"
        assert cat.name_i18n["ru"] == "Electronics"
        assert cat.slug == "electronics"
        assert cat.parent_id is None
        assert cat.level == 0
        assert cat.full_slug == "electronics"
        assert isinstance(cat.id, uuid.UUID)

    def test_create_root_with_template(self):
        tid = uuid.uuid4()
        cat = Category.create_root(
            name_i18n=_i18n("Electronics"), slug="electronics", template_id=tid
        )
        assert cat.template_id == tid
        assert cat.effective_template_id == tid

    def test_create_root_without_template(self):
        cat = Category.create_root(
            name_i18n=_i18n("Electronics"), slug="electronics"
        )
        assert cat.template_id is None
        assert cat.effective_template_id is None

    def test_create_root_custom_sort_order(self):
        cat = Category.create_root(
            name_i18n=_i18n("Electronics"), slug="electronics", sort_order=5
        )
        assert cat.sort_order == 5

    def test_create_root_rejects_empty_slug(self):
        with pytest.raises(ValueError, match="slug must be non-empty"):
            Category.create_root(name_i18n=_i18n("Electronics"), slug="")

    def test_create_root_rejects_invalid_slug(self):
        with pytest.raises(ValueError, match="slug must be non-empty"):
            Category.create_root(
                name_i18n=_i18n("Electronics"), slug="Bad Slug!"
            )

    def test_create_root_rejects_missing_locale(self):
        with pytest.raises(MissingRequiredLocalesError):
            Category.create_root(
                name_i18n={"en": "Only English"}, slug="electronics"
            )

    def test_create_root_rejects_blank_i18n_values(self):
        with pytest.raises(ValueError, match="must not contain empty or blank"):
            Category.create_root(
                name_i18n={"en": "", "ru": "Valid"}, slug="electronics"
            )

    def test_create_root_rejects_negative_sort_order(self):
        with pytest.raises(ValueError, match="sort_order must be non-negative"):
            Category.create_root(
                name_i18n=_i18n("Electronics"), slug="electronics", sort_order=-1
            )


class TestCategoryCreateChild:
    """Factory method tests for Category.create_child()."""

    def test_create_child_valid(self):
        parent = Category.create_root(
            name_i18n=_i18n("Electronics"), slug="electronics"
        )
        child = Category.create_child(
            name_i18n=_i18n("Phones"), slug="phones", parent=parent
        )
        assert child.level == 1
        assert child.parent_id == parent.id
        assert child.full_slug == "electronics/phones"

    def test_create_child_inherits_template(self):
        tid = uuid.uuid4()
        parent = Category.create_root(
            name_i18n=_i18n("Electronics"),
            slug="electronics",
            template_id=tid,
        )
        child = Category.create_child(
            name_i18n=_i18n("Phones"), slug="phones", parent=parent
        )
        assert child.template_id is None
        assert child.effective_template_id == tid

    def test_create_child_overrides_template(self):
        parent_tid = uuid.uuid4()
        child_tid = uuid.uuid4()
        parent = Category.create_root(
            name_i18n=_i18n("Electronics"),
            slug="electronics",
            template_id=parent_tid,
        )
        child = Category.create_child(
            name_i18n=_i18n("Phones"),
            slug="phones",
            parent=parent,
            template_id=child_tid,
        )
        assert child.effective_template_id == child_tid

    def test_create_child_max_depth_enforcement(self):
        # MAX_CATEGORY_DEPTH = 3
        root = Category.create_root(
            name_i18n=_i18n("L0"), slug="l0"
        )  # level 0
        child = Category.create_child(
            name_i18n=_i18n("L1"), slug="l1", parent=root
        )  # level 1
        grandchild = Category.create_child(
            name_i18n=_i18n("L2"), slug="l2", parent=child
        )  # level 2
        # grandchild is at level 2, its level (2) < MAX_CATEGORY_DEPTH (3)
        # but creating a child from grandchild: grandchild.level (2) < 3, so OK
        great_grandchild = Category.create_child(
            name_i18n=_i18n("L3"), slug="l3", parent=grandchild
        )  # level 3
        # Now great_grandchild is at level 3 == MAX_CATEGORY_DEPTH
        # Attempting to create under it should fail
        with pytest.raises(CategoryMaxDepthError):
            Category.create_child(
                name_i18n=_i18n("L4"), slug="l4", parent=great_grandchild
            )

    def test_create_child_level_2_allowed(self):
        root = Category.create_root(
            name_i18n=_i18n("L0"), slug="l0"
        )
        child = Category.create_child(
            name_i18n=_i18n("L1"), slug="l1", parent=root
        )
        grandchild = Category.create_child(
            name_i18n=_i18n("L2"), slug="l2", parent=child
        )
        assert grandchild.level == 2

    def test_create_child_rejects_invalid_slug(self):
        parent = Category.create_root(
            name_i18n=_i18n("Electronics"), slug="electronics"
        )
        with pytest.raises(ValueError):
            Category.create_child(
                name_i18n=_i18n("Phones"), slug="Bad Slug!", parent=parent
            )


class TestCategoryUpdate:
    """Update method tests for Category.update()."""

    def test_update_name_i18n(self):
        cat = Category.create_root(
            name_i18n=_i18n("Old Name"), slug="old-name"
        )
        cat.update(name_i18n=_i18n("New Name"))
        assert cat.name_i18n["en"] == "New Name"

    def test_update_slug_returns_old_full_slug(self):
        cat = Category.create_root(
            name_i18n=_i18n("Test"), slug="old"
        )
        result = cat.update(slug="new")
        assert result == "old"
        assert cat.slug == "new"

    def test_update_without_slug_returns_none(self):
        cat = Category.create_root(
            name_i18n=_i18n("Test"), slug="test"
        )
        result = cat.update(name_i18n=_i18n("X"))
        assert result is None

    def test_update_sort_order(self):
        cat = Category.create_root(
            name_i18n=_i18n("Test"), slug="test"
        )
        cat.update(sort_order=10)
        assert cat.sort_order == 10

    def test_update_template_id_recomputes_effective(self):
        cat = Category.create_root(
            name_i18n=_i18n("Test"), slug="test"
        )
        new_id = uuid.uuid4()
        cat.update(template_id=new_id)
        assert cat.effective_template_id == new_id

    def test_update_template_id_to_none_clears_effective(self):
        tid = uuid.uuid4()
        cat = Category.create_root(
            name_i18n=_i18n("Test"), slug="test", template_id=tid
        )
        cat.update(template_id=None)
        assert cat.template_id is None
        assert cat.effective_template_id is None

    def test_update_template_id_to_none_with_parent_effective(self):
        parent_tid = uuid.uuid4()
        cat = Category.create_root(
            name_i18n=_i18n("Test"), slug="test", template_id=uuid.uuid4()
        )
        cat.update(template_id=None, parent_effective_template_id=parent_tid)
        assert cat.template_id is None
        assert cat.effective_template_id == parent_tid

    def test_update_rejects_invalid_slug(self):
        cat = Category.create_root(
            name_i18n=_i18n("Test"), slug="test"
        )
        with pytest.raises(ValueError):
            cat.update(slug="Bad Slug!")

    def test_update_rejects_negative_sort_order(self):
        cat = Category.create_root(
            name_i18n=_i18n("Test"), slug="test"
        )
        with pytest.raises(ValueError, match="sort_order must be non-negative"):
            cat.update(sort_order=-1)


class TestCategoryGuard:
    """DDD-01 guard: __setattr__ prevents direct slug mutation."""

    def test_direct_slug_assignment_raises(self):
        cat = Category.create_root(
            name_i18n=_i18n("Test"), slug="test"
        )
        with pytest.raises(
            AttributeError, match="Cannot set 'slug' directly"
        ):
            cat.slug = "hacked"


class TestCategoryDeletion:
    """validate_deletable() deletion guard tests."""

    def test_deletable_when_no_children_no_products(self):
        cat = Category.create_root(
            name_i18n=_i18n("Test"), slug="test"
        )
        cat.validate_deletable(has_children=False, has_products=False)

    def test_not_deletable_when_has_children(self):
        cat = Category.create_root(
            name_i18n=_i18n("Test"), slug="test"
        )
        with pytest.raises(CategoryHasChildrenError):
            cat.validate_deletable(has_children=True, has_products=False)

    def test_not_deletable_when_has_products(self):
        cat = Category.create_root(
            name_i18n=_i18n("Test"), slug="test"
        )
        with pytest.raises(CategoryHasProductsError):
            cat.validate_deletable(has_children=False, has_products=True)


class TestCategorySetEffectiveTemplateId:
    """Tests for Category.set_effective_template_id()."""

    def test_set_to_uuid(self):
        cat = Category.create_root(
            name_i18n=_i18n("Test"), slug="test"
        )
        tid = uuid.uuid4()
        cat.set_effective_template_id(tid)
        assert cat.effective_template_id == tid

    def test_set_to_none(self):
        tid = uuid.uuid4()
        cat = Category.create_root(
            name_i18n=_i18n("Test"), slug="test", template_id=tid
        )
        cat.set_effective_template_id(None)
        assert cat.effective_template_id is None
