"""Unit tests for catalog domain value objects.

Covers Money, BehaviorFlags, enums (MediaType, MediaRole,
AttributeDataType, AttributeUIType, AttributeLevel, RequirementLevel,
ProductStatus), i18n validation, slug regex, and validation rules.
Part of the unit test layer -- no I/O or infrastructure dependencies.
"""

import pytest
from attrs.exceptions import FrozenInstanceError

from src.modules.catalog.domain.exceptions import MissingRequiredLocalesError
from src.modules.catalog.domain.value_objects import (
    SLUG_RE,
    AttributeDataType,
    AttributeLevel,
    AttributeUIType,
    BehaviorFlags,
    MediaRole,
    MediaType,
    Money,
    ProductStatus,
    RequirementLevel,
    validate_i18n_completeness,
    validate_validation_rules,
)


class TestMoney:
    """Tests for the Money frozen value object."""

    def test_create_valid(self):
        m = Money(amount=1000, currency="RUB")
        assert m.amount == 1000
        assert m.currency == "RUB"

    def test_currency_uppercased(self):
        m = Money(amount=100, currency="rub")
        assert m.currency == "RUB"

    def test_rejects_negative_amount(self):
        with pytest.raises(ValueError, match="non-negative"):
            Money(amount=-1, currency="RUB")

    def test_zero_amount_allowed(self):
        m = Money(amount=0, currency="RUB")
        assert m.amount == 0

    def test_rejects_invalid_currency_length(self):
        with pytest.raises(ValueError, match="3-character"):
            Money(amount=100, currency="US")

    def test_rejects_long_currency(self):
        with pytest.raises(ValueError, match="3-character"):
            Money(amount=100, currency="USDX")

    def test_frozen_rejects_mutation(self):
        m = Money(amount=1000, currency="RUB")
        with pytest.raises(FrozenInstanceError):
            m.amount = 2000  # ty: ignore[invalid-assignment]

    def test_equality(self):
        assert Money(amount=100, currency="RUB") == Money(amount=100, currency="RUB")

    def test_inequality_different_amount(self):
        assert Money(amount=100, currency="RUB") != Money(amount=200, currency="RUB")

    def test_lt_same_currency(self):
        assert Money(amount=100, currency="RUB") < Money(amount=200, currency="RUB")

    def test_le_same_currency(self):
        assert Money(amount=100, currency="RUB") <= Money(amount=100, currency="RUB")

    def test_gt_same_currency(self):
        assert Money(amount=200, currency="RUB") > Money(amount=100, currency="RUB")

    def test_ge_same_currency(self):
        assert Money(amount=200, currency="RUB") >= Money(amount=200, currency="RUB")

    def test_comparison_different_currency_raises(self):
        with pytest.raises(ValueError, match="different currencies"):
            _ = Money(amount=100, currency="RUB") < Money(amount=200, currency="USD")

    def test_from_primitives_with_compare_at(self):
        price, compare = Money.from_primitives(1000, "RUB", compare_at_amount=2000)
        assert price.amount == 1000
        assert compare is not None
        assert compare.amount == 2000

    def test_from_primitives_without_compare_at(self):
        price, compare = Money.from_primitives(1000, "RUB")
        assert price.amount == 1000
        assert compare is None

    def test_from_primitives_rejects_compare_at_not_greater(self):
        with pytest.raises(ValueError, match="compare_at_price must be greater"):
            Money.from_primitives(1000, "RUB", compare_at_amount=500)

    def test_from_primitives_rejects_compare_at_equal(self):
        with pytest.raises(ValueError, match="compare_at_price must be greater"):
            Money.from_primitives(1000, "RUB", compare_at_amount=1000)


class TestBehaviorFlags:
    """Tests for the BehaviorFlags frozen value object."""

    def test_defaults(self):
        bf = BehaviorFlags()
        assert bf.is_filterable is False
        assert bf.is_searchable is False
        assert bf.search_weight == 5
        assert bf.is_comparable is False
        assert bf.is_visible_on_card is False

    def test_custom_values(self):
        bf = BehaviorFlags(is_filterable=True, search_weight=8)
        assert bf.is_filterable is True
        assert bf.search_weight == 8

    def test_frozen_rejects_mutation(self):
        bf = BehaviorFlags()
        with pytest.raises(FrozenInstanceError):
            bf.is_filterable = True  # ty: ignore[invalid-assignment]

    def test_search_weight_below_min_raises(self):
        with pytest.raises(ValueError, match="search_weight must be between"):
            BehaviorFlags(search_weight=0)

    def test_search_weight_above_max_raises(self):
        with pytest.raises(ValueError, match="search_weight must be between"):
            BehaviorFlags(search_weight=11)

    def test_search_weight_at_boundaries(self):
        low = BehaviorFlags(search_weight=1)
        high = BehaviorFlags(search_weight=10)
        assert low.search_weight == 1
        assert high.search_weight == 10


