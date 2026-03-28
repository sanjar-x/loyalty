"""
Fake repository implementations for all 10 catalog domain interfaces.

Each fake extends ``FakeRepository`` (for ICatalogRepository-based interfaces)
or implements the ABC directly (for non-ICatalogRepository interfaces like
IAttributeValueRepository, IProductAttributeValueRepository, IMediaAssetRepository).

Commonly-used query methods have real dict-scanning logic. Less common methods
raise ``NotImplementedError`` with a message indicating which phase will need them.

Cross-repo references (_product_store, _child_store, _attribute_store) are
wired by ``FakeUnitOfWork.__init__()`` after all repos are constructed.
"""

from __future__ import annotations

import uuid
from typing import Any

from src.modules.catalog.domain.entities import (
    Attribute as DomainAttribute,
)
from src.modules.catalog.domain.entities import (
    AttributeGroup as DomainAttributeGroup,
)
from src.modules.catalog.domain.entities import (
    AttributeTemplate as DomainAttributeTemplate,
)
from src.modules.catalog.domain.entities import (
    AttributeValue as DomainAttributeValue,
)
from src.modules.catalog.domain.entities import Brand as DomainBrand
from src.modules.catalog.domain.entities import Category as DomainCategory
from src.modules.catalog.domain.entities import MediaAsset as DomainMediaAsset
from src.modules.catalog.domain.entities import Product as DomainProduct
from src.modules.catalog.domain.entities import (
    ProductAttributeValue as DomainProductAttributeValue,
)
from src.modules.catalog.domain.entities import (
    TemplateAttributeBinding as DomainTemplateAttributeBinding,
)
from src.modules.catalog.domain.interfaces import (
    IAttributeGroupRepository,
    IAttributeRepository,
    IAttributeTemplateRepository,
    IAttributeValueRepository,
    IBrandRepository,
    ICategoryRepository,
    IMediaAssetRepository,
    IProductAttributeValueRepository,
    IProductRepository,
    ITemplateAttributeBindingRepository,
)


# ============================================================================
# 1. FakeBrandRepository
# ============================================================================


class FakeBrandRepository(IBrandRepository):
    """In-memory Brand repository with dict-based storage.

    Cross-repo reference ``_product_store`` is wired by FakeUoW for
    ``has_products()`` checks.
    """

    def __init__(self) -> None:
        self._store: dict[uuid.UUID, DomainBrand] = {}
        self._product_store: dict[uuid.UUID, DomainProduct] = {}

    async def add(self, entity: DomainBrand) -> DomainBrand:
        self._store[entity.id] = entity
        return entity

    async def get(self, entity_id: uuid.UUID) -> DomainBrand | None:
        return self._store.get(entity_id)

    async def update(self, entity: DomainBrand) -> DomainBrand:
        self._store[entity.id] = entity
        return entity

    async def delete(self, entity_id: uuid.UUID) -> None:
        self._store.pop(entity_id, None)

    async def check_slug_exists(self, slug: str) -> bool:
        return any(b.slug == slug for b in self._store.values())

    async def get_for_update(self, brand_id: uuid.UUID) -> DomainBrand | None:
        return self._store.get(brand_id)

    async def check_slug_exists_excluding(
        self, slug: str, exclude_id: uuid.UUID
    ) -> bool:
        return any(
            b.slug == slug and b.id != exclude_id for b in self._store.values()
        )

    async def has_products(self, brand_id: uuid.UUID) -> bool:
        return any(
            p.brand_id == brand_id and p.deleted_at is None
            for p in self._product_store.values()
        )

    async def check_name_exists(self, name: str) -> bool:
        return any(b.name == name for b in self._store.values())

    async def check_name_exists_excluding(
        self, name: str, exclude_id: uuid.UUID
    ) -> bool:
        return any(
            b.name == name and b.id != exclude_id for b in self._store.values()
        )


# ============================================================================
# 2. FakeCategoryRepository
# ============================================================================


