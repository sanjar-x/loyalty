# tests/unit/modules/catalog/domain/test_attribute.py
"""Tests for Attribute domain entity, value objects, events, and exceptions."""

import uuid

import pytest

from src.modules.catalog.domain.entities import Attribute
from src.modules.catalog.domain.events import (
    AttributeCreatedEvent,
    AttributeDeletedEvent,
    AttributeUpdatedEvent,
)
from src.modules.catalog.domain.exceptions import (
    AttributeCodeConflictError,
    AttributeDataTypeChangeError,
    AttributeHasCategoryBindingsError,
    AttributeNotFoundError,
    AttributeSlugConflictError,
)
from src.modules.catalog.domain.value_objects import (
    DEFAULT_SEARCH_WEIGHT,
    MAX_SEARCH_WEIGHT,
    MIN_SEARCH_WEIGHT,
    AttributeDataType,
    AttributeLevel,
    AttributeUIType,
    validate_validation_rules,
)


def _make_group_id() -> uuid.UUID:
    return uuid.uuid4()


def _make_attribute(**overrides) -> Attribute:
    defaults = {
        "code": "color",
        "slug": "color",
        "name_i18n": {"en": "Color", "ru": "Цвет"},
        "data_type": AttributeDataType.STRING,
        "ui_type": AttributeUIType.COLOR_SWATCH,
        "is_dictionary": True,
        "group_id": _make_group_id(),
    }
    defaults.update(overrides)
    return Attribute.create(**defaults)


# ---------------------------------------------------------------------------
# Attribute entity -- creation
# ---------------------------------------------------------------------------


class TestAttributeCreate:
    def test_create_sets_all_fields(self):
        gid = _make_group_id()
        attr = Attribute.create(
            code="screen_size",
            slug="screen-size",
            name_i18n={"en": "Screen Size"},
            data_type=AttributeDataType.FLOAT,
            ui_type=AttributeUIType.RANGE_SLIDER,
            is_dictionary=False,
            group_id=gid,
            description_i18n={"en": "Measured in inches"},
            level=AttributeLevel.PRODUCT,
            is_filterable=True,
            is_searchable=False,
            search_weight=3,
            is_comparable=True,
            is_visible_on_card=True,
            is_visible_in_catalog=False,
            validation_rules={"min_value": 1.0, "max_value": 100.0},
        )
        assert attr.code == "screen_size"
        assert attr.slug == "screen-size"
        assert attr.name_i18n == {"en": "Screen Size"}
        assert attr.data_type == AttributeDataType.FLOAT
        assert attr.ui_type == AttributeUIType.RANGE_SLIDER
        assert attr.is_dictionary is False
        assert attr.group_id == gid
        assert attr.description_i18n == {"en": "Measured in inches"}
        assert attr.level == AttributeLevel.PRODUCT
        assert attr.is_filterable is True
        assert attr.is_searchable is False
        assert attr.search_weight == 3
        assert attr.is_comparable is True
        assert attr.is_visible_on_card is True
        assert attr.is_visible_in_catalog is False
        assert attr.validation_rules == {"min_value": 1.0, "max_value": 100.0}
        assert isinstance(attr.id, uuid.UUID)

    def test_create_with_defaults(self):
        attr = _make_attribute()
        assert attr.level == AttributeLevel.PRODUCT
        assert attr.is_filterable is False
        assert attr.is_searchable is False
        assert attr.search_weight == DEFAULT_SEARCH_WEIGHT
        assert attr.is_comparable is False
        assert attr.is_visible_on_card is False
        assert attr.is_visible_in_catalog is False
        assert attr.validation_rules is None
        assert attr.description_i18n == {}

    def test_create_with_custom_id(self):
        custom_id = uuid.uuid4()
        attr = _make_attribute(attribute_id=custom_id)
        assert attr.id == custom_id

    def test_create_raises_on_empty_name_i18n(self):
        with pytest.raises(ValueError, match="name_i18n must contain at least one language"):
            _make_attribute(name_i18n={})

    def test_create_raises_on_search_weight_below_min(self):
        with pytest.raises(ValueError, match="search_weight must be between"):
            _make_attribute(search_weight=0)

    def test_create_raises_on_search_weight_above_max(self):
        with pytest.raises(ValueError, match="search_weight must be between"):
            _make_attribute(search_weight=11)

    def test_create_accepts_boundary_search_weights(self):
        attr_min = _make_attribute(search_weight=MIN_SEARCH_WEIGHT)
        assert attr_min.search_weight == 1
        attr_max = _make_attribute(search_weight=MAX_SEARCH_WEIGHT)
        assert attr_max.search_weight == 10

    def test_create_raises_on_invalid_validation_rules(self):
        with pytest.raises(ValueError, match="not valid for data type"):
            _make_attribute(
                data_type=AttributeDataType.STRING,
                validation_rules={"min_value": 0},  # numeric rule for string type
            )

    def test_create_accepts_valid_string_validation_rules(self):
        attr = _make_attribute(
            data_type=AttributeDataType.STRING,
            validation_rules={
                "min_length": 1,
                "max_length": 100,
                "pattern": r"^[A-Z].*",
            },
        )
        assert attr.validation_rules == {
            "min_length": 1,
            "max_length": 100,
            "pattern": r"^[A-Z].*",
        }

    def test_create_accepts_valid_numeric_validation_rules(self):
        attr = _make_attribute(
            data_type=AttributeDataType.INTEGER,
            validation_rules={"min_value": 0, "max_value": 1000},
        )
        assert attr.validation_rules == {"min_value": 0, "max_value": 1000}

    def test_create_variant_level(self):
        attr = _make_attribute(level=AttributeLevel.VARIANT)
        assert attr.level == AttributeLevel.VARIANT


