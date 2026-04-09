"""Unit tests for Attribute, AttributeValue, and ProductAttributeValue entities.

Covers factory methods, update logic, guarded-field __setattr__ guards,
behavior-flag delegation, and validation rules for the EAV attribute
subsystem.
"""

from __future__ import annotations

import uuid

import pytest

from src.modules.catalog.domain.entities import (
    Attribute,
    AttributeValue,
)
from src.modules.catalog.domain.exceptions import MissingRequiredLocalesError
from src.modules.catalog.domain.value_objects import (
    AttributeDataType,
    AttributeLevel,
    AttributeUIType,
    BehaviorFlags,
)
from tests.factories.attribute_builder import (
    AttributeBuilder,
    AttributeValueBuilder,
    ProductAttributeValueBuilder,
)


def _i18n(en: str, ru: str | None = None) -> dict[str, str]:
    return {"en": en, "ru": ru or en}


# ============================================================================
# Attribute -- create
# ============================================================================


class TestAttributeCreate:
    def test_create_valid(self):
        attr = AttributeBuilder().build()
        assert isinstance(attr.id, uuid.UUID)
        assert attr.data_type == AttributeDataType.STRING
        assert attr.level == AttributeLevel.PRODUCT

    def test_create_with_behavior_flags_object(self):
        attr = (
            AttributeBuilder()
            .with_behavior(BehaviorFlags(is_filterable=True, search_weight=8))
            .build()
        )
        assert attr.behavior.is_filterable is True
        assert attr.behavior.search_weight == 8

    def test_create_with_individual_behavior_flags(self):
        attr = Attribute.create(
            code="x",
            slug="x",
            name_i18n=_i18n("X"),
            data_type=AttributeDataType.STRING,
            ui_type=AttributeUIType.DROPDOWN,
            is_dictionary=True,
            group_id=uuid.uuid4(),
            is_filterable=True,
            search_weight=8,
        )
        assert attr.is_filterable is True
        assert attr.search_weight == 8

    def test_create_at_variant_level(self):
        attr = AttributeBuilder().at_variant_level().build()
        assert attr.level == AttributeLevel.VARIANT

    def test_create_with_validation_rules(self):
        attr = (
            AttributeBuilder()
            .with_data_type(AttributeDataType.STRING)
            .with_validation_rules({"min_length": 1, "max_length": 100})
            .build()
        )
        assert attr.validation_rules == {"min_length": 1, "max_length": 100}

    def test_create_rejects_invalid_slug_with_spaces(self):
        """Slug is validated via _validate_slug; code is not validated."""
        with pytest.raises(ValueError, match="slug must be non-empty"):
            Attribute.create(
                code="valid",
                slug="BAD SLUG!",
                name_i18n=_i18n("X"),
                data_type=AttributeDataType.STRING,
                ui_type=AttributeUIType.DROPDOWN,
                is_dictionary=True,
                group_id=uuid.uuid4(),
            )

    def test_create_rejects_invalid_slug_with_uppercase(self):
        with pytest.raises(ValueError):
            Attribute.create(
                code="valid",
                slug="Bad-Slug",
                name_i18n=_i18n("X"),
                data_type=AttributeDataType.STRING,
                ui_type=AttributeUIType.DROPDOWN,
                is_dictionary=True,
                group_id=uuid.uuid4(),
            )

    def test_create_rejects_missing_locale(self):
        with pytest.raises(MissingRequiredLocalesError):
            Attribute.create(
                code="color",
                slug="color",
                name_i18n={"en": "Only English"},
                data_type=AttributeDataType.STRING,
                ui_type=AttributeUIType.DROPDOWN,
                is_dictionary=True,
                group_id=uuid.uuid4(),
            )

    def test_create_rejects_blank_i18n_values(self):
        with pytest.raises(ValueError):
            Attribute.create(
                code="color",
                slug="color",
                name_i18n={"en": "", "ru": "Valid"},
                data_type=AttributeDataType.STRING,
                ui_type=AttributeUIType.DROPDOWN,
                is_dictionary=True,
                group_id=uuid.uuid4(),
            )

    def test_create_rejects_invalid_validation_rules_for_type(self):
        with pytest.raises(ValueError):
            Attribute.create(
                code="size",
                slug="size",
                name_i18n=_i18n("Size"),
                data_type=AttributeDataType.STRING,
                ui_type=AttributeUIType.DROPDOWN,
                is_dictionary=True,
                group_id=uuid.uuid4(),
                validation_rules={"min_value": 0},
            )