class FakeCategoryRepository(ICategoryRepository):
    """In-memory Category repository with dict-based storage.

    Cross-repo references ``_product_store`` and ``_child_store`` are
    wired by FakeUoW for ``has_products()`` and ``has_children()`` checks.
    """

    def __init__(self) -> None:
        self._store: dict[uuid.UUID, DomainCategory] = {}
        self._product_store: dict[uuid.UUID, DomainProduct] = {}
        self._child_store: dict[uuid.UUID, DomainCategory] = {}

    async def add(self, entity: DomainCategory) -> DomainCategory:
        self._store[entity.id] = entity
        return entity

    async def get(self, entity_id: uuid.UUID) -> DomainCategory | None:
        return self._store.get(entity_id)

    async def update(self, entity: DomainCategory) -> DomainCategory:
        self._store[entity.id] = entity
        return entity

    async def delete(self, entity_id: uuid.UUID) -> None:
        self._store.pop(entity_id, None)

    async def get_all_ordered(self) -> list[DomainCategory]:
        return sorted(self._store.values(), key=lambda c: (c.level, c.sort_order))

    async def check_slug_exists(
        self, slug: str, parent_id: uuid.UUID | None
    ) -> bool:
        return any(
            c.slug == slug and c.parent_id == parent_id
            for c in self._store.values()
        )

    async def get_for_update(
        self, category_id: uuid.UUID
    ) -> DomainCategory | None:
        return self._store.get(category_id)

    async def check_slug_exists_excluding(
        self, slug: str, parent_id: uuid.UUID | None, exclude_id: uuid.UUID
    ) -> bool:
        return any(
            c.slug == slug and c.parent_id == parent_id and c.id != exclude_id
            for c in self._store.values()
        )

    async def has_children(self, category_id: uuid.UUID) -> bool:
        return any(
            c.parent_id == category_id for c in self._child_store.values()
        )

    async def has_products(self, category_id: uuid.UUID) -> bool:
        return any(
            p.primary_category_id == category_id and p.deleted_at is None
            for p in self._product_store.values()
        )

    async def update_descendants_full_slug(
        self, old_prefix: str, new_prefix: str
    ) -> None:
        raise NotImplementedError(
            "update_descendants_full_slug: fill in when Phase 4 needs it"
        )

    async def propagate_effective_template_id(
        self, category_id: uuid.UUID, effective_template_id: uuid.UUID | None
    ) -> list[uuid.UUID]:
        raise NotImplementedError(
            "propagate_effective_template_id: fill in when Phase 4 needs it"
        )


# ============================================================================
# 3. FakeAttributeGroupRepository
# ============================================================================


class FakeAttributeGroupRepository(IAttributeGroupRepository):
    """In-memory AttributeGroup repository with dict-based storage.

    Cross-repo reference ``_attribute_store`` is wired by FakeUoW for
    ``has_attributes()`` checks.
    """

    def __init__(self) -> None:
        self._store: dict[uuid.UUID, DomainAttributeGroup] = {}
        self._attribute_store: dict[uuid.UUID, DomainAttribute] = {}

    async def add(self, entity: DomainAttributeGroup) -> DomainAttributeGroup:
        self._store[entity.id] = entity
        return entity

    async def get(self, entity_id: uuid.UUID) -> DomainAttributeGroup | None:
        return self._store.get(entity_id)

    async def update(self, entity: DomainAttributeGroup) -> DomainAttributeGroup:
        self._store[entity.id] = entity
        return entity

    async def delete(self, entity_id: uuid.UUID) -> None:
        self._store.pop(entity_id, None)

    async def check_code_exists(self, code: str) -> bool:
        return any(g.code == code for g in self._store.values())

    async def get_by_code(self, code: str) -> DomainAttributeGroup | None:
        for g in self._store.values():
            if g.code == code:
                return g
        return None

    async def has_attributes(self, group_id: uuid.UUID) -> bool:
        return any(
            a.group_id == group_id for a in self._attribute_store.values()
        )

    async def move_attributes_to_group(
        self, source_group_id: uuid.UUID, target_group_id: uuid.UUID
    ) -> None:
        raise NotImplementedError(
            "move_attributes_to_group: fill in when Phase 4 needs it"
        )


# ============================================================================
# 4. FakeAttributeRepository
# ============================================================================


