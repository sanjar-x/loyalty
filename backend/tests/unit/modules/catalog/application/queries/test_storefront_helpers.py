# tests/unit/modules/catalog/application/queries/test_storefront_helpers.py
"""Tests for storefront query helper functions -- flag override resolution."""

import uuid

from src.modules.catalog.application.queries.storefront import (
    _effective_bool,
    _effective_display_type,
    _null_group,
)

# ---------------------------------------------------------------------------
# _effective_bool -- flag override resolution
# ---------------------------------------------------------------------------


class TestEffectiveBool:
    """Test the COALESCE-like logic for behavior flag resolution."""

    def test_no_overrides_returns_global_true(self):
        assert _effective_bool(None, "is_filterable", True) is True

    def test_no_overrides_returns_global_false(self):
        assert _effective_bool(None, "is_filterable", False) is False

    def test_empty_overrides_returns_global(self):
        assert _effective_bool({}, "is_filterable", True) is True
        assert _effective_bool({}, "is_filterable", False) is False

    def test_override_true_overrides_global_false(self):
        overrides = {"is_filterable": True}
        assert _effective_bool(overrides, "is_filterable", False) is True

    def test_override_false_overrides_global_true(self):
        overrides = {"is_filterable": False}
        assert _effective_bool(overrides, "is_filterable", True) is False

    def test_override_for_different_flag_does_not_affect(self):
        overrides = {"is_comparable": True}
        assert _effective_bool(overrides, "is_filterable", False) is False

    def test_override_truthy_int_is_converted_to_bool(self):
        overrides = {"is_searchable": 1}
        assert _effective_bool(overrides, "is_searchable", False) is True

    def test_override_falsy_zero_is_converted_to_bool(self):
        overrides = {"is_searchable": 0}
        assert _effective_bool(overrides, "is_searchable", True) is False

    def test_multiple_flags_in_overrides(self):
        overrides = {
            "is_filterable": True,
            "is_comparable": False,
            "is_visible_on_card": True,
        }
        assert _effective_bool(overrides, "is_filterable", False) is True
        assert _effective_bool(overrides, "is_comparable", True) is False
        assert _effective_bool(overrides, "is_visible_on_card", False) is True
        # Not overridden -- falls back to global
        assert _effective_bool(overrides, "is_searchable", True) is True


# ---------------------------------------------------------------------------
# _effective_display_type -- filter type resolution
# ---------------------------------------------------------------------------


class TestEffectiveDisplayType:
    """Test the filter type override resolution."""

    def test_no_settings_returns_global(self):
        assert _effective_display_type(None, "text_button") == "text_button"

    def test_empty_settings_returns_global(self):
        assert _effective_display_type({}, "dropdown") == "dropdown"

    def test_settings_without_filter_type_returns_global(self):
        settings = {"thresholds": [0, 5000, 10000]}
        assert _effective_display_type(settings, "checkbox") == "checkbox"

    def test_settings_with_filter_type_overrides(self):
        settings = {"filter_type": "range", "thresholds": [0, 5000]}
        assert _effective_display_type(settings, "text_button") == "range"

    def test_settings_with_dropdown_filter_type(self):
        settings = {"filter_type": "dropdown"}
        assert _effective_display_type(settings, "range_slider") == "dropdown"


# ---------------------------------------------------------------------------
# _null_group -- sentinel for unassigned groups
# ---------------------------------------------------------------------------


class TestNullGroup:
    """Test the null group sentinel used for ungrouped attributes."""

    def test_null_group_sort_order_is_high(self):
        ng = _null_group()
        assert ng.sort_order == 999_999

    def test_null_group_code_is_none(self):
        ng = _null_group()
        assert ng.code is None

    def test_null_group_name_i18n_is_empty(self):
        ng = _null_group()
        assert ng.name_i18n == {}


# ---------------------------------------------------------------------------
# Storefront read model structure tests
# ---------------------------------------------------------------------------


class TestStorefrontReadModels:
    """Verify read model structures can be instantiated correctly."""

    def test_filter_attribute_model(self):
        from src.modules.catalog.application.queries.read_models import (
            StorefrontFilterAttributeReadModel,
            StorefrontValueReadModel,
        )

        val = StorefrontValueReadModel(
            id=uuid.uuid4(),
            code="red",
            slug="red",
            value_i18n={"en": "Red"},
            meta_data={"hex": "#FF0000"},
            value_group="Warm",
            sort_order=0,
        )
        attr = StorefrontFilterAttributeReadModel(
            attribute_id=uuid.uuid4(),
            code="color",
            slug="color",
            name_i18n={"en": "Color"},
            data_type="string",
            display_type="color_swatch",
            is_dictionary=True,
            values=[val],
            filter_settings=None,
            sort_order=0,
        )
        assert attr.is_dictionary is True
        assert len(attr.values) == 1
        assert attr.values[0].code == "red"

    def test_card_group_model(self):
        from src.modules.catalog.application.queries.read_models import (
            StorefrontCardAttributeReadModel,
            StorefrontCardGroupReadModel,
        )

        attr = StorefrontCardAttributeReadModel(
            attribute_id=uuid.uuid4(),
            code="material",
            slug="material",
            name_i18n={"en": "Material"},
            data_type="string",
            display_type="text_button",
            requirement_level="recommended",
            sort_order=0,
        )
        group = StorefrontCardGroupReadModel(
            group_id=uuid.uuid4(),
            group_code="physical",
            group_name_i18n={"en": "Physical"},
            group_sort_order=1,
            attributes=[attr],
        )
        assert group.group_code == "physical"
        assert len(group.attributes) == 1

    def test_form_attribute_model_with_validation_and_values(self):
        from src.modules.catalog.application.queries.read_models import (
            StorefrontFormAttributeReadModel,
            StorefrontValueReadModel,
        )

        val = StorefrontValueReadModel(
            id=uuid.uuid4(),
            code="xl",
            slug="xl",
            value_i18n={"en": "XL"},
            meta_data={},
            sort_order=0,
        )
        attr = StorefrontFormAttributeReadModel(
            attribute_id=uuid.uuid4(),
            code="size",
            slug="size",
            name_i18n={"en": "Size"},
            description_i18n={"en": "Choose a size"},
            data_type="string",
            display_type="text_button",
            is_dictionary=True,
            level="variant",
            requirement_level="required",
            validation_rules={"min_length": 1},
            values=[val],
            sort_order=0,
        )
        assert attr.requirement_level == "required"
        assert attr.validation_rules == {"min_length": 1}
        assert len(attr.values) == 1

    def test_comparison_model(self):
        from src.modules.catalog.application.queries.read_models import (
            StorefrontComparisonAttributeReadModel,
            StorefrontComparisonReadModel,
        )

        cat_id = uuid.uuid4()
        attr = StorefrontComparisonAttributeReadModel(
            attribute_id=uuid.uuid4(),
            code="screen_size",
            slug="screen-size",
            name_i18n={"en": "Screen Size"},
            data_type="float",
            display_type="range_slider",
            sort_order=0,
        )
        model = StorefrontComparisonReadModel(
            category_id=cat_id,
            attributes=[attr],
        )
        assert model.category_id == cat_id
        assert len(model.attributes) == 1

    def test_filter_list_model_empty(self):
        from src.modules.catalog.application.queries.read_models import (
            StorefrontFilterListReadModel,
        )

        cat_id = uuid.uuid4()
        model = StorefrontFilterListReadModel(category_id=cat_id, attributes=[])
        assert model.category_id == cat_id
        assert model.attributes == []
