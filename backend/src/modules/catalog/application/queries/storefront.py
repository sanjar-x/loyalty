"""
Storefront query handlers -- 4 read-only endpoints for the frontend.

Pure CQRS read side: queries the ORM directly with JOIN-loaded relationships,
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
from collections.abc import Callable
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.modules.catalog.application.constants import (
    STOREFRONT_CACHE_TTL,
    storefront_card_cache_key,
    storefront_comparison_cache_key,
    storefront_filters_cache_key,
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
from src.modules.catalog.domain.exceptions import CategoryNotFoundError
from src.modules.catalog.infrastructure.models import (
    Attribute as OrmAttribute,
)
from src.modules.catalog.infrastructure.models import (
    AttributeGroup as OrmAttributeGroup,
)
from src.modules.catalog.infrastructure.models import (
    AttributeValue as OrmAttributeValue,
)
from src.modules.catalog.infrastructure.models import (
    Category as OrmCategory,
)
from src.modules.catalog.infrastructure.models import (
    CategoryAttributeBinding as OrmBinding,
)
from src.shared.interfaces.cache import ICacheService
from src.shared.interfaces.logger import ILogger

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _effective_bool(
    flag_overrides: dict[str, Any] | None, flag_name: str, global_value: bool
) -> bool:
    """Resolve an effective boolean flag value.

    If the binding's ``flag_overrides`` dict contains a key for *flag_name*,
    that value is used. Otherwise the global attribute flag is used.
    """
    if flag_overrides and flag_name in flag_overrides:
        return bool(flag_overrides[flag_name])
    return global_value


def _effective_ui_type(filter_settings: dict[str, Any] | None, global_ui_type: str) -> str:
    """Resolve the effective UI type for storefront display.

    If filter_settings has a ``filter_type`` key, it overrides the
    global ``ui_type`` from the attribute.
    """
    if filter_settings and "filter_type" in filter_settings:
        return str(filter_settings["filter_type"])
    return global_ui_type


def _values_to_read_models(
    values: list[OrmAttributeValue],
) -> list[StorefrontValueReadModel]:
    """Convert ORM attribute values to storefront value read models.

    Note: ORM ``group_code`` is mapped to read-model ``value_group`` to
    keep the public API field name stable.
    """
    return [
        StorefrontValueReadModel(
            id=v.id,
            code=v.code,
            slug=v.slug,
            value_i18n=v.value_i18n,
            meta_data=v.meta_data,
            value_group=v.group_code,  # ORM group_code -> read model value_group
            sort_order=v.sort_order,
        )
        for v in sorted(values, key=lambda x: x.sort_order)
    ]


async def _load_bindings_with_attributes(
    session: AsyncSession, category_id: uuid.UUID
) -> list[OrmBinding]:
    """Load all bindings for a category with eagerly-loaded attribute + group + values.

    Raises:
        CategoryNotFoundError: If the category does not exist.
    """
    # Verify the category exists before loading bindings
    cat = await session.get(OrmCategory, category_id)
    if cat is None:
        raise CategoryNotFoundError(category_id=category_id)

    stmt = (
        select(OrmBinding)
        .where(OrmBinding.category_id == category_id)
        .options(
            joinedload(OrmBinding.attribute).joinedload(OrmAttribute.group),
            joinedload(OrmBinding.attribute).selectinload(OrmAttribute.values),
        )
        .order_by(OrmBinding.sort_order)
    )
    result = await session.execute(stmt)
    return list(result.unique().scalars().all())


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

        rules = await _load_bindings_with_attributes(self._session, category_id)

        attributes: list[StorefrontFilterAttributeReadModel] = []
        for rule in rules:
            attr = rule.attribute
            if not _effective_bool(rule.flag_overrides, "is_filterable", attr.is_filterable):
                continue

            ui_type = _effective_ui_type(rule.filter_settings, attr.ui_type.value)
            values = _values_to_read_models(attr.values) if attr.is_dictionary else []

            attributes.append(
                StorefrontFilterAttributeReadModel(
                    attribute_id=attr.id,
                    code=attr.code,
                    slug=attr.slug,
                    name_i18n=attr.name_i18n,
                    data_type=attr.data_type.value,
                    ui_type=ui_type,
                    is_dictionary=attr.is_dictionary,
                    values=values,
                    filter_settings=dict(rule.filter_settings) if rule.filter_settings else None,
                    sort_order=rule.sort_order,
                )
            )

        result = StorefrontFilterListReadModel(
            category_id=category_id,
            attributes=attributes,
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

        rules = await _load_bindings_with_attributes(self._session, category_id)

        grouped = _group_bindings_into_groups(
            rules,
            predicate=lambda rule, attr: _effective_bool(
                rule.flag_overrides, "is_visible_on_card", attr.is_visible_on_card
            ),
        )

        group_models: list[StorefrontCardGroupReadModel] = []
        for gid, group, items in grouped:
            card_attrs = [
                StorefrontCardAttributeReadModel(
                    attribute_id=attr.id,
                    code=attr.code,
                    slug=attr.slug,
                    name_i18n=attr.name_i18n,
                    data_type=attr.data_type.value,
                    ui_type=attr.ui_type.value,
                    requirement_level=rule.requirement_level.value,
                    sort_order=rule.sort_order,
                )
                for rule, attr in items
            ]
            group_models.append(
                StorefrontCardGroupReadModel(
                    group_id=gid,
                    group_code=group.code if group else None,
                    group_name_i18n=group.name_i18n if group else {},
                    group_sort_order=group.sort_order if group else 0,
                    attributes=card_attrs,
                )
            )

        result = StorefrontCardReadModel(
            category_id=category_id,
            groups=group_models,
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

        rules = await _load_bindings_with_attributes(self._session, category_id)

        attributes: list[StorefrontComparisonAttributeReadModel] = []
        for rule in rules:
            attr = rule.attribute
            if not _effective_bool(rule.flag_overrides, "is_comparable", attr.is_comparable):
                continue

            attributes.append(
                StorefrontComparisonAttributeReadModel(
                    attribute_id=attr.id,
                    code=attr.code,
                    slug=attr.slug,
                    name_i18n=attr.name_i18n,
                    data_type=attr.data_type.value,
                    ui_type=attr.ui_type.value,
                    sort_order=rule.sort_order,
                )
            )

        result = StorefrontComparisonReadModel(
            category_id=category_id,
            attributes=attributes,
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

    def __init__(self, session: AsyncSession, logger: ILogger):
        self._session = session
        self._logger = logger.bind(handler="StorefrontFormAttributesHandler")

    async def handle(self, category_id: uuid.UUID) -> StorefrontFormReadModel:
        """Return ALL attributes bound to this category, grouped, with full metadata."""
        rules = await _load_bindings_with_attributes(self._session, category_id)

        grouped = _group_bindings_into_groups(rules)

        group_models: list[StorefrontFormGroupReadModel] = []
        for gid, group, items in grouped:
            form_attrs = [
                StorefrontFormAttributeReadModel(
                    attribute_id=attr.id,
                    code=attr.code,
                    slug=attr.slug,
                    name_i18n=attr.name_i18n,
                    description_i18n=attr.description_i18n,
                    data_type=attr.data_type.value,
                    ui_type=attr.ui_type.value,
                    is_dictionary=attr.is_dictionary,
                    level=attr.level.value,
                    requirement_level=rule.requirement_level.value,
                    validation_rules=(
                        dict(attr.validation_rules) if attr.validation_rules else None
                    ),
                    values=_values_to_read_models(attr.values) if attr.is_dictionary else [],
                    sort_order=rule.sort_order,
                )
                for rule, attr in items
            ]
            group_models.append(
                StorefrontFormGroupReadModel(
                    group_id=gid,
                    group_code=group.code if group else None,
                    group_name_i18n=group.name_i18n if group else {},
                    group_sort_order=group.sort_order if group else 0,
                    attributes=form_attrs,
                )
            )

        return StorefrontFormReadModel(
            category_id=category_id,
            groups=group_models,
        )


# ---------------------------------------------------------------------------
# Sentinel for null groups (attributes with no group assigned)
# ---------------------------------------------------------------------------


class _NullGroup:
    """Placeholder for attributes whose group_id is NULL.

    All fields are immutable to prevent cross-request corruption
    (module-level singleton).
    """

    __slots__ = ()
    sort_order: int = 999_999
    code: str | None = None

    @property
    def name_i18n(self) -> dict[str, Any]:
        """Return a fresh empty dict each time (caller can mutate safely)."""
        return {}


_NULL_GROUP = _NullGroup()


def _null_group() -> _NullGroup:
    return _NULL_GROUP


def _group_bindings_into_groups(
    bindings: list[OrmBinding],
    *,
    predicate: Callable[[OrmBinding, OrmAttribute], bool] | None = None,
) -> list[
    tuple[
        uuid.UUID | None,
        OrmAttributeGroup | None,
        list[tuple[OrmBinding, OrmAttribute]],
    ]
]:
    """Group bindings by attribute group, filter with optional *predicate*, and sort.

    Returns a list of ``(group_id, group_or_none, [(binding, attribute), ...])``
    tuples sorted by the group's ``sort_order`` (NULL-group last).
    """
    groups_map: dict[uuid.UUID | None, list[tuple[OrmBinding, OrmAttribute]]] = defaultdict(list)
    group_info: dict[uuid.UUID | None, OrmAttributeGroup | None] = {}

    for rule in bindings:
        attr = rule.attribute
        if predicate is not None and not predicate(rule, attr):
            continue
        gid = attr.group_id
        groups_map[gid].append((rule, attr))
        if gid not in group_info:
            group_info[gid] = attr.group

    sorted_groups = sorted(
        groups_map.items(),
        key=lambda item: (group_info.get(item[0]) or _null_group()).sort_order,
    )

    return [(gid, group_info.get(gid), items) for gid, items in sorted_groups]


# ---------------------------------------------------------------------------
# Cache invalidation
# ---------------------------------------------------------------------------


async def invalidate_storefront_cache(
    cache: ICacheService,
    category_id: uuid.UUID,
) -> None:
    """Delete all storefront cache entries for the given category.

    Must be called whenever data that feeds the storefront queries changes:
      - Attribute metadata updates  (name, flags, ui_type, …)
      - Attribute value additions / updates / deletions
      - Category-attribute binding changes  (bind, unbind, reorder,
        flag_overrides, filter_settings, requirement_level)

    The category tree cache (``CATEGORY_TREE_CACHE_KEY``) is handled
    separately in the category CRUD handlers; this function only covers
    the per-category storefront attribute caches.
    """
    keys = [
        storefront_filters_cache_key(category_id),
        storefront_card_cache_key(category_id),
        storefront_comparison_cache_key(category_id),
    ]
    await cache.delete_many(keys)
