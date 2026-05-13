"""
Shared helper functions and constants for catalog domain entities.

Contains validation helpers (_validate_slug, _generate_id, etc.) and
guarded field sets used across multiple entity modules. Part of the
domain layer -- zero infrastructure imports.
"""

import uuid
from typing import Any

from src.modules.catalog.domain.value_objects import SLUG_RE

GENERAL_GROUP_CODE = "general"
"""Code of the default attribute group that always exists and cannot be deleted."""


def _validate_slug(slug: str, entity_name: str) -> None:
    """Validate that a slug is URL-safe (lowercase alphanumeric with hyphens)."""
    if not slug or not SLUG_RE.match(slug):
        raise ValueError(
            f"{entity_name} slug must be non-empty and match pattern: "
            f"lowercase letters, digits, and hyphens (e.g. 'my-slug-123')"
        )


def _generate_id() -> uuid.UUID:
    """Generate a time-sortable UUID (v7 if available, v4 fallback)."""
    return uuid.uuid7() if hasattr(uuid, "uuid7") else uuid.uuid4()


def _validate_sort_order(sort_order: int, entity_name: str) -> None:
    """Validate that sort_order is non-negative."""
    if sort_order < 0:
        raise ValueError(f"{entity_name} sort_order must be non-negative")


def _validate_i18n_values(i18n_dict: dict[str, str], field_name: str) -> None:
    """Validate that i18n dict values are non-blank."""
    if any(not v or not v.strip() for v in i18n_dict.values()):
        raise ValueError(f"{field_name} must not contain empty or blank values")


_FILTER_SETTINGS_MAX_KEYS = 20
_FILTER_SETTINGS_ALLOWED_KEYS = frozenset(
    {
        "widget",
        "min",
        "max",
        "step",
        "unit",
        "collapsed",
        "behavior",
        "display",
        "options",
    }
)


def _validate_filter_settings(settings: dict[str, Any] | None) -> None:
    """Basic structural validation for filter_settings JSON.

    Ensures the dict is flat-ish (top-level key whitelist) and bounded
    in size.  Full semantic validation is deferred to the frontend.
    """
    if settings is None:
        return
    if not isinstance(settings, dict):
        raise ValueError("filter_settings must be a JSON object")
    if len(settings) > _FILTER_SETTINGS_MAX_KEYS:
        raise ValueError(
            f"filter_settings has too many keys: {len(settings)} "
            f"(max {_FILTER_SETTINGS_MAX_KEYS})"
        )
    unknown = settings.keys() - _FILTER_SETTINGS_ALLOWED_KEYS
    if unknown:
        raise ValueError(
            f"filter_settings contains unknown keys: {', '.join(sorted(unknown))}. "
            f"Allowed: {', '.join(sorted(_FILTER_SETTINGS_ALLOWED_KEYS))}"
        )