# ============================================================================
# Attribute -- update
# ============================================================================


class TestAttributeUpdate:
    def test_update_name_i18n(self):
        attr = AttributeBuilder().build()
        attr.update(name_i18n=_i18n("New Name"))
        assert attr.name_i18n == _i18n("New Name")

    def test_update_ui_type(self):
        attr = AttributeBuilder().build()
        attr.update(ui_type=AttributeUIType.COLOR_SWATCH)
        assert attr.ui_type == AttributeUIType.COLOR_SWATCH

    def test_update_level(self):
        attr = AttributeBuilder().build()
        attr.update(level=AttributeLevel.VARIANT)
        assert attr.level == AttributeLevel.VARIANT

    def test_update_group_id(self):
        attr = AttributeBuilder().build()
        new_group = uuid.uuid4()
        attr.update(group_id=new_group)
        assert attr.group_id == new_group

    def test_update_group_id_to_none(self):
        attr = AttributeBuilder().build()
        attr.update(group_id=None)
        assert attr.group_id is None

    def test_update_behavior_via_object(self):
        attr = AttributeBuilder().build()
        attr.update(behavior=BehaviorFlags(is_filterable=True))
        assert attr.behavior.is_filterable is True

    def test_update_behavior_via_individual_flags(self):
        attr = AttributeBuilder().build()
        attr.update(is_filterable=True, search_weight=7)
        assert attr.is_filterable is True
        assert attr.search_weight == 7

    def test_update_validation_rules(self):
        attr = AttributeBuilder().with_data_type(AttributeDataType.STRING).build()
        attr.update(validation_rules={"min_length": 5})
        assert attr.validation_rules == {"min_length": 5}

    def test_update_rejects_unknown_field(self):
        attr = AttributeBuilder().build()
        with pytest.raises(TypeError):
            attr.update(unknown="x")

    def test_update_rejects_search_weight_below_min(self):
        attr = AttributeBuilder().build()
        with pytest.raises(ValueError):
            attr.update(search_weight=0)

    def test_update_rejects_search_weight_above_max(self):
        attr = AttributeBuilder().build()
        with pytest.raises(ValueError):
            attr.update(search_weight=11)


# ============================================================================
# Attribute -- __setattr__ guard
# ============================================================================


class TestAttributeGuard:
    def test_direct_code_assignment_raises(self):
        attr = AttributeBuilder().build()
        with pytest.raises(AttributeError, match="Cannot set 'code' directly"):
            attr.code = "new-code"

    def test_direct_slug_assignment_raises(self):
        attr = AttributeBuilder().build()
        with pytest.raises(AttributeError, match="Cannot set 'slug' directly"):
            attr.slug = "new-slug"


# ============================================================================
# Attribute -- behavior property delegation
# ============================================================================


class TestAttributeProperties:
    def test_is_filterable_delegates_to_behavior(self):
        attr = (
            AttributeBuilder().with_behavior(BehaviorFlags(is_filterable=True)).build()
        )
        assert attr.is_filterable is True

    def test_is_searchable_delegates(self):
        attr = (
            AttributeBuilder().with_behavior(BehaviorFlags(is_searchable=True)).build()
        )
        assert attr.is_searchable is True

    def test_search_weight_delegates(self):
        attr = AttributeBuilder().with_behavior(BehaviorFlags(search_weight=8)).build()
        assert attr.search_weight == 8

    def test_is_comparable_delegates(self):
        attr = (
            AttributeBuilder().with_behavior(BehaviorFlags(is_comparable=True)).build()
        )
        assert attr.is_comparable is True

    def test_is_visible_on_card_delegates(self):
        attr = (
            AttributeBuilder()
            .with_behavior(BehaviorFlags(is_visible_on_card=True))
            .build()
        )
        assert attr.is_visible_on_card is True