# ---------------------------------------------------------------------------
# Attribute entity -- update
# ---------------------------------------------------------------------------


class TestAttributeUpdate:
    def test_update_name(self):
        attr = _make_attribute()
        attr.update(name_i18n={"en": "Updated Color", "uz": "Rang"})
        assert attr.name_i18n == {"en": "Updated Color", "uz": "Rang"}

    def test_update_description(self):
        attr = _make_attribute()
        attr.update(description_i18n={"en": "New description"})
        assert attr.description_i18n == {"en": "New description"}

    def test_update_ui_type(self):
        attr = _make_attribute(ui_type=AttributeUIType.TEXT_BUTTON)
        attr.update(ui_type=AttributeUIType.DROPDOWN)
        assert attr.ui_type == AttributeUIType.DROPDOWN

    def test_update_group_id(self):
        attr = _make_attribute()
        new_gid = uuid.uuid4()
        attr.update(group_id=new_gid)
        assert attr.group_id == new_gid

    def test_update_level(self):
        attr = _make_attribute(level=AttributeLevel.PRODUCT)
        attr.update(level=AttributeLevel.VARIANT)
        assert attr.level == AttributeLevel.VARIANT

    def test_update_behavior_flags(self):
        attr = _make_attribute()
        attr.update(
            is_filterable=True,
            is_searchable=True,
            search_weight=8,
            is_comparable=True,
            is_visible_on_card=True,
            is_visible_in_catalog=True,
        )
        assert attr.is_filterable is True
        assert attr.is_searchable is True
        assert attr.search_weight == 8
        assert attr.is_comparable is True
        assert attr.is_visible_on_card is True
        assert attr.is_visible_in_catalog is True

    def test_update_with_none_keeps_current(self):
        attr = _make_attribute()
        original_name = attr.name_i18n.copy()
        original_ui = attr.ui_type
        attr.update()  # all defaults (None or sentinel)
        assert attr.name_i18n == original_name
        assert attr.ui_type == original_ui

    def test_update_raises_on_empty_name_i18n(self):
        attr = _make_attribute()
        with pytest.raises(ValueError, match="name_i18n must contain at least one language"):
            attr.update(name_i18n={})

    def test_update_raises_on_invalid_search_weight(self):
        attr = _make_attribute()
        with pytest.raises(ValueError, match="search_weight must be between"):
            attr.update(search_weight=0)

    def test_update_validation_rules_set(self):
        attr = _make_attribute(data_type=AttributeDataType.STRING)
        attr.update(validation_rules={"min_length": 5})
        assert attr.validation_rules == {"min_length": 5}

    def test_update_validation_rules_clear(self):
        attr = _make_attribute(
            data_type=AttributeDataType.STRING,
            validation_rules={"min_length": 5},
        )
        attr.update(validation_rules=None)
        assert attr.validation_rules is None

    def test_update_validation_rules_invalid_for_type(self):
        attr = _make_attribute(data_type=AttributeDataType.STRING)
        with pytest.raises(ValueError, match="not valid for data type"):
            attr.update(validation_rules={"min_value": 0})

    def test_code_slug_data_type_not_in_update_signature(self):
        """Verify that code, slug, and data_type cannot be passed to update()."""
        attr = _make_attribute()
        # These should raise TypeError since they are not parameters
        with pytest.raises(TypeError):
            attr.update(code="new_code")  # type: ignore[call-arg]
        with pytest.raises(TypeError):
            attr.update(slug="new-slug")  # type: ignore[call-arg]
        with pytest.raises(TypeError):
            attr.update(data_type=AttributeDataType.INTEGER)  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# Value objects -- AttributeLevel enum
# ---------------------------------------------------------------------------


class TestAttributeLevel:
    def test_product_value(self):
        assert AttributeLevel.PRODUCT.value == "product"

    def test_variant_value(self):
        assert AttributeLevel.VARIANT.value == "variant"


# ---------------------------------------------------------------------------
# Value objects -- validate_validation_rules
# ---------------------------------------------------------------------------


