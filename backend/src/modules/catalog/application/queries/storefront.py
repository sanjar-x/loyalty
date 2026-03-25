"""
Storefront query handlers -- 4 read-only endpoints for the frontend.

Pure CQRS read side: resolves effective attributes through AttributeFamily,
applies flag-override resolution, and returns structured read models.

Handlers:
    1. StorefrontFilterableAttributesHandler -- filterable attributes + values
    2. StorefrontCardAttributesHandler -- visible-on-card attributes grouped
    3. StorefrontComparisonAttributesHandler -- comparable attributes
    4. StorefrontFormAttributesHandler -- full attribute set with validation
"""

import json
import uuid
from collections import defaultdict
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
    StorefrontCardAttributeReadModel,
    StorefrontCardGroupReadModel,
    StorefrontCardReadModel,
    StorefrontComparisonAttributeReadModel,
    StorefrontComparisonReadModel,
    StorefrontFilterAttributeReadModel,
    StorefrontFilterListReadModel,
    StorefrontFormAttributeReadModel,
    StorefrontFormGroupReadModel,
    StorefrontFormReadModel,
    StorefrontValueReadModel,
)
from src.modules.catalog.application.queries.resolve_family_attributes import (
    EffectiveAttributeReadModel,
    ResolveFamilyAttributesHandler,
)
from src.modules.catalog.domain.exceptions import CategoryNotFoundError
from src.shared.interfaces.cache import ICacheService
from src.shared.interfaces.logger import ILogger


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _effective_bool(
    flag_overrides: dict[str, Any] | None,
    flag_name: str,
    global_default: bool,
) -> bool:
    """Resolve an effective boolean flag.

    If ``flag_overrides`` contains the flag, use the override value;
    otherwise fall back to the attribute's global default.
    """
    if flag_overrides and flag_name in flag_overrides:
        return bool(flag_overrides[flag_name])
    return global_default


def _values_to_read_models(
    attr: EffectiveAttributeReadModel,
) -> list[StorefrontValueReadModel]:
    """Convert effective attribute values to storefront value read models."""
    return [
        StorefrontValueReadModel(
            id=v.id,
            code=v.code,
            slug=v.slug,
            value_i18n=v.value_i18n,
            meta_data=v.meta_data,
            value_group=v.value_group,
            sort_order=v.sort_order,
        )
        for v in attr.values
    ]


async def _resolve_effective_for_category(
    session: AsyncSession,
    resolver: ResolveFamilyAttributesHandler,
    category_id: uuid.UUID,
) -> list[EffectiveAttributeReadModel]:
    """Load category, get family_id, resolve effective attributes."""
    from src.modules.catalog.infrastructure.models import Category as OrmCategory

    cat = await session.get(OrmCategory, category_id)
    if cat is None:
        raise CategoryNotFoundError(category_id=category_id)
    if cat.effective_family_id is None:
        return []
    result = await resolver.handle(cat.effective_family_id)
    return result.attributes


# ---------------------------------------------------------------------------
# 1. Filterable attributes
# ---------------------------------------------------------------------------


class StorefrontFilterableAttributesHandler:
    """Fetch filterable attributes for a category with their values."""

    def __init__(
        self,
        session: AsyncSession,
        resolver: ResolveFamilyAttributesHandler,
        cache: ICacheService,
        logger: ILogger,
    ):
        self._session = session
        self._resolver = resolver
        self._cache = cache
        self._logger = logger.bind(handler="StorefrontFilterableAttributesHandler")

    async def handle(self, category_id: uuid.UUID) -> StorefrontFilterListReadModel:
        """Return all attributes where the effective is_filterable flag is True."""
        cache_key = storefront_filters_cache_key(category_id)
        cached = await self._cache.get(cache_key)
        if cached is not None:
            return StorefrontFilterListReadModel.model_validate(json.loads(cached))

        effective = await _resolve_effective_for_category(
            self._session, self._resolver, category_id
        )

        filter_attrs: list[StorefrontFilterAttributeReadModel] = []
        for attr in effective:
            if not _effective_bool(
                attr.flag_overrides, "is_filterable", attr.is_filterable
            ):
                continue
            filter_attrs.append(
                StorefrontFilterAttributeReadModel(
                    attribute_id=attr.attribute_id,
                    code=attr.code,
                    slug=attr.slug,
                    name_i18n=attr.name_i18n,
                    data_type=attr.data_type,
                    ui_type=attr.ui_type,
                    is_dictionary=attr.is_dictionary,
                    values=_values_to_read_models(attr),
                    filter_settings=attr.filter_settings,
                    sort_order=attr.sort_order,
                )
            )

        result = StorefrontFilterListReadModel(
            category_id=category_id,
            attributes=filter_attrs,
        )

        await self._cache.set(
            cache_key,
            json.dumps(result.model_dump(mode="json")),
            ttl=STOREFRONT_CACHE_TTL,
        )
        return result


