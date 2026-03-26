"""
Query handler: resolve effective attributes for an attribute template.

Performs flat binding lookups for a template to produce the effective
attribute set.  Results are cached in Redis.
"""

import json
import uuid
from typing import Any

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.modules.catalog.application.constants import (
    STOREFRONT_CACHE_TTL,
    template_effective_attrs_cache_key,
)
from src.modules.catalog.domain.interfaces import (
    IAttributeTemplateRepository,
    ITemplateAttributeBindingRepository,
)
from src.modules.catalog.infrastructure.models import (
    Attribute as OrmAttribute,
)
from src.shared.interfaces.cache import ICacheService
from src.shared.interfaces.logger import ILogger

# ---------------------------------------------------------------------------
# Read Models
# ---------------------------------------------------------------------------


class EffectiveValueReadModel(BaseModel):
    """A single attribute value in the effective set."""

    id: uuid.UUID
    code: str
    slug: str
    value_i18n: dict[str, Any]
    meta_data: dict[str, Any]
    value_group: str | None = None
    sort_order: int


class EffectiveAttributeReadModel(BaseModel):
    """A single attribute in the effective set with full metadata."""

    attribute_id: uuid.UUID
    code: str
    slug: str
    name_i18n: dict[str, Any]
    description_i18n: dict[str, Any]
    data_type: str
    ui_type: str
    is_dictionary: bool
    level: str  # "product" or "variant"
    requirement_level: str
    validation_rules: dict[str, Any] | None = None
    filter_settings: dict[str, Any] | None = None
    source_template_id: uuid.UUID
    is_overridden: bool = False
    values: list[EffectiveValueReadModel] = []
    sort_order: int = 0

    # Global attribute flags (from the attribute definition itself).
    is_filterable: bool = False
    is_searchable: bool = False
    is_comparable: bool = False
    is_visible_on_card: bool = False
    search_weight: int = 5
    group_id: uuid.UUID | None = None
    group_code: str | None = None
    group_name_i18n: dict[str, Any] = {}
    group_sort_order: int = 0


class EffectiveAttributeSetReadModel(BaseModel):
    """Complete effective attribute set for a template."""

    template_id: uuid.UUID
    attributes: list[EffectiveAttributeReadModel]


# ---------------------------------------------------------------------------
# Shared resolution logic (used by command handlers to avoid duplication)
# ---------------------------------------------------------------------------


async def resolve_effective_attribute_ids(
    binding_repo: ITemplateAttributeBindingRepository,
    template_id: uuid.UUID,
) -> set[uuid.UUID]:
    """Resolve the set of effective attribute IDs for a template.

    Returns:
        Set of attribute UUIDs bound to this template.
    """
    all_bindings = await binding_repo.get_bindings_for_templates([template_id])
    return {b.attribute_id for b in all_bindings.get(template_id, [])}


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------


async def invalidate_template_effective_cache(
    cache: ICacheService,
    template_repo: IAttributeTemplateRepository,
    template_id: uuid.UUID,
) -> None:
    """Invalidate effective attribute cache AND storefront caches.

    When a template's bindings change, invalidate:
    1. The template effective-attribute cache for this template
    2. The per-category storefront caches for all categories that reference it
    """
    from src.modules.catalog.application.constants import (
        storefront_card_cache_key,
        storefront_comparison_cache_key,
        storefront_filters_cache_key,
        storefront_form_cache_key,
    )

    keys = [template_effective_attrs_cache_key(template_id)]

    category_ids = await template_repo.get_category_ids_by_template_ids([template_id])
    for cat_id in category_ids:
        keys.append(storefront_filters_cache_key(cat_id))
        keys.append(storefront_card_cache_key(cat_id))
        keys.append(storefront_comparison_cache_key(cat_id))
        keys.append(storefront_form_cache_key(cat_id))

    await cache.delete_many(keys)


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------