class TestValidateValidationRules:
    def test_none_rules_pass(self):
        validate_validation_rules(AttributeDataType.STRING, None)

    def test_empty_rules_pass(self):
        validate_validation_rules(AttributeDataType.STRING, {})

    def test_valid_string_rules(self):
        validate_validation_rules(
            AttributeDataType.STRING,
            {"min_length": 1, "max_length": 100, "pattern": r".*"},
        )

    def test_valid_integer_rules(self):
        validate_validation_rules(AttributeDataType.INTEGER, {"min_value": 0, "max_value": 999})

    def test_valid_float_rules(self):
        validate_validation_rules(AttributeDataType.FLOAT, {"min_value": 0.0, "max_value": 99.9})

    def test_boolean_rejects_all_keys(self):
        with pytest.raises(ValueError, match="not valid for data type"):
            validate_validation_rules(AttributeDataType.BOOLEAN, {"min_value": 0})

    def test_string_rejects_numeric_keys(self):
        with pytest.raises(ValueError, match="not valid for data type"):
            validate_validation_rules(AttributeDataType.STRING, {"min_value": 0})

    def test_numeric_rejects_string_keys(self):
        with pytest.raises(ValueError, match="not valid for data type"):
            validate_validation_rules(AttributeDataType.INTEGER, {"min_length": 1})

    def test_min_length_must_be_int(self):
        with pytest.raises(ValueError, match="min_length must be an integer"):
            validate_validation_rules(AttributeDataType.STRING, {"min_length": "abc"})

    def test_min_length_must_be_non_negative(self):
        with pytest.raises(ValueError, match="min_length must be non-negative"):
            validate_validation_rules(AttributeDataType.STRING, {"min_length": -1})

    def test_min_length_cannot_exceed_max_length(self):
        with pytest.raises(ValueError, match="min_length cannot exceed max_length"):
            validate_validation_rules(AttributeDataType.STRING, {"min_length": 10, "max_length": 5})

    def test_min_value_must_be_number(self):
        with pytest.raises(ValueError, match="min_value must be a number"):
            validate_validation_rules(AttributeDataType.INTEGER, {"min_value": "abc"})

    def test_min_value_cannot_exceed_max_value(self):
        with pytest.raises(ValueError, match="min_value cannot exceed max_value"):
            validate_validation_rules(
                AttributeDataType.INTEGER, {"min_value": 100, "max_value": 50}
            )


# ---------------------------------------------------------------------------
# Attribute domain events
# ---------------------------------------------------------------------------


class TestAttributeCreatedEvent:
    def test_raises_when_attribute_id_is_none(self):
        with pytest.raises(ValueError, match="attribute_id is required"):
            AttributeCreatedEvent(attribute_id=None, code="test")

    def test_auto_sets_aggregate_id(self):
        aid = uuid.uuid4()
        event = AttributeCreatedEvent(attribute_id=aid, code="test")
        assert event.aggregate_id == str(aid)

    def test_fields_populated(self):
        aid = uuid.uuid4()
        event = AttributeCreatedEvent(attribute_id=aid, code="color")
        assert event.aggregate_type == "Attribute"
        assert event.event_type == "AttributeCreatedEvent"
        assert event.code == "color"


class TestAttributeUpdatedEvent:
    def test_raises_when_attribute_id_is_none(self):
        with pytest.raises(ValueError, match="attribute_id is required"):
            AttributeUpdatedEvent(attribute_id=None)

    def test_auto_sets_aggregate_id(self):
        aid = uuid.uuid4()
        event = AttributeUpdatedEvent(attribute_id=aid)
        assert event.aggregate_id == str(aid)


class TestAttributeDeletedEvent:
    def test_raises_when_attribute_id_is_none(self):
        with pytest.raises(ValueError, match="attribute_id is required"):
            AttributeDeletedEvent(attribute_id=None, code="test")

    def test_fields_populated(self):
        aid = uuid.uuid4()
        event = AttributeDeletedEvent(attribute_id=aid, code="color")
        assert event.aggregate_type == "Attribute"
        assert event.event_type == "AttributeDeletedEvent"
        assert event.code == "color"


# ---------------------------------------------------------------------------
# Attribute domain exceptions
# ---------------------------------------------------------------------------


class TestAttributeExceptions:
    def test_not_found_error(self):
        aid = uuid.uuid4()
        error = AttributeNotFoundError(attribute_id=aid)
        assert error.status_code == 404
        assert error.error_code == "ATTRIBUTE_NOT_FOUND"
        assert str(aid) in error.message

    def test_code_conflict_error(self):
        error = AttributeCodeConflictError(code="color")
        assert error.status_code == 409
        assert error.error_code == "ATTRIBUTE_CODE_CONFLICT"
        assert "color" in error.message

    def test_slug_conflict_error(self):
        error = AttributeSlugConflictError(slug="color")
        assert error.status_code == 409
        assert error.error_code == "ATTRIBUTE_SLUG_CONFLICT"

    def test_has_category_bindings_error(self):
        aid = uuid.uuid4()
        error = AttributeHasCategoryBindingsError(attribute_id=aid)
        assert error.status_code == 409
        assert error.error_code == "ATTRIBUTE_HAS_CATEGORY_BINDINGS"

    def test_data_type_change_error(self):
        aid = uuid.uuid4()
        error = AttributeDataTypeChangeError(attribute_id=aid)
        assert error.status_code == 422
        assert error.error_code == "ATTRIBUTE_DATA_TYPE_CHANGE_NOT_ALLOWED"