# ---------------------------------------------------------------------------
# 2. Card attributes (grouped)
# ---------------------------------------------------------------------------


class StorefrontCardAttributesHandler:
    """Fetch visible-on-card attributes for a category, grouped by attribute group."""

    def __init__(
        self,
        session: AsyncSession,
        resolver: ResolveFamilyAttributesHandler,
        cache: ICacheService,
        logger: ILogger,
    ):
        self._session = session
        self._resolver = resolver
        self._cache = cache
        self._logger = logger.bind(handler="StorefrontCardAttributesHandler")

    async def handle(self, category_id: uuid.UUID) -> StorefrontCardReadModel:
        """Return all attributes where the effective is_visible_on_card flag is True."""
        cache_key = storefront_card_cache_key(category_id)
        cached = await self._cache.get(cache_key)
        if cached is not None:
            return StorefrontCardReadModel.model_validate(json.loads(cached))

        effective = await _resolve_effective_for_category(
            self._session, self._resolver, category_id
        )

        # Group by attribute group
        groups_map: dict[uuid.UUID | None, list[StorefrontCardAttributeReadModel]] = (
            defaultdict(list)
        )
        group_meta: dict[uuid.UUID | None, tuple[str | None, dict[str, Any], int]] = {}

        for attr in effective:
            if not _effective_bool(
                attr.flag_overrides, "is_visible_on_card", attr.is_visible_on_card
            ):
                continue
            groups_map[attr.group_id].append(
                StorefrontCardAttributeReadModel(
                    attribute_id=attr.attribute_id,
                    code=attr.code,
                    slug=attr.slug,
                    name_i18n=attr.name_i18n,
                    data_type=attr.data_type,
                    ui_type=attr.ui_type,
                    requirement_level=attr.requirement_level,
                    sort_order=attr.sort_order,
                )
            )
            if attr.group_id not in group_meta:
                group_meta[attr.group_id] = (
                    attr.group_code,
                    attr.group_name_i18n,
                    attr.group_sort_order,
                )

        groups: list[StorefrontCardGroupReadModel] = []
        for gid, attrs in groups_map.items():
            code, name_i18n, sort_order = group_meta.get(gid, (None, {}, 0))
            groups.append(
                StorefrontCardGroupReadModel(
                    group_id=gid,
                    group_code=code,
                    group_name_i18n=name_i18n,
                    group_sort_order=sort_order,
                    attributes=attrs,
                )
            )
        groups.sort(key=lambda g: g.group_sort_order)

        result = StorefrontCardReadModel(
            category_id=category_id,
            groups=groups,
        )

        await self._cache.set(
            cache_key,
            json.dumps(result.model_dump(mode="json")),
            ttl=STOREFRONT_CACHE_TTL,
        )
        return result


# ---------------------------------------------------------------------------
# 3. Comparison attributes
# ---------------------------------------------------------------------------


