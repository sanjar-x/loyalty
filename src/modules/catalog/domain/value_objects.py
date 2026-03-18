"""
Catalog domain value objects.

Contains immutable types that represent domain concepts without
identity. Part of the domain layer — zero infrastructure imports.
"""

import enum


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