class ResolveTemplateAttributesHandler:
    """Resolve the effective attribute set for a template (flat binding lookup)."""

    def __init__(
        self,
        session: AsyncSession,
        binding_repo: ITemplateAttributeBindingRepository,
        cache: ICacheService,
        logger: ILogger,
    ) -> None:
        self._session = session
        self._binding_repo = binding_repo
        self._cache = cache
        self._logger = logger.bind(handler="ResolveTemplateAttributesHandler")

    async def handle(self, template_id: uuid.UUID) -> EffectiveAttributeSetReadModel:
        """Return the effective attribute set for the given template."""
        # 1. Check cache
        cache_key = template_effective_attrs_cache_key(template_id)
        cached = await self._cache.get(cache_key)
        if cached is not None:
            return EffectiveAttributeSetReadModel.model_validate(json.loads(cached))

        # 2. Load bindings for this template (flat — no ancestor chain walk)
        all_bindings = await self._binding_repo.get_bindings_for_templates([
            template_id
        ])
        bindings = all_bindings.get(template_id, [])

        # 4. Build effective map (simplified — no tree walk, no overrides)
        effective: dict[uuid.UUID, tuple] = {}
        for binding in bindings:
            effective[binding.attribute_id] = (binding, template_id, False)

        # 5. Load attribute metadata for the effective set
        effective_attr_ids = list(effective.keys())
        if not effective_attr_ids:
            result = EffectiveAttributeSetReadModel(
                template_id=template_id, attributes=[]
            )
            await self._cache.set(
                cache_key,
                json.dumps(result.model_dump(mode="json")),
                ttl=STOREFRONT_CACHE_TTL,
            )
            return result

        stmt = (
            select(OrmAttribute)
            .where(OrmAttribute.id.in_(effective_attr_ids))
            .options(
                selectinload(OrmAttribute.values), selectinload(OrmAttribute.group)
            )
        )
        attr_result = await self._session.execute(stmt)
        orm_attrs = {a.id: a for a in attr_result.unique().scalars().all()}

        # 6. Build read models
        attributes: list[EffectiveAttributeReadModel] = []
        for attr_id, (binding, source_fid, is_overridden) in effective.items():
            orm_attr = orm_attrs.get(attr_id)
            if orm_attr is None:
                continue  # attribute was deleted, skip

            values = []
            if orm_attr.is_dictionary:
                values = [
                    EffectiveValueReadModel(
                        id=v.id,
                        code=v.code,
                        slug=v.slug,
                        value_i18n=v.value_i18n or {},
                        meta_data=v.meta_data or {},
                        value_group=v.value_group,
                        sort_order=v.sort_order,
                    )
                    for v in sorted(orm_attr.values, key=lambda x: x.sort_order)
                    if v.is_active
                ]

            grp = orm_attr.group
            attributes.append(
                EffectiveAttributeReadModel(
                    attribute_id=orm_attr.id,
                    code=orm_attr.code,
                    slug=orm_attr.slug,
                    name_i18n=orm_attr.name_i18n or {},
                    description_i18n=orm_attr.description_i18n or {},
                    data_type=orm_attr.data_type.value,
                    ui_type=orm_attr.ui_type.value,
                    is_dictionary=orm_attr.is_dictionary,
                    level=orm_attr.level.value,
                    requirement_level=binding.requirement_level.value,
                    validation_rules=dict(orm_attr.validation_rules)
                    if orm_attr.validation_rules
                    else None,
                    filter_settings=dict(binding.filter_settings)
                    if binding.filter_settings
                    else None,
                    source_template_id=source_fid,
                    is_overridden=is_overridden,
                    values=values,
                    sort_order=binding.sort_order,
                    # Global attribute flags
                    is_filterable=orm_attr.is_filterable,
                    is_searchable=orm_attr.is_searchable,
                    is_comparable=orm_attr.is_comparable,
                    is_visible_on_card=orm_attr.is_visible_on_card,
                    search_weight=orm_attr.search_weight,
                    group_id=grp.id if grp else None,
                    group_code=grp.code if grp else None,
                    group_name_i18n=(grp.name_i18n or {}) if grp else {},
                    group_sort_order=grp.sort_order if grp else 0,
                )
            )

        attributes.sort(key=lambda a: a.sort_order)

        result = EffectiveAttributeSetReadModel(
            template_id=template_id,
            attributes=attributes,
        )

        # 7. Cache
        await self._cache.set(
            cache_key,
            json.dumps(result.model_dump(mode="json")),
            ttl=STOREFRONT_CACHE_TTL,
        )

        return result
