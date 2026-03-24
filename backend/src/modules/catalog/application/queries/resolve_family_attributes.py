"""
Query handler: resolve effective attributes for an attribute family.

Walks the ancestor chain from root to target family, applying bindings,
overrides, and exclusions at each level to produce the final effective
attribute set. Results are cached in Redis.
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
    family_effective_attrs_cache_key,
)
from src.modules.catalog.domain.exceptions import AttributeFamilyNotFoundError
from src.modules.catalog.domain.interfaces import (
    IAttributeFamilyRepository,
    IFamilyAttributeBindingRepository,
    IFamilyAttributeExclusionRepository,
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
    flag_overrides: dict[str, Any] | None = None
    filter_settings: dict[str, Any] | None = None
    source_family_id: uuid.UUID
    is_overridden: bool = False
    values: list[EffectiveValueReadModel] = []
    sort_order: int = 0

    # Global attribute flags (from the attribute definition itself).
    # These serve as defaults when flag_overrides does not specify a value.
    is_filterable: bool = False
    is_searchable: bool = False
    is_comparable: bool = False
    is_visible_on_card: bool = False
    is_visible_in_catalog: bool = False
    search_weight: int = 5
    group_id: uuid.UUID | None = None
    group_code: str | None = None
    group_name_i18n: dict[str, Any] = {}
    group_sort_order: int = 0


class EffectiveAttributeSetReadModel(BaseModel):
    """Complete effective attribute set for a family."""

    family_id: uuid.UUID
    attributes: list[EffectiveAttributeReadModel]


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------


async def invalidate_family_effective_cache(
    cache: ICacheService,
    family_repo: IAttributeFamilyRepository,
    family_id: uuid.UUID,
) -> None:
    """Invalidate effective attribute cache for a family and all its descendants."""
    descendant_ids = await family_repo.get_descendant_ids(family_id)
    all_ids = [family_id, *descendant_ids]
    keys = [family_effective_attrs_cache_key(fid) for fid in all_ids]
    await cache.delete_many(keys)


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------


class ResolveFamilyAttributesHandler:
    """Resolve the effective attribute set for a family with inheritance."""

    def __init__(
        self,
        session: AsyncSession,
        family_repo: IAttributeFamilyRepository,
        binding_repo: IFamilyAttributeBindingRepository,
        exclusion_repo: IFamilyAttributeExclusionRepository,
        cache: ICacheService,
        logger: ILogger,
    ) -> None:
        self._session = session
        self._family_repo = family_repo
        self._binding_repo = binding_repo
        self._exclusion_repo = exclusion_repo
        self._cache = cache
        self._logger = logger.bind(handler="ResolveFamilyAttributesHandler")

    async def handle(self, family_id: uuid.UUID) -> EffectiveAttributeSetReadModel:
        """Return the effective attribute set for the given family."""
        # 1. Check cache
        cache_key = family_effective_attrs_cache_key(family_id)
        cached = await self._cache.get(cache_key)
        if cached is not None:
            return EffectiveAttributeSetReadModel.model_validate(json.loads(cached))

        # 2. Load ancestor chain
        chain = await self._family_repo.get_ancestor_chain(family_id)
        if not chain:
            raise AttributeFamilyNotFoundError(family_id=family_id)

        # 3. Load all bindings and exclusions for the chain
        chain_ids = [f.id for f in chain]
        all_bindings = await self._binding_repo.get_bindings_for_families(chain_ids)
        all_exclusions = await self._exclusion_repo.get_exclusions_for_families(chain_ids)

        # 4. Merge: walk root -> leaf
        # effective maps attribute_id -> (binding, source_family_id, is_overridden)
        effective: dict[uuid.UUID, tuple] = {}

        for family in chain:
            # Apply exclusions first -- remove inherited attrs
            for excluded_attr_id in all_exclusions.get(family.id, set()):
                effective.pop(excluded_attr_id, None)

            # Apply own bindings -- add or override
            for binding in all_bindings.get(family.id, []):
                is_overridden = binding.attribute_id in effective
                effective[binding.attribute_id] = (binding, family.id, is_overridden)

        # 5. Load attribute metadata for the effective set
        effective_attr_ids = list(effective.keys())
        if not effective_attr_ids:
            result = EffectiveAttributeSetReadModel(family_id=family_id, attributes=[])
            await self._cache.set(
                cache_key, json.dumps(result.model_dump(mode="json")), ttl=STOREFRONT_CACHE_TTL
            )
            return result

        stmt = (
            select(OrmAttribute)
            .where(OrmAttribute.id.in_(effective_attr_ids))
            .options(selectinload(OrmAttribute.values), selectinload(OrmAttribute.group))
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
                    validation_rules=dict(orm_attr.validation_rules) if orm_attr.validation_rules else None,
                    flag_overrides=dict(binding.flag_overrides) if binding.flag_overrides else None,
                    filter_settings=dict(binding.filter_settings) if binding.filter_settings else None,
                    source_family_id=source_fid,
                    is_overridden=is_overridden,
                    values=values,
                    sort_order=binding.sort_order,
                    # Global attribute flags
                    is_filterable=orm_attr.is_filterable,
                    is_searchable=orm_attr.is_searchable,
                    is_comparable=orm_attr.is_comparable,
                    is_visible_on_card=orm_attr.is_visible_on_card,
                    is_visible_in_catalog=orm_attr.is_visible_in_catalog,
                    search_weight=orm_attr.search_weight,
                    group_id=grp.id if grp else None,
                    group_code=grp.code if grp else None,
                    group_name_i18n=(grp.name_i18n or {}) if grp else {},
                    group_sort_order=grp.sort_order if grp else 0,
                )
            )

        attributes.sort(key=lambda a: a.sort_order)

        result = EffectiveAttributeSetReadModel(
            family_id=family_id,
            attributes=attributes,
        )

        # 7. Cache
        await self._cache.set(
            cache_key,
            json.dumps(result.model_dump(mode="json")),
            ttl=STOREFRONT_CACHE_TTL,
        )

        return result