class FakeAttributeRepository(IAttributeRepository):
    """In-memory Attribute repository with dict-based storage."""

    def __init__(self) -> None:
        self._store: dict[uuid.UUID, DomainAttribute] = {}

    async def add(self, entity: DomainAttribute) -> DomainAttribute:
        self._store[entity.id] = entity
        return entity

    async def get(self, entity_id: uuid.UUID) -> DomainAttribute | None:
        return self._store.get(entity_id)

    async def update(self, entity: DomainAttribute) -> DomainAttribute:
        self._store[entity.id] = entity
        return entity

    async def delete(self, entity_id: uuid.UUID) -> None:
        self._store.pop(entity_id, None)

    async def get_many(
        self, ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, DomainAttribute]:
        return {
            aid: self._store[aid] for aid in ids if aid in self._store
        }

    async def get_for_update(
        self, attribute_id: uuid.UUID
    ) -> DomainAttribute | None:
        return self._store.get(attribute_id)

    async def check_code_exists(self, code: str) -> bool:
        return any(a.code == code for a in self._store.values())

    async def check_slug_exists(self, slug: str) -> bool:
        return any(a.slug == slug for a in self._store.values())

    async def has_product_attribute_values(self, attribute_id: uuid.UUID) -> bool:
        # Cross-repo reference can be added when Phase 5 needs it
        return False


# ============================================================================
# 5. FakeAttributeValueRepository
# ============================================================================


class FakeAttributeValueRepository(IAttributeValueRepository):
    """In-memory AttributeValue repository with dict-based storage.

    Not based on FakeRepository since IAttributeValueRepository is a
    separate ABC (not ICatalogRepository).
    """

    def __init__(self) -> None:
        self._store: dict[uuid.UUID, DomainAttributeValue] = {}

    async def add(self, entity: DomainAttributeValue) -> DomainAttributeValue:
        self._store[entity.id] = entity
        return entity

    async def get(self, value_id: uuid.UUID) -> DomainAttributeValue | None:
        return self._store.get(value_id)

    async def update(self, entity: DomainAttributeValue) -> DomainAttributeValue:
        self._store[entity.id] = entity
        return entity

    async def delete(self, value_id: uuid.UUID) -> None:
        self._store.pop(value_id, None)

    async def get_many(
        self, ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, DomainAttributeValue]:
        return {vid: self._store[vid] for vid in ids if vid in self._store}

    async def check_code_exists(self, attribute_id: uuid.UUID, code: str) -> bool:
        return any(
            v.attribute_id == attribute_id and v.code == code
            for v in self._store.values()
        )

    async def check_slug_exists(self, attribute_id: uuid.UUID, slug: str) -> bool:
        return any(
            v.attribute_id == attribute_id and v.slug == slug
            for v in self._store.values()
        )

    async def has_product_references(self, value_id: uuid.UUID) -> bool:
        # Would need cross-repo reference to product_attribute_values store
        return False

    async def list_ids_by_attribute(
        self, attribute_id: uuid.UUID
    ) -> set[uuid.UUID]:
        return {
            v.id
            for v in self._store.values()
            if v.attribute_id == attribute_id
        }

    async def check_codes_exist(
        self, attribute_id: uuid.UUID, codes: list[str]
    ) -> set[str]:
        return {
            v.code
            for v in self._store.values()
            if v.attribute_id == attribute_id and v.code in codes
        }

    async def check_slugs_exist(
        self, attribute_id: uuid.UUID, slugs: list[str]
    ) -> set[str]:
        return {
            v.slug
            for v in self._store.values()
            if v.attribute_id == attribute_id and v.slug in slugs
        }

    async def bulk_update_sort_order(
        self, updates: list[tuple[uuid.UUID, int]]
    ) -> None:
        for value_id, new_sort_order in updates:
            if value_id in self._store:
                self._store[value_id].sort_order = new_sort_order


# ============================================================================
# 6. FakeProductRepository
# ============================================================================


