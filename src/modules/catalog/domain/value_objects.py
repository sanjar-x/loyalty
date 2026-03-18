"""
Catalog domain value objects.

Contains immutable types that represent domain concepts without
identity. Part of the domain layer -- zero infrastructure imports.
"""

import enum
from typing import Any

DEFAULT_SEARCH_WEIGHT = 5
"""Default search weight for new attributes."""

MIN_SEARCH_WEIGHT = 1
MAX_SEARCH_WEIGHT = 10


class MediaProcessingStatus(str, enum.Enum):
    """Finite state machine (FSM) for media file processing lifecycle.

    Describes exclusively the business states of a media file's lifecycle,
    independent of any infrastructure details.

    States:
        PENDING_UPLOAD: Awaiting the client to upload the original file.
        PROCESSING: File uploaded; background processing in progress.
        COMPLETED: Processing finished; media is ready for use.
        FAILED: Processing failed (corrupted file or unsupported format).
    """

    PENDING_UPLOAD = "PENDING_UPLOAD"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class AttributeDataType(str, enum.Enum):
    """Allowed primitive types for catalog attribute values.

    Determines how attribute values are stored, validated, and
    compared in the domain layer.

    Members:
        STRING: Free-text or enumerated string values.
        INTEGER: Whole number values (e.g. weight in grams).
        FLOAT: Decimal number values (e.g. screen size in inches).
        BOOLEAN: True/false flag values (e.g. "is waterproof").
    """

    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"


class AttributeUIType(str, enum.Enum):
    """Widget hints for rendering an attribute filter on the storefront.

    Used by the presentation layer to select the appropriate UI component
    when displaying attribute filters to end users.

    Members:
        TEXT_BUTTON: Clickable text labels (e.g. size buttons).
        COLOR_SWATCH: Colour circles/squares with hex fill.
        DROPDOWN: Single-select dropdown menu.
        CHECKBOX: Multi-select checkboxes.
        RANGE_SLIDER: Numeric range slider (min/max).
    """

    TEXT_BUTTON = "text_button"
    COLOR_SWATCH = "color_swatch"
    DROPDOWN = "dropdown"
    CHECKBOX = "checkbox"
    RANGE_SLIDER = "range_slider"


class AttributeLevel(str, enum.Enum):
    """Scope at which an attribute applies.

    Determines whether the attribute value is shared by all SKUs of a
    product or varies per individual SKU variant.

    Members:
        PRODUCT: Same value for all variants (e.g. brand, description).
        VARIANT: Different value per SKU (e.g. colour, size).
    """

    PRODUCT = "product"
    VARIANT = "variant"


# ---------------------------------------------------------------------------
# Validation rules -- pure domain helpers
# ---------------------------------------------------------------------------

# Keys allowed per data type
_STRING_RULE_KEYS = {"min_length", "max_length", "pattern"}
_NUMERIC_RULE_KEYS = {"min_value", "max_value"}
_DATE_RULE_KEYS = {"min_date", "max_date"}
_BOOLEAN_RULE_KEYS: set[str] = set()  # no rules for booleans


def validate_validation_rules(
    data_type: AttributeDataType,
    rules: dict[str, Any] | None,
) -> None:
    """Verify that *rules* only contain keys valid for the given *data_type*.

    Args:
        data_type: The attribute's data type.
        rules: Validation rules dict, or None (no rules).

    Raises:
        ValueError: If *rules* contains keys not allowed for *data_type*.
    """
    if not rules:
        return

    allowed: set[str]
    if data_type == AttributeDataType.STRING:
        allowed = _STRING_RULE_KEYS
    elif data_type in (AttributeDataType.INTEGER, AttributeDataType.FLOAT):
        allowed = _NUMERIC_RULE_KEYS
    elif data_type == AttributeDataType.BOOLEAN:
        allowed = _BOOLEAN_RULE_KEYS
    else:
        allowed = set()

    invalid_keys = set(rules.keys()) - allowed
    if invalid_keys:
        raise ValueError(
            f"Validation rules {invalid_keys} are not valid for data type '{data_type.value}'. "
            f"Allowed keys: {allowed or 'none'}"
        )

    # Type-specific value checks
    if data_type == AttributeDataType.STRING:
        _validate_string_rules(rules)
    elif data_type in (AttributeDataType.INTEGER, AttributeDataType.FLOAT):
        _validate_numeric_rules(rules)


def _validate_string_rules(rules: dict[str, Any]) -> None:
    """Validate string-specific rule values."""
    min_len = rules.get("min_length")
    max_len = rules.get("max_length")
    if min_len is not None and not isinstance(min_len, int):
        raise ValueError("min_length must be an integer")
    if max_len is not None and not isinstance(max_len, int):
        raise ValueError("max_length must be an integer")
    if min_len is not None and min_len < 0:
        raise ValueError("min_length must be non-negative")
    if max_len is not None and max_len < 0:
        raise ValueError("max_length must be non-negative")
    if min_len is not None and max_len is not None and min_len > max_len:
        raise ValueError("min_length cannot exceed max_length")


def _validate_numeric_rules(rules: dict[str, Any]) -> None:
    """Validate numeric-specific rule values."""
    min_val = rules.get("min_value")
    max_val = rules.get("max_value")
    if min_val is not None and not isinstance(min_val, int | float):
        raise ValueError("min_value must be a number")
    if max_val is not None and not isinstance(max_val, int | float):
        raise ValueError("max_value must be a number")
    if min_val is not None and max_val is not None and min_val > max_val:
        raise ValueError("min_value cannot exceed max_value")
