"""
Constants and cache-key builders for the Catalog module.

Part of the application layer.
"""

import uuid

DEFAULT_CURRENCY = "RUB"
"""Default ISO 4217 currency code used when none is specified."""

DEFAULT_SEARCH_WEIGHT = 5
"""Default search weight for new attributes."""

REQUIRED_LOCALES: frozenset[str] = frozenset({"ru", "en"})
"""Locales that must be present in every user-facing i18n field."""


CATEGORY_TREE_CACHE_KEY = "catalog:category_tree"
"""Redis cache key for the full category tree JSON payload."""


def storefront_filters_cache_key(category_id: uuid.UUID) -> str:
    """Redis cache key for storefront filterable attributes of a category."""
    return f"catalog:storefront:filters:{category_id}"


def storefront_card_cache_key(category_id: uuid.UUID) -> str:
    """Redis cache key for storefront card attributes of a category."""
    return f"catalog:storefront:card:{category_id}"


def storefront_comparison_cache_key(category_id: uuid.UUID) -> str:
    """Redis cache key for storefront comparison attributes of a category."""
    return f"catalog:storefront:comparison:{category_id}"


def storefront_form_cache_key(category_id: uuid.UUID) -> str:
    """Redis cache key for storefront form attributes of a category."""
    return f"catalog:storefront:form:{category_id}"


STOREFRONT_CACHE_TTL = 3600
"""TTL in seconds for storefront attribute cache entries.

Safety-net TTL ensures caches self-heal within 1 hour even if explicit
invalidation fails (e.g. Redis temporarily unreachable after commit).
Caches are still invalidated explicitly on every database mutation.
"""


def template_effective_attrs_cache_key(template_id: uuid.UUID) -> str:
    """Build the Redis cache key for a template's effective attribute set."""
    return f"catalog:template:{template_id}:effective_attrs"