class FakeProductRepository(IProductRepository):
    """In-memory Product repository with dict-based storage."""

    def __init__(self) -> None:
        self._store: dict[uuid.UUID, DomainProduct] = {}

    async def add(self, entity: DomainProduct) -> DomainProduct:
        self._store[entity.id] = entity
        return entity

    async def get(self, entity_id: uuid.UUID) -> DomainProduct | None:
        return self._store.get(entity_id)

    async def update(self, entity: DomainProduct) -> DomainProduct:
        self._store[entity.id] = entity
        return entity

    async def delete(self, entity_id: uuid.UUID) -> None:
        self._store.pop(entity_id, None)

    async def check_slug_exists(self, slug: str) -> bool:
        return any(
            p.slug == slug and p.deleted_at is None
            for p in self._store.values()
        )

    async def check_slug_exists_excluding(
        self, slug: str, exclude_id: uuid.UUID
    ) -> bool:
        return any(
            p.slug == slug and p.id != exclude_id and p.deleted_at is None
            for p in self._store.values()
        )

    async def get_for_update_with_variants(
        self, product_id: uuid.UUID
    ) -> DomainProduct | None:
        # In-memory entities already carry variants
        return self._store.get(product_id)

    async def get_with_variants(
        self, product_id: uuid.UUID
    ) -> DomainProduct | None:
        # In-memory entities already carry variants
        return self._store.get(product_id)

    async def check_sku_code_exists(
        self, sku_code: str, exclude_sku_id: uuid.UUID | None = None
    ) -> bool:
        for product in self._store.values():
            if product.deleted_at is not None:
                continue
            for variant in product.variants:
                if variant.deleted_at is not None:
                    continue
                for sku in variant.skus:
                    if sku.deleted_at is not None:
                        continue
                    if sku.sku_code == sku_code:
                        if exclude_sku_id is not None and sku.id == exclude_sku_id:
                            continue
                        return True
        return False


# ============================================================================
# 7. FakeProductAttributeValueRepository
# ============================================================================


class FakeProductAttributeValueRepository(IProductAttributeValueRepository):
    """In-memory ProductAttributeValue repository with dict-based storage."""

    def __init__(self) -> None:
        self._store: dict[uuid.UUID, DomainProductAttributeValue] = {}

    async def add(
        self, entity: DomainProductAttributeValue
    ) -> DomainProductAttributeValue:
        self._store[entity.id] = entity
        return entity

    async def get(
        self, pav_id: uuid.UUID
    ) -> DomainProductAttributeValue | None:
        return self._store.get(pav_id)

    async def delete(self, pav_id: uuid.UUID) -> None:
        self._store.pop(pav_id, None)

    async def list_by_product(
        self, product_id: uuid.UUID
    ) -> list[DomainProductAttributeValue]:
        return [
            pav
            for pav in self._store.values()
            if pav.product_id == product_id
        ]

    async def get_by_product_and_attribute(
        self, product_id: uuid.UUID, attribute_id: uuid.UUID
    ) -> DomainProductAttributeValue | None:
        for pav in self._store.values():
            if pav.product_id == product_id and pav.attribute_id == attribute_id:
                return pav
        return None

    async def check_assignment_exists(
        self, product_id: uuid.UUID, attribute_id: uuid.UUID
    ) -> bool:
        return any(
            pav.product_id == product_id and pav.attribute_id == attribute_id
            for pav in self._store.values()
        )

    async def check_assignments_exist_bulk(
        self, product_id: uuid.UUID, attribute_ids: list[uuid.UUID]
    ) -> set[uuid.UUID]:
        return {
            pav.attribute_id
            for pav in self._store.values()
            if pav.product_id == product_id and pav.attribute_id in attribute_ids
        }


# ============================================================================
# 8. FakeMediaAssetRepository
# ============================================================================


class FakeMediaAssetRepository(IMediaAssetRepository):
    """In-memory MediaAsset repository with dict-based storage."""

    def __init__(self) -> None:
        self._store: dict[uuid.UUID, DomainMediaAsset] = {}

    async def add(self, media: DomainMediaAsset) -> DomainMediaAsset:
        self._store[media.id] = media
        return media

    async def get(self, media_id: uuid.UUID) -> DomainMediaAsset | None:
        return self._store.get(media_id)

    async def get_for_update(
        self, media_id: uuid.UUID
    ) -> DomainMediaAsset | None:
        return self._store.get(media_id)

    async def update(self, media: DomainMediaAsset) -> DomainMediaAsset:
        self._store[media.id] = media
        return media

    async def delete(self, media_id: uuid.UUID) -> None:
        self._store.pop(media_id, None)

    async def list_by_product(
        self, product_id: uuid.UUID
    ) -> list[DomainMediaAsset]:
        return sorted(
            [m for m in self._store.values() if m.product_id == product_id],
            key=lambda m: (
                m.variant_id if m.variant_id is not None else uuid.UUID(int=0),
                m.sort_order,
            ),
        )

    async def list_by_storage_ids(
        self,
        storage_object_ids: list[uuid.UUID],
    ) -> list[DomainMediaAsset]:
        sid_set = set(storage_object_ids)
        return [
            m
            for m in self._store.values()
            if m.storage_object_id in sid_set
        ]

    async def delete_by_product(
        self,
        product_id: uuid.UUID,
    ) -> list[uuid.UUID]:
        to_remove = [
            m for m in self._store.values() if m.product_id == product_id
        ]
        storage_ids = [
            m.storage_object_id
            for m in to_remove
            if m.storage_object_id is not None
        ]
        for m in to_remove:
            self._store.pop(m.id, None)
        return storage_ids


