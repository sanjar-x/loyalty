"""Leaf Hypothesis strategies for catalog domain value objects.

Provides composable strategies for generating valid primitive values
used throughout the catalog domain: i18n dictionaries, URL-safe slugs,
machine-readable codes, monetary amounts, behavior flags, and all
domain enums. These form the foundation layer that entity and aggregate
strategies build upon.
"""

from __future__ import annotations

import uuid

from hypothesis import strategies as st

from src.modules.catalog.domain.value_objects import (
    AttributeDataType,
    AttributeLevel,
    AttributeUIType,
    BehaviorFlags,
    MediaRole,
    MediaType,
    Money,
    ProductStatus,
    RequirementLevel,
    MIN_SEARCH_WEIGHT,
    MAX_SEARCH_WEIGHT,
)


def i18n_names(
    min_length: int = 1, max_length: int = 50
) -> st.SearchStrategy[dict[str, str]]:
    """Generate i18n dictionaries with both required locales ("ru" and "en").

    Uses a safe alphabet (letters, numbers, spaces) with min_codepoint=65
    to avoid control characters and low ASCII that cause _validate_i18n_values()
    failures. Filters out whitespace-only strings.

    Args:
        min_length: Minimum length of each locale string.
        max_length: Maximum length of each locale string.

    Returns:
        Strategy producing dicts like {"ru": "...", "en": "..."}.
    """
    name_st = st.text(
        min_size=min_length,
        max_size=max_length,
        alphabet=st.characters(
            whitelist_categories=("L", "N", "Zs"),
            min_codepoint=65,
            max_codepoint=1000,
        ),
    ).filter(lambda s: s.strip() != "")

    required = st.fixed_dictionaries({"ru": name_st, "en": name_st})

    # Optionally merge extra locales
    extra = st.dictionaries(
        st.sampled_from(["fr", "de", "zh"]),
        name_st,
        min_size=0,
        max_size=2,
    )

    @st.composite
    def _merged(draw: st.DrawFn) -> dict[str, str]:
        base = draw(required)
        extras = draw(extra)
        return {**extras, **base}  # base keys override any overlap

    return _merged()


def valid_slugs(
    min_length: int = 1, max_length: int = 40
) -> st.SearchStrategy[str]:
    """Generate strings matching ^[a-z0-9]+(-[a-z0-9]+)*$.

    Uses a segment-based approach per research pitfall #3 to avoid
    edge cases like leading hyphens, consecutive hyphens, and empty
    segments that st.text() would generate.

    Args:
        min_length: Minimum total slug length.
        max_length: Maximum total slug length.

    Returns:
        Strategy producing valid slugs like "abc", "my-slug-123".
    """
    return st.from_regex(
        r"[a-z][a-z0-9]{0,9}(-[a-z0-9]{1,10}){0,3}", fullmatch=True
    ).filter(lambda s: min_length <= len(s) <= max_length)


def valid_codes(
    min_length: int = 1, max_length: int = 30
) -> st.SearchStrategy[str]:
    """Generate machine-readable codes (like slugs but for attribute/group codes).

    Same pattern as slugs: lowercase alphanumeric with hyphens.

    Args:
        min_length: Minimum code length.
        max_length: Maximum code length.

    Returns:
        Strategy producing valid codes like "color", "screen-size".
    """
    return st.from_regex(
        r"[a-z][a-z0-9]{0,9}(-[a-z0-9]{1,10}){0,3}", fullmatch=True
    ).filter(lambda s: min_length <= len(s) <= max_length)


def money(
    min_amount: int = 0,
    max_amount: int = 10_000_00,
    currencies: list[str] | None = None,
) -> st.SearchStrategy[Money]:
    """Generate valid Money value objects.

    Args:
        min_amount: Minimum amount in smallest currency units.
        max_amount: Maximum amount in smallest currency units.
        currencies: List of 3-char ISO 4217 codes. Defaults to RUB/USD/EUR.

    Returns:
        Strategy producing Money instances.
    """
    return st.builds(
        Money,
        amount=st.integers(min_value=min_amount, max_value=max_amount),
        currency=st.sampled_from(currencies or ["RUB", "USD", "EUR"]),
    )


def behavior_flags() -> st.SearchStrategy[BehaviorFlags]:
    """Generate valid BehaviorFlags value objects.

    search_weight is constrained to the valid range [MIN_SEARCH_WEIGHT, MAX_SEARCH_WEIGHT].

    Returns:
        Strategy producing BehaviorFlags instances.
    """
    return st.builds(
        BehaviorFlags,
        is_filterable=st.booleans(),
        is_searchable=st.booleans(),
        search_weight=st.integers(
            min_value=MIN_SEARCH_WEIGHT, max_value=MAX_SEARCH_WEIGHT
        ),
        is_comparable=st.booleans(),
        is_visible_on_card=st.booleans(),
    )


def data_types() -> st.SearchStrategy[AttributeDataType]:
    """Generate AttributeDataType enum values."""
    return st.sampled_from(list(AttributeDataType))


def ui_types() -> st.SearchStrategy[AttributeUIType]:
    """Generate AttributeUIType enum values."""
    return st.sampled_from(list(AttributeUIType))


def attribute_levels() -> st.SearchStrategy[AttributeLevel]:
    """Generate AttributeLevel enum values."""
    return st.sampled_from(list(AttributeLevel))


def requirement_levels() -> st.SearchStrategy[RequirementLevel]:
    """Generate RequirementLevel enum values."""
    return st.sampled_from(list(RequirementLevel))


def media_types() -> st.SearchStrategy[MediaType]:
    """Generate MediaType enum values."""
    return st.sampled_from(list(MediaType))


def media_roles() -> st.SearchStrategy[MediaRole]:
    """Generate MediaRole enum values."""
    return st.sampled_from(list(MediaRole))


def uuids() -> st.SearchStrategy[uuid.UUID]:
    """Generate version-4 UUIDs."""
    return st.uuids(version=4)


def tags() -> st.SearchStrategy[list[str]]:
    """Generate lists of tag strings.

    Tags are non-empty strings of letters and numbers, up to 5 per list.

    Returns:
        Strategy producing lists of tag strings.
    """
    return st.lists(
        st.text(
            min_size=1,
            max_size=30,
            alphabet=st.characters(whitelist_categories=("L", "N")),
        ).filter(lambda s: s.strip()),
        max_size=5,
    )