class TestValidateI18nCompleteness:
    """Tests for validate_i18n_completeness (REQUIRED_LOCALES = {"ru", "en"})."""

    def test_valid_both_locales(self):
        validate_i18n_completeness({"en": "Name", "ru": "Name"}, "test")

    def test_missing_ru_raises(self):
        with pytest.raises(MissingRequiredLocalesError):
            validate_i18n_completeness({"en": "Name"}, "test")

    def test_missing_en_raises(self):
        with pytest.raises(MissingRequiredLocalesError):
            validate_i18n_completeness({"ru": "Name"}, "test")

    def test_empty_dict_raises(self):
        with pytest.raises(MissingRequiredLocalesError):
            validate_i18n_completeness({}, "test")


class TestValidateValidationRules:
    """Tests for validate_validation_rules per data type."""

    def test_none_rules_passes(self):
        validate_validation_rules(AttributeDataType.STRING, None)

    def test_empty_dict_passes(self):
        validate_validation_rules(AttributeDataType.STRING, {})

    def test_string_valid_keys(self):
        validate_validation_rules(
            AttributeDataType.STRING, {"min_length": 1, "max_length": 100}
        )

    def test_string_invalid_keys_raises(self):
        with pytest.raises(ValueError):
            validate_validation_rules(AttributeDataType.STRING, {"min_value": 1})

    def test_numeric_valid_keys(self):
        validate_validation_rules(
            AttributeDataType.INTEGER, {"min_value": 0, "max_value": 100}
        )

    def test_numeric_invalid_keys_raises(self):
        with pytest.raises(ValueError):
            validate_validation_rules(AttributeDataType.INTEGER, {"min_length": 1})

    def test_boolean_rejects_all_keys(self):
        with pytest.raises(ValueError):
            validate_validation_rules(AttributeDataType.BOOLEAN, {"min_value": 0})

    def test_string_min_exceeds_max_raises(self):
        with pytest.raises(ValueError, match="min_length cannot exceed max_length"):
            validate_validation_rules(
                AttributeDataType.STRING, {"min_length": 100, "max_length": 10}
            )

    def test_numeric_min_exceeds_max_raises(self):
        with pytest.raises(ValueError, match="min_value cannot exceed max_value"):
            validate_validation_rules(
                AttributeDataType.INTEGER, {"min_value": 100, "max_value": 10}
            )


class TestSlugRegex:
    """Tests for the SLUG_RE compiled regex pattern."""

    def test_valid_simple_slug(self):
        assert SLUG_RE.match("nike") is not None

    def test_valid_slug_with_hyphens(self):
        assert SLUG_RE.match("nike-air-max") is not None

    def test_valid_slug_with_digits(self):
        assert SLUG_RE.match("product-123") is not None

    def test_rejects_uppercase(self):
        assert SLUG_RE.match("Nike") is None

    def test_rejects_spaces(self):
        assert SLUG_RE.match("nike air") is None

    def test_rejects_leading_hyphen(self):
        assert SLUG_RE.match("-nike") is None

    def test_rejects_trailing_hyphen(self):
        assert SLUG_RE.match("nike-") is None

    def test_rejects_empty(self):
        assert SLUG_RE.match("") is None

    def test_rejects_consecutive_hyphens(self):
        assert SLUG_RE.match("nike--air") is None


class TestEnums:
    """Tests for all StrEnum values in the domain layer."""

    def test_product_status_values(self):
        assert ProductStatus.DRAFT == "draft"
        assert ProductStatus.ENRICHING == "enriching"
        assert ProductStatus.READY_FOR_REVIEW == "ready_for_review"
        assert ProductStatus.PUBLISHED == "published"
        assert ProductStatus.ARCHIVED == "archived"

    def test_media_type_values(self):
        assert MediaType.IMAGE == "image"
        assert MediaType.VIDEO == "video"
        assert MediaType.MODEL_3D == "model_3d"
        assert MediaType.DOCUMENT == "document"

    def test_media_role_values(self):
        assert MediaRole.MAIN == "main"
        assert MediaRole.HOVER == "hover"
        assert MediaRole.GALLERY == "gallery"
        assert MediaRole.HERO_VIDEO == "hero_video"
        assert MediaRole.SIZE_GUIDE == "size_guide"
        assert MediaRole.PACKAGING == "packaging"

    def test_attribute_data_type_values(self):
        assert AttributeDataType.STRING == "string"
        assert AttributeDataType.INTEGER == "integer"
        assert AttributeDataType.FLOAT == "float"
        assert AttributeDataType.BOOLEAN == "boolean"

    def test_attribute_ui_type_values(self):
        assert AttributeUIType.TEXT_BUTTON == "text_button"
        assert AttributeUIType.COLOR_SWATCH == "color_swatch"
        assert AttributeUIType.DROPDOWN == "dropdown"
        assert AttributeUIType.CHECKBOX == "checkbox"
        assert AttributeUIType.RANGE_SLIDER == "range_slider"

    def test_attribute_level_values(self):
        assert AttributeLevel.PRODUCT == "product"
        assert AttributeLevel.VARIANT == "variant"

    def test_requirement_level_values(self):
        assert RequirementLevel.REQUIRED == "required"
        assert RequirementLevel.RECOMMENDED == "recommended"
        assert RequirementLevel.OPTIONAL == "optional"