# ============================================================================
# 9. FakeAttributeTemplateRepository
# ============================================================================


class FakeAttributeTemplateRepository(IAttributeTemplateRepository):
    """In-memory AttributeTemplate repository with dict-based storage."""

    def __init__(self) -> None:
        self._store: dict[uuid.UUID, DomainAttributeTemplate] = {}

    async def add(
        self, entity: DomainAttributeTemplate
    ) -> DomainAttributeTemplate:
        self._store[entity.id] = entity
        return entity

    async def get(
        self, entity_id: uuid.UUID
    ) -> DomainAttributeTemplate | None:
        return self._store.get(entity_id)

    async def update(
        self, entity: DomainAttributeTemplate
    ) -> DomainAttributeTemplate:
        self._store[entity.id] = entity
        return entity

    async def delete(self, entity_id: uuid.UUID) -> None:
        self._store.pop(entity_id, None)

    async def check_code_exists(self, code: str) -> bool:
        return any(t.code == code for t in self._store.values())

    async def has_category_references(self, template_id: uuid.UUID) -> bool:
        # Would need cross-repo reference to category store; returns False
        return False

    async def get_category_ids_by_template_ids(
        self, template_ids: list[uuid.UUID]
    ) -> list[uuid.UUID]:
        raise NotImplementedError(
            "get_category_ids_by_template_ids: fill in when Phase 4 needs it"
        )


# ============================================================================
# 10. FakeTemplateAttributeBindingRepository
# ============================================================================


class FakeTemplateAttributeBindingRepository(ITemplateAttributeBindingRepository):
    """In-memory TemplateAttributeBinding repository with dict-based storage."""

    def __init__(self) -> None:
        self._store: dict[uuid.UUID, DomainTemplateAttributeBinding] = {}

    async def add(
        self, entity: DomainTemplateAttributeBinding
    ) -> DomainTemplateAttributeBinding:
        self._store[entity.id] = entity
        return entity

    async def get(
        self, entity_id: uuid.UUID
    ) -> DomainTemplateAttributeBinding | None:
        return self._store.get(entity_id)

    async def update(
        self, entity: DomainTemplateAttributeBinding
    ) -> DomainTemplateAttributeBinding:
        self._store[entity.id] = entity
        return entity

    async def delete(self, entity_id: uuid.UUID) -> None:
        self._store.pop(entity_id, None)

    async def check_binding_exists(
        self, template_id: uuid.UUID, attribute_id: uuid.UUID
    ) -> bool:
        return any(
            b.template_id == template_id and b.attribute_id == attribute_id
            for b in self._store.values()
        )

    async def list_ids_by_template(
        self, template_id: uuid.UUID
    ) -> set[uuid.UUID]:
        return {
            b.id
            for b in self._store.values()
            if b.template_id == template_id
        }

    async def get_bindings_for_templates(
        self, template_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, list[DomainTemplateAttributeBinding]]:
        raise NotImplementedError(
            "get_bindings_for_templates: fill in when Phase 5 needs it"
        )

    async def bulk_update_sort_order(
        self, updates: list[tuple[uuid.UUID, int]]
    ) -> None:
        raise NotImplementedError(
            "bulk_update_sort_order: fill in when Phase 5 needs it"
        )

    async def has_bindings_for_attribute(
        self, attribute_id: uuid.UUID
    ) -> bool:
        return any(
            b.attribute_id == attribute_id for b in self._store.values()
        )

    async def get_template_ids_for_attribute(
        self, attribute_id: uuid.UUID
    ) -> list[uuid.UUID]:
        raise NotImplementedError(
            "get_template_ids_for_attribute: fill in when Phase 5 needs it"
        )