class StorefrontComparisonAttributesHandler:
    """Fetch comparable attributes for a category."""

    def __init__(
        self,
        session: AsyncSession,
        resolver: ResolveFamilyAttributesHandler,
        cache: ICacheService,
        logger: ILogger,
    ):
        self._session = session
        self._resolver = resolver
        self._cache = cache
        self._logger = logger.bind(handler="StorefrontComparisonAttributesHandler")

    async def handle(self, category_id: uuid.UUID) -> StorefrontComparisonReadModel:
        """Return all attributes where the effective is_comparable flag is True."""
        cache_key = storefront_comparison_cache_key(category_id)
        cached = await self._cache.get(cache_key)
        if cached is not None:
            return StorefrontComparisonReadModel.model_validate(json.loads(cached))

        effective = await _resolve_effective_for_category(
            self._session, self._resolver, category_id
        )

        comparison_attrs: list[StorefrontComparisonAttributeReadModel] = []
        for attr in effective:
            if not _effective_bool(
                attr.flag_overrides, "is_comparable", attr.is_comparable
            ):
                continue
            comparison_attrs.append(
                StorefrontComparisonAttributeReadModel(
                    attribute_id=attr.attribute_id,
                    code=attr.code,
                    slug=attr.slug,
                    name_i18n=attr.name_i18n,
                    data_type=attr.data_type,
                    ui_type=attr.ui_type,
                    sort_order=attr.sort_order,
                )
            )

        result = StorefrontComparisonReadModel(
            category_id=category_id,
            attributes=comparison_attrs,
        )

        await self._cache.set(
            cache_key,
            json.dumps(result.model_dump(mode="json")),
            ttl=STOREFRONT_CACHE_TTL,
        )
        return result


# ---------------------------------------------------------------------------
# 4. Form attributes (full set, grouped, with validation + values)
# ---------------------------------------------------------------------------


class StorefrontFormAttributesHandler:
    """Fetch the complete attribute set for a product creation form."""

    def __init__(
        self,
        session: AsyncSession,
        resolver: ResolveFamilyAttributesHandler,
        cache: ICacheService,
        logger: ILogger,
    ):
        self._session = session
        self._resolver = resolver
        self._cache = cache
        self._logger = logger.bind(handler="StorefrontFormAttributesHandler")

    async def handle(self, category_id: uuid.UUID) -> StorefrontFormReadModel:
        """Return ALL attributes bound to this category, grouped, with full metadata."""
        cache_key = storefront_form_cache_key(category_id)
        cached = await self._cache.get(cache_key)
        if cached is not None:
            return StorefrontFormReadModel.model_validate(json.loads(cached))

        effective = await _resolve_effective_for_category(
            self._session, self._resolver, category_id
        )

        # Group by attribute group -- form returns ALL attributes, no flag filter
        groups_map: dict[uuid.UUID | None, list[StorefrontFormAttributeReadModel]] = (
            defaultdict(list)
        )
        group_meta: dict[uuid.UUID | None, tuple[str | None, dict[str, Any], int]] = {}

        for attr in effective:
            groups_map[attr.group_id].append(
                StorefrontFormAttributeReadModel(
                    attribute_id=attr.attribute_id,
                    code=attr.code,
                    slug=attr.slug,
                    name_i18n=attr.name_i18n,
                    description_i18n=attr.description_i18n,
                    data_type=attr.data_type,
                    ui_type=attr.ui_type,
                    is_dictionary=attr.is_dictionary,
                    level=attr.level,
                    requirement_level=attr.requirement_level,
                    validation_rules=attr.validation_rules,
                    values=_values_to_read_models(attr),
                    sort_order=attr.sort_order,
                )
            )
            if attr.group_id not in group_meta:
                group_meta[attr.group_id] = (
                    attr.group_code,
                    attr.group_name_i18n,
                    attr.group_sort_order,
                )

        groups: list[StorefrontFormGroupReadModel] = []
        for gid, attrs in groups_map.items():
            code, name_i18n, sort_order = group_meta.get(gid, (None, {}, 0))
            groups.append(
                StorefrontFormGroupReadModel(
                    group_id=gid,
                    group_code=code,
                    group_name_i18n=name_i18n,
                    group_sort_order=sort_order,
                    attributes=attrs,
                )
            )
        groups.sort(key=lambda g: g.group_sort_order)

        result = StorefrontFormReadModel(
            category_id=category_id,
            groups=groups,
        )

        await self._cache.set(
            cache_key,
            json.dumps(result.model_dump(mode="json")),
            ttl=STOREFRONT_CACHE_TTL,
        )
        return result


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