# ============================================================================
# AttributeValue -- create
# ============================================================================


class TestAttributeValueCreate:
    def test_create_valid(self):
        val = AttributeValueBuilder().build()
        assert isinstance(val.id, uuid.UUID)

    def test_create_rejects_missing_locale(self):
        with pytest.raises(MissingRequiredLocalesError):
            AttributeValue.create(
                attribute_id=uuid.uuid4(),
                code="red",
                slug="red",
                value_i18n={"en": "Red"},
            )

    def test_create_rejects_blank_i18n_values(self):
        with pytest.raises(ValueError):
            AttributeValue.create(
                attribute_id=uuid.uuid4(),
                code="red",
                slug="red",
                value_i18n={"en": "", "ru": "Valid"},
            )

    def test_create_rejects_invalid_slug(self):
        with pytest.raises(ValueError):
            AttributeValue.create(
                attribute_id=uuid.uuid4(),
                code="red",
                slug="Bad Slug!",
                value_i18n=_i18n("Red"),
            )

    def test_create_rejects_negative_sort_order(self):
        with pytest.raises(ValueError, match="sort_order must be non-negative"):
            AttributeValue.create(
                attribute_id=uuid.uuid4(),
                code="red",
                slug="red",
                value_i18n=_i18n("Red"),
                sort_order=-1,
            )

    def test_create_defaults(self):
        val = AttributeValueBuilder().build()
        assert val.is_active is True
        assert val.sort_order == 0
        assert val.search_aliases == []
        assert val.meta_data == {}

    def test_create_with_optional_fields(self):
        val = AttributeValue.create(
            attribute_id=uuid.uuid4(),
            code="red",
            slug="red",
            value_i18n=_i18n("Red"),
            search_aliases=["scarlet"],
            meta_data={"hex": "#FF0000"},
            value_group="warm",
        )
        assert val.search_aliases == ["scarlet"]
        assert val.meta_data == {"hex": "#FF0000"}
        assert val.value_group == "warm"


# ============================================================================
# AttributeValue -- update
# ============================================================================


class TestAttributeValueUpdate:
    def test_update_value_i18n(self):
        val = AttributeValueBuilder().build()
        val.update(value_i18n=_i18n("Blue"))
        assert val.value_i18n == _i18n("Blue")

    def test_update_sort_order(self):
        val = AttributeValueBuilder().build()
        val.update(sort_order=5)
        assert val.sort_order == 5

    def test_update_is_active(self):
        val = AttributeValueBuilder().build()
        val.update(is_active=False)
        assert val.is_active is False

    def test_update_search_aliases(self):
        val = AttributeValueBuilder().build()
        val.update(search_aliases=["crimson", "scarlet"])
        assert val.search_aliases == ["crimson", "scarlet"]

    def test_update_meta_data(self):
        val = AttributeValueBuilder().build()
        val.update(meta_data={"hex": "#FF0000"})
        assert val.meta_data == {"hex": "#FF0000"}

    def test_update_value_group(self):
        val = AttributeValueBuilder().build()
        val.update(value_group="warm")
        assert val.value_group == "warm"

    def test_update_value_group_to_none(self):
        val = AttributeValueBuilder().with_value_group("warm").build()
        val.update(value_group=None)
        assert val.value_group is None

    def test_update_rejects_unknown_field(self):
        val = AttributeValueBuilder().build()
        with pytest.raises(TypeError):
            val.update(unknown="x")


# ============================================================================
# ProductAttributeValue -- create
# ============================================================================


class TestProductAttributeValueCreate:
    def test_create_valid(self):
        pav = ProductAttributeValueBuilder().build()
        assert isinstance(pav.id, uuid.UUID)

    def test_create_has_correct_refs(self):
        product_id = uuid.uuid4()
        attribute_id = uuid.uuid4()
        attribute_value_id = uuid.uuid4()
        pav = (
            ProductAttributeValueBuilder()
            .with_product_id(product_id)
            .with_attribute_id(attribute_id)
            .with_attribute_value_id(attribute_value_id)
            .build()
        )
        assert pav.product_id == product_id
        assert pav.attribute_id == attribute_id
        assert pav.attribute_value_id == attribute_value_id
