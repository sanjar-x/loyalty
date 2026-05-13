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


STOREFRONT_CACHE_TTL = 3600
"""TTL in seconds for storefront attribute cache entries.

Safety-net TTL ensures caches self-heal within 1 hour even if explicit
invalidation fails (e.g. Redis temporarily unreachable after commit).
Caches are still invalidated explicitly on every database mutation.
"""

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


def template_effective_attrs_cache_key(template_id: uuid.UUID) -> str:
    """Build the Redis cache key for a template's effective attribute set."""
    return f"catalog:template:{template_id}:effective_attrs"


# ---------------------------------------------------------------------------
# Storefront product cache keys & TTLs
# ---------------------------------------------------------------------------

STOREFRONT_PLP_CACHE_TTL = 60
"""TTL for PLP (product listing) cache entries (seconds)."""

STOREFRONT_PDP_CACHE_TTL = 300
"""TTL for PDP (product detail) cache entries (seconds)."""


def storefront_plp_cache_key(query_hash: str) -> str:
    """Redis cache key for a storefront PLP query result."""
    return f"catalog:storefront:plp:{query_hash}"


def storefront_pdp_cache_key(slug: str, generation: int = 0) -> str:
    """Redis cache key for a storefront PDP by product slug + generation."""
    return f"catalog:storefront:pdp:{generation}:{slug}"


STOREFRONT_FACET_CACHE_TTL = 300
"""TTL for facet count cache entries (seconds)."""


STOREFRONT_FACET_GENERATION_KEY = "catalog:storefront:facets:generation"
"""Redis key holding the monotonically-increasing facet generation counter.
Incrementing this key effectively invalidates all existing facet cache
entries because the generation participates in the cache-key hash."""


def storefront_facet_cache_key(query_hash: str) -> str:
    """Redis cache key for facet computation results."""
    return f"catalog:storefront:facets:{query_hash}"


STOREFRONT_SEARCH_CACHE_TTL = 60
"""TTL for search result cache entries (seconds)."""

STOREFRONT_SUGGEST_CACHE_TTL = 120
"""TTL for autocomplete suggestion cache entries (seconds)."""


def storefront_search_cache_key(query_hash: str) -> str:
    """Redis cache key for storefront search query results."""
    return f"catalog:storefront:search:{query_hash}"


def storefront_suggest_cache_key(prefix_hash: str) -> str:
    """Redis cache key for autocomplete suggestions."""
    return f"catalog:storefront:suggest:{prefix_hash}"
