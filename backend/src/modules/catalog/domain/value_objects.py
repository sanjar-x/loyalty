"""
Catalog domain value objects.

Contains immutable types that represent domain concepts without
identity. Part of the domain layer -- zero infrastructure imports.
"""

import enum
import re
from typing import Any

from attrs import frozen

DEFAULT_CURRENCY = "RUB"
"""Default ISO 4217 currency code used when none is specified."""

DEFAULT_SEARCH_WEIGHT = 5
"""Default search weight for new attributes."""

MIN_SEARCH_WEIGHT = 1
MAX_SEARCH_WEIGHT = 10

SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
"""Compiled pattern for valid slug values (shared with entities._validate_slug)."""


# ---------------------------------------------------------------------------
# ARCH-03: Domain enums moved from infrastructure
# ---------------------------------------------------------------------------


class MediaType(str, enum.Enum):
    """Discriminator for media asset file types.

    Members:
        IMAGE: Raster or vector image (JPEG, PNG, SVG, WebP).
        VIDEO: Video file (MP4, WebM).
        MODEL_3D: 3-D model file (glTF, USDZ).
        DOCUMENT: PDF or other document attachment.
    """

    IMAGE = "image"
    VIDEO = "video"
    MODEL_3D = "model_3d"
    DOCUMENT = "document"


class MediaRole(str, enum.Enum):
    """Semantic role a media asset plays within a product gallery.

    Defines the business-level roles that media assets can fulfil,
    independent of any infrastructure or ORM details.

    Members:
        MAIN: Primary product image (one per variant), shown in listings.
        HOVER: Image shown on mouse-over in catalog grids.
        GALLERY: Additional gallery images.
        HERO_VIDEO: Hero video for the product detail page.
        SIZE_GUIDE: Size/fit guide image or document.
        PACKAGING: Packaging shots.
    """

    MAIN = "main"
    HOVER = "hover"
    GALLERY = "gallery"
    HERO_VIDEO = "hero_video"
    SIZE_GUIDE = "size_guide"
    PACKAGING = "packaging"


from src.modules.supplier.domain.value_objects import SupplierType  # noqa: F401


# ---------------------------------------------------------------------------
# QUAL-01: BehaviorFlags value object
# ---------------------------------------------------------------------------


@frozen
class BehaviorFlags:
    """Immutable value object grouping boolean behavior flags for an Attribute.

    Replaces the individual ``is_filterable``, ``is_searchable``,
    ``is_comparable``, ``is_visible_on_card``, ``is_visible_in_catalog``
    booleans and the ``search_weight`` integer that were previously
    passed as separate parameters.

    Attributes:
        is_filterable: Available as filter on the storefront.
        is_searchable: Participates in full-text search.
        search_weight: Priority for search ranking (1-10, default 5).
        is_comparable: Shown in the product comparison table.
        is_visible_on_card: Shown on the product detail page.
        is_visible_in_catalog: Shown in catalog listing preview.
    """

    is_filterable: bool = False
    is_searchable: bool = False
    search_weight: int = DEFAULT_SEARCH_WEIGHT
    is_comparable: bool = False
    is_visible_on_card: bool = False
    is_visible_in_catalog: bool = False

    def __attrs_post_init__(self) -> None:
        if not (MIN_SEARCH_WEIGHT <= self.search_weight <= MAX_SEARCH_WEIGHT):
            raise ValueError(
                f"search_weight must be between {MIN_SEARCH_WEIGHT} and "
                f"{MAX_SEARCH_WEIGHT}, got {self.search_weight}"
            )


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

    Values use lowercase strings to enable simple string-based
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


# @frozen does not generate order methods by default in attrs, so custom
# __lt__/__le__/__gt__/__ge__ are safe to define without conflict.
# __attrs_post_init__ in @frozen classes must only read fields, never assign;
# our validation only reads self.amount and self.currency, so this is safe.
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
        object.__setattr__(self, "currency", self.currency.upper())

    @staticmethod
    def from_primitives(
        amount: int,
        currency: str,
        compare_at_amount: int | None = None,
    ) -> tuple[Money, Money | None]:
        """Build a price/compare-at-price pair from primitive values.

        Convenience factory that eliminates repeated Money construction
        boilerplate across command handlers.

        Args:
            amount: Price in smallest currency units.
            currency: 3-character ISO 4217 currency code.
            compare_at_amount: Optional compare-at (strikethrough) price.
                When provided, must be strictly greater than *amount*.

        Returns:
            Tuple of ``(price, compare_at_price)``.  ``compare_at_price``
            is ``None`` when *compare_at_amount* is ``None``.

        Raises:
            ValueError: If *compare_at_amount* is not greater than *amount*.
        """
        price = Money(amount=amount, currency=currency)
        compare_at_price: Money | None = None
        if compare_at_amount is not None:
            if compare_at_amount <= amount:
                raise ValueError("compare_at_price must be greater than price")
            compare_at_price = Money(amount=compare_at_amount, currency=currency)
        return price, compare_at_price

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

    def __lt__(self, other: object) -> bool:
        """Return True if this amount is strictly less than *other*.

        Returns NotImplemented for non-Money operands so Python can
        try the reflected operation or raise TypeError.
        """
        if not isinstance(other, Money):
            return NotImplemented
        self._check_currency(other)
        return self.amount < other.amount

    def __le__(self, other: object) -> bool:
        """Return True if this amount is less than or equal to *other*."""
        if not isinstance(other, Money):
            return NotImplemented
        self._check_currency(other)
        return self.amount <= other.amount

    def __gt__(self, other: object) -> bool:
        """Return True if this amount is strictly greater than *other*."""
        if not isinstance(other, Money):
            return NotImplemented
        self._check_currency(other)
        return self.amount > other.amount

    def __ge__(self, other: object) -> bool:
        """Return True if this amount is greater than or equal to *other*."""
        if not isinstance(other, Money):
            return NotImplemented
        self._check_currency(other)
        return self.amount >= other.amount
