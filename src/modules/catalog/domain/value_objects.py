"""
Catalog domain value objects.

Contains immutable types that represent domain concepts without
identity. Part of the domain layer -- zero infrastructure imports.
"""

import enum
from typing import Any

from attrs import frozen

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


class RequirementLevel(str, enum.Enum):
    """How mandatory an attribute is within a specific category.

    Used by category-attribute bindings to indicate whether the
    attribute must be filled, is recommended, or entirely optional.

    Members:
        REQUIRED: Attribute must have a value; blocks completeness.
        RECOMMENDED: Attribute is desired; affects completeness score.
        OPTIONAL: Attribute is available but does not affect completeness.
    """

    REQUIRED = "required"
    RECOMMENDED = "recommended"
    OPTIONAL = "optional"


class ProductStatus(str, enum.Enum):
    """Lifecycle states for a product listing.

    Describes the FSM transitions a product passes through from
    initial creation to publication and eventual archival. The allowed
    transitions are enforced by the Product aggregate root (MT-2):

        DRAFT -> ENRICHING
        ENRICHING -> DRAFT
        ENRICHING -> READY_FOR_REVIEW
        READY_FOR_REVIEW -> ENRICHING
        READY_FOR_REVIEW -> PUBLISHED
        PUBLISHED -> ARCHIVED
        ARCHIVED -> DRAFT

    Values use lowercase strings matching the ORM ProductStatus enum
    (see infrastructure/models.py) to enable simple string-based
    mapping in repositories without a translation table.

    Members:
        DRAFT: Initial state; product data is incomplete.
        ENRICHING: Content team is actively filling in attributes.
        READY_FOR_REVIEW: Content is complete; awaiting approval.
        PUBLISHED: Product is live on the storefront.
        ARCHIVED: Product has been taken off sale.
    """

    DRAFT = "draft"
    ENRICHING = "enriching"
    READY_FOR_REVIEW = "ready_for_review"
    PUBLISHED = "published"
    ARCHIVED = "archived"


# Context7: verified @frozen does not generate order methods by default in attrs.
# Custom __lt__/__le__/__gt__/__ge__ are therefore safe to define without conflict.
# Context7: verified __attrs_post_init__ in @frozen classes must only READ fields,
# never assign -- our validation only reads self.amount and self.currency, so safe.
@frozen
class Money:
    """Immutable value object representing a monetary amount.

    Stores the amount in the smallest currency units (e.g. kopecks for RUB,
    cents for USD) to avoid floating-point rounding errors. Currency is
    validated to be exactly 3 characters per ISO 4217; full whitelist
    validation is deferred to the presentation layer.

    Ordering comparisons are only meaningful within the same currency.
    Comparing instances with different currencies raises ``ValueError``
    to prevent silent currency confusion.

    Attributes:
        amount: Non-negative integer in smallest currency units (e.g. kopecks).
        currency: 3-character ISO 4217 currency code (e.g. "RUB", "USD").

    Raises:
        ValueError: If ``amount`` is negative at construction time.
        ValueError: If ``currency`` is not exactly 3 characters at construction time.
        ValueError: If ordering comparison is attempted between instances with
            different ``currency`` values.
    """

    amount: int
    currency: str

    def __attrs_post_init__(self) -> None:
        """Validate field values after attrs-generated __init__ runs."""
        if self.amount < 0:
            raise ValueError("Money amount must be non-negative")
        if len(self.currency) != 3:
            raise ValueError("Currency must be a 3-character ISO code")

    def _check_currency(self, other: Money) -> None:
        """Assert both instances share the same currency.

        Args:
            other: The Money instance being compared against.

        Raises:
            ValueError: If ``self.currency != other.currency``.
        """
        if self.currency != other.currency:
            raise ValueError(
                f"Cannot compare Money with different currencies: "
                f"{self.currency} vs {other.currency}"
            )

    def __lt__(self, other: Money) -> bool:
        """Return True if this amount is strictly less than *other*.

        Args:
            other: Money instance to compare against (must share currency).

        Returns:
            True if ``self.amount < other.amount``.

        Raises:
            ValueError: If currencies differ.
        """
        self._check_currency(other)
        return self.amount < other.amount

    def __le__(self, other: Money) -> bool:
        """Return True if this amount is less than or equal to *other*.

        Args:
            other: Money instance to compare against (must share currency).

        Returns:
            True if ``self.amount <= other.amount``.

        Raises:
            ValueError: If currencies differ.
        """
        self._check_currency(other)
        return self.amount <= other.amount

    def __gt__(self, other: Money) -> bool:
        """Return True if this amount is strictly greater than *other*.

        Args:
            other: Money instance to compare against (must share currency).

        Returns:
            True if ``self.amount > other.amount``.

        Raises:
            ValueError: If currencies differ.
        """
        self._check_currency(other)
        return self.amount > other.amount

    def __ge__(self, other: Money) -> bool:
        """Return True if this amount is greater than or equal to *other*.

        Args:
            other: Money instance to compare against (must share currency).

        Returns:
            True if ``self.amount >= other.amount``.

        Raises:
            ValueError: If currencies differ.
        """
        self._check_currency(other)
        return self.amount >= other.amount
