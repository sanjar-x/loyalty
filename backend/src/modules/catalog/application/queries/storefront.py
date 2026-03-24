"""
Storefront query handlers -- 4 read-only endpoints for the frontend.

Pure CQRS read side: queries the ORM directly with JOIN-loaded relationships,
applies flag-override resolution, and returns structured read models.

Handlers:
    1. StorefrontFilterableAttributesHandler -- filterable attributes + values
    2. StorefrontCardAttributesHandler -- visible-on-card attributes grouped
    3. StorefrontComparisonAttributesHandler -- comparable attributes
    4. StorefrontFormAttributesHandler -- full attribute set with validation

NOTE: _load_bindings_with_attributes is stubbed out -- will be rewritten
in Task 16 to resolve attributes through AttributeFamily.
"""

import json
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.application.constants import (
    STOREFRONT_CACHE_TTL,
    storefront_card_cache_key,
    storefront_comparison_cache_key,
    storefront_filters_cache_key,
    storefront_form_cache_key,
)
from src.modules.catalog.application.queries.read_models import (
    StorefrontCardReadModel,
    StorefrontComparisonReadModel,
    StorefrontFilterListReadModel,
    StorefrontFormReadModel,
)
from src.shared.interfaces.cache import ICacheService
from src.shared.interfaces.logger import ILogger


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


async def _load_bindings_with_attributes(
    session: AsyncSession, category_id: uuid.UUID
) -> list:
    """Placeholder -- will be rewritten in Task 16 to resolve through AttributeFamily."""
    raise NotImplementedError(
        "_load_bindings_with_attributes will be rewritten to use AttributeFamily"
    )


# ---------------------------------------------------------------------------
# 1. Filterable attributes
# ---------------------------------------------------------------------------


class StorefrontFilterableAttributesHandler:
    """Fetch filterable attributes for a category with their values."""

    def __init__(self, session: AsyncSession, cache: ICacheService, logger: ILogger):
        self._session = session
        self._cache = cache
        self._logger = logger.bind(handler="StorefrontFilterableAttributesHandler")

    async def handle(self, category_id: uuid.UUID) -> StorefrontFilterListReadModel:
        """Return all attributes where the effective is_filterable flag is True."""
        cache_key = storefront_filters_cache_key(category_id)
        cached = await self._cache.get(cache_key)
        if cached is not None:
            return StorefrontFilterListReadModel.model_validate(json.loads(cached))

        # Will be rewritten in Task 16 to resolve through AttributeFamily
        raise NotImplementedError(
            "StorefrontFilterableAttributesHandler will be rewritten to use AttributeFamily"
        )


# ---------------------------------------------------------------------------
# 2. Card attributes (grouped)
# ---------------------------------------------------------------------------


class StorefrontCardAttributesHandler:
    """Fetch visible-on-card attributes for a category, grouped by attribute group."""

    def __init__(self, session: AsyncSession, cache: ICacheService, logger: ILogger):
        self._session = session
        self._cache = cache
        self._logger = logger.bind(handler="StorefrontCardAttributesHandler")

    async def handle(self, category_id: uuid.UUID) -> StorefrontCardReadModel:
        """Return all attributes where the effective is_visible_on_card flag is True."""
        cache_key = storefront_card_cache_key(category_id)
        cached = await self._cache.get(cache_key)
        if cached is not None:
            return StorefrontCardReadModel.model_validate(json.loads(cached))

        # Will be rewritten in Task 16 to resolve through AttributeFamily
        raise NotImplementedError(
            "StorefrontCardAttributesHandler will be rewritten to use AttributeFamily"
        )


# ---------------------------------------------------------------------------
# 3. Comparison attributes
# ---------------------------------------------------------------------------


class StorefrontComparisonAttributesHandler:
    """Fetch comparable attributes for a category."""

    def __init__(self, session: AsyncSession, cache: ICacheService, logger: ILogger):
        self._session = session
        self._cache = cache
        self._logger = logger.bind(handler="StorefrontComparisonAttributesHandler")

    async def handle(self, category_id: uuid.UUID) -> StorefrontComparisonReadModel:
        """Return all attributes where the effective is_comparable flag is True."""
        cache_key = storefront_comparison_cache_key(category_id)
        cached = await self._cache.get(cache_key)
        if cached is not None:
            return StorefrontComparisonReadModel.model_validate(json.loads(cached))

        # Will be rewritten in Task 16 to resolve through AttributeFamily
        raise NotImplementedError(
            "StorefrontComparisonAttributesHandler will be rewritten to use AttributeFamily"
        )


# ---------------------------------------------------------------------------
# 4. Form attributes (full set, grouped, with validation + values)
# ---------------------------------------------------------------------------


class StorefrontFormAttributesHandler:
    """Fetch the complete attribute set for a product creation form."""

    def __init__(self, session: AsyncSession, cache: ICacheService, logger: ILogger):
        self._session = session
        self._cache = cache
        self._logger = logger.bind(handler="StorefrontFormAttributesHandler")

    async def handle(self, category_id: uuid.UUID) -> StorefrontFormReadModel:
        """Return ALL attributes bound to this category, grouped, with full metadata."""
        cache_key = storefront_form_cache_key(category_id)
        cached = await self._cache.get(cache_key)
        if cached is not None:
            return StorefrontFormReadModel.model_validate(json.loads(cached))

        # Will be rewritten in Task 16 to resolve through AttributeFamily
        raise NotImplementedError(
            "StorefrontFormAttributesHandler will be rewritten to use AttributeFamily"
        )


# ---------------------------------------------------------------------------
# Cache invalidation
# ---------------------------------------------------------------------------


async def invalidate_storefront_cache(
    cache: ICacheService,
    category_id: uuid.UUID,
) -> None:
    """Delete all storefront cache entries for the given category.

    Must be called whenever data that feeds the storefront queries changes:
      - Attribute metadata updates  (name, flags, ui_type, ...)
      - Attribute value additions / updates / deletions
      - Family-attribute binding changes  (bind, unbind, reorder,
        flag_overrides, filter_settings, requirement_level)

    The category tree cache (``CATEGORY_TREE_CACHE_KEY``) is handled
    separately in the category CRUD handlers; this function only covers
    the per-category storefront attribute caches.
    """
    keys = [
        storefront_filters_cache_key(category_id),
        storefront_card_cache_key(category_id),
        storefront_comparison_cache_key(category_id),
        storefront_form_cache_key(category_id),
    ]
    await cache.delete_many(keys)
