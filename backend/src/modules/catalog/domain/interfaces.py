"""
Catalog repository port interfaces.

Defines the abstract repository contracts for Brand, Category, Product,
Attribute, and AttributeGroup aggregates. The application layer depends
only on these interfaces; concrete implementations live in the
infrastructure layer.

Typical usage:
    class CreateBrandHandler:
        def __init__(self, repo: IBrandRepository) -> None:
            self._repo = repo
"""

import uuid
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from src.modules.catalog.domain.entities import Attribute as DomainAttribute
from src.modules.catalog.domain.entities import AttributeGroup as DomainAttributeGroup
from src.modules.catalog.domain.entities import AttributeValue as DomainAttributeValue
from src.modules.catalog.domain.entities import Brand as DomainBrand
from src.modules.catalog.domain.entities import Category as DomainCategory
from src.modules.catalog.domain.entities import (
    AttributeFamily as DomainAttributeFamily,
)
from src.modules.catalog.domain.entities import (
    FamilyAttributeBinding as DomainFamilyAttributeBinding,
)
from src.modules.catalog.domain.entities import (
    FamilyAttributeExclusion as DomainFamilyAttributeExclusion,
)
from src.modules.catalog.domain.entities import MediaAsset as DomainMediaAsset
from src.modules.catalog.domain.entities import Product as DomainProduct
from src.modules.catalog.domain.entities import (
    ProductAttributeValue as DomainProductAttributeValue,
)


class ICatalogRepository[T](ABC):
    """Generic CRUD repository contract for catalog aggregates.

    Type parameter ``T`` is the domain entity type (e.g. ``DomainBrand``).
    Module-specific repositories extend this with additional query methods.
    """

    @abstractmethod
    async def add(self, entity: T) -> T:
        """Persist a new aggregate and return it with any generated fields."""
        pass

    @abstractmethod
    async def get(self, entity_id: uuid.UUID) -> T | None:
        """Retrieve an aggregate by its unique identifier."""
        pass

    @abstractmethod
    async def update(self, entity: T) -> T:
        """Persist changes to an existing aggregate."""
        pass

    @abstractmethod
    async def delete(self, entity_id: uuid.UUID) -> None:
        """Delete an aggregate by its unique identifier."""
        pass


class IBrandRepository(ICatalogRepository[DomainBrand]):
    """Repository contract for the Brand aggregate."""

    @abstractmethod
    async def check_slug_exists(self, slug: str) -> bool:
        """Check whether a brand with the given slug already exists."""
        pass

    @abstractmethod
    async def get_for_update(self, brand_id: uuid.UUID) -> DomainBrand | None:
        """Retrieve a brand with a pessimistic lock (SELECT FOR UPDATE)."""
        pass

    @abstractmethod
    async def check_slug_exists_excluding(
        self, slug: str, exclude_id: uuid.UUID
    ) -> bool:
        """Check if a slug is taken by another brand (excluding given ID)."""
        pass

    @abstractmethod
    async def get_by_slug(self, slug: str) -> DomainBrand | None:
        """Retrieve a brand by its URL slug, or ``None``."""
        pass

    @abstractmethod
    async def has_products(self, brand_id: uuid.UUID) -> bool:
        """Check whether any non-deleted products reference this brand."""
        pass


class ICategoryRepository(ICatalogRepository[DomainCategory]):
    """Repository contract for the Category aggregate."""

    @abstractmethod
    async def get_all_ordered(self) -> list[DomainCategory]:
        """Retrieve the full category tree ordered by level and sort_order."""
        pass

    @abstractmethod
    async def check_slug_exists(self, slug: str, parent_id: uuid.UUID | None) -> bool:
        """Check whether a category slug exists at the given parent level."""
        pass

    @abstractmethod
    async def get_for_update(self, category_id: uuid.UUID) -> DomainCategory | None:
        """Retrieve a category with a pessimistic lock (SELECT FOR UPDATE)."""
        pass

    @abstractmethod
    async def check_slug_exists_excluding(
        self, slug: str, parent_id: uuid.UUID | None, exclude_id: uuid.UUID
    ) -> bool:
        """Check if a slug is taken by another category at the same level."""
        pass

    @abstractmethod
    async def has_children(self, category_id: uuid.UUID) -> bool:
        """Check whether a category has any child categories."""
        pass

    @abstractmethod
    async def has_products(self, category_id: uuid.UUID) -> bool:
        """Check whether any non-deleted products reference this category."""
        pass

    @abstractmethod
    async def update_descendants_full_slug(
        self, old_prefix: str, new_prefix: str
    ) -> None:
        """Bulk-update full_slug for all descendants when a parent's slug changes."""
        pass


class IAttributeGroupRepository(ICatalogRepository[DomainAttributeGroup]):
    """Repository contract for the AttributeGroup aggregate."""

    @abstractmethod
    async def check_code_exists(self, code: str) -> bool:
        """Check whether a group with the given code already exists."""
        pass

    @abstractmethod
    async def get_by_code(self, code: str) -> DomainAttributeGroup | None:
        """Retrieve an attribute group by its unique code."""
        pass

    @abstractmethod
    async def has_attributes(self, group_id: uuid.UUID) -> bool:
        """Check whether the group contains any attributes."""
        pass

    @abstractmethod
    async def move_attributes_to_group(
        self, source_group_id: uuid.UUID, target_group_id: uuid.UUID
    ) -> None:
        """Bulk-move all attributes from one group to another."""
        pass


class IAttributeRepository(ICatalogRepository[DomainAttribute]):
    """Repository contract for the Attribute aggregate."""

    @abstractmethod
    async def get_for_update(self, attribute_id: uuid.UUID) -> DomainAttribute | None:
        """Retrieve an attribute with a pessimistic lock (SELECT FOR UPDATE)."""
        pass

    @abstractmethod
    async def check_code_exists(self, code: str) -> bool:
        """Check whether an attribute with the given code already exists."""
        pass

    @abstractmethod
    async def check_slug_exists(self, slug: str) -> bool:
        """Check whether an attribute with the given slug already exists."""
        pass

    @abstractmethod
    async def check_code_exists_excluding(
        self, code: str, exclude_id: uuid.UUID
    ) -> bool:
        """Check if a code is taken by another attribute (excluding given ID)."""
        pass

    @abstractmethod
    async def check_slug_exists_excluding(
        self, slug: str, exclude_id: uuid.UUID
    ) -> bool:
        """Check if a slug is taken by another attribute (excluding given ID)."""
        pass

    @abstractmethod
    async def get_by_slug(self, slug: str) -> DomainAttribute | None:
        """Retrieve an attribute by its URL slug."""
        pass

    @abstractmethod
    async def has_product_attribute_values(self, attribute_id: uuid.UUID) -> bool:
        """Check whether any products reference this attribute."""
        pass


class IAttributeValueRepository(ABC):
    """Repository contract for AttributeValue entities (children of Attribute)."""

    @abstractmethod
    async def add(self, entity: DomainAttributeValue) -> DomainAttributeValue:
        """Persist a new attribute value."""
        pass

    @abstractmethod
    async def get(self, value_id: uuid.UUID) -> DomainAttributeValue | None:
        """Retrieve an attribute value by its unique identifier."""
        pass

    @abstractmethod
    async def update(self, entity: DomainAttributeValue) -> DomainAttributeValue:
        """Persist changes to an existing attribute value."""
        pass

    @abstractmethod
    async def delete(self, value_id: uuid.UUID) -> None:
        """Delete an attribute value by its unique identifier."""
        pass

    @abstractmethod
    async def check_code_exists(self, attribute_id: uuid.UUID, code: str) -> bool:
        """Check if a code is taken within the given attribute."""
        pass

    @abstractmethod
    async def check_slug_exists(self, attribute_id: uuid.UUID, slug: str) -> bool:
        """Check if a slug is taken within the given attribute."""
        pass

    @abstractmethod
    async def check_code_exists_excluding(
        self, attribute_id: uuid.UUID, code: str, exclude_id: uuid.UUID
    ) -> bool:
        """Check if a code is taken by another value within the attribute."""
        pass

    @abstractmethod
    async def check_slug_exists_excluding(
        self, attribute_id: uuid.UUID, slug: str, exclude_id: uuid.UUID
    ) -> bool:
        """Check if a slug is taken by another value within the attribute."""
        pass

    @abstractmethod
    async def has_product_references(self, value_id: uuid.UUID) -> bool:
        """Check whether any products reference this attribute value."""
        pass

    @abstractmethod
    async def list_ids_by_attribute(self, attribute_id: uuid.UUID) -> set[uuid.UUID]:
        """Return the set of value IDs belonging to the given attribute."""
        pass

    @abstractmethod
    async def bulk_update_sort_order(
        self, updates: list[tuple[uuid.UUID, int]]
    ) -> None:
        """Bulk-update sort_order for multiple values atomically.

        Args:
            updates: List of (value_id, new_sort_order) tuples.
        """
        pass


class IProductRepository(ICatalogRepository[DomainProduct]):
    """Repository contract for the Product aggregate.

    Extends the generic CRUD base with slug-based lookups,
    pessimistic locking, and eager SKU loading.
    """

    @abstractmethod
    async def get_by_slug(self, slug: str) -> DomainProduct | None:
        """Retrieve a product by its URL slug."""
        pass

    @abstractmethod
    async def check_slug_exists(self, slug: str) -> bool:
        """Check whether a product with the given slug already exists."""
        pass

    @abstractmethod
    async def check_slug_exists_excluding(
        self, slug: str, exclude_id: uuid.UUID
    ) -> bool:
        """Check if a slug is taken by another product (excluding given ID)."""
        pass

    @abstractmethod
    async def get_for_update(self, product_id: uuid.UUID) -> DomainProduct | None:
        """Retrieve a product with a pessimistic lock (SELECT FOR UPDATE)."""
        pass

    @abstractmethod
    async def get_for_update_with_variants(
        self, product_id: uuid.UUID
    ) -> DomainProduct | None:
        """Retrieve a product with pessimistic lock AND eagerly loaded variants/SKUs."""
        pass

    @abstractmethod
    async def get_with_variants(self, product_id: uuid.UUID) -> DomainProduct | None:
        """Retrieve a product with eagerly loaded variant and SKU child entities."""
        pass

    @abstractmethod
    async def check_sku_code_exists(
        self, sku_code: str, exclude_sku_id: uuid.UUID | None = None
    ) -> bool:
        """Check whether a non-deleted SKU with the given code already exists.

        Args:
            sku_code: The SKU code to check.
            exclude_sku_id: Optional SKU ID to exclude from the check
                (used during updates to ignore the SKU being updated).
        """
        pass


class IProductAttributeValueRepository(ABC):
    """Repository contract for ProductAttributeValue entities.

    Manages product-level EAV assignments -- linking products to
    attribute dictionary values. This is a child-entity repository
    (not an aggregate root repository).
    """

    @abstractmethod
    async def add(
        self, entity: DomainProductAttributeValue
    ) -> DomainProductAttributeValue:
        """Persist a new product attribute assignment."""
        pass

    @abstractmethod
    async def get(self, pav_id: uuid.UUID) -> DomainProductAttributeValue | None:
        """Retrieve a product attribute value by its unique identifier."""
        pass

    @abstractmethod
    async def delete(self, pav_id: uuid.UUID) -> None:
        """Delete a product attribute assignment by its unique identifier."""
        pass

    @abstractmethod
    async def list_by_product(
        self, product_id: uuid.UUID
    ) -> list[DomainProductAttributeValue]:
        """List all attribute assignments for a given product."""
        pass

    @abstractmethod
    async def get_by_product_and_attribute(
        self, product_id: uuid.UUID, attribute_id: uuid.UUID
    ) -> DomainProductAttributeValue | None:
        """Retrieve a product attribute value by the product+attribute pair."""
        pass

    @abstractmethod
    async def check_assignment_exists(
        self, product_id: uuid.UUID, attribute_id: uuid.UUID
    ) -> bool:
        """Check whether a product+attribute pair already exists (duplicate guard)."""
        pass


class IMediaAssetRepository(ABC):
    """Repository contract for MediaAsset entities."""

    @abstractmethod
    async def add(self, media: DomainMediaAsset) -> DomainMediaAsset:
        """Persist a new media asset and return it."""
        pass

    @abstractmethod
    async def get(self, media_id: uuid.UUID) -> DomainMediaAsset | None:
        """Retrieve a media asset by ID."""
        pass

    @abstractmethod
    async def get_for_update(self, media_id: uuid.UUID) -> DomainMediaAsset | None:
        """Retrieve a media asset with row-level lock (SELECT FOR UPDATE)."""
        pass

    @abstractmethod
    async def update(self, media: DomainMediaAsset) -> DomainMediaAsset:
        """Persist changes to an existing media asset and return it."""
        pass

    @abstractmethod
    async def delete(self, media_id: uuid.UUID) -> None:
        """Delete a media asset by ID."""
        pass

    @abstractmethod
    async def list_by_product(self, product_id: uuid.UUID) -> list[DomainMediaAsset]:
        """List all media assets for a product, ordered by (variant_id, sort_order)."""
        pass

    @abstractmethod
    async def list_by_variant(self, variant_id: uuid.UUID) -> list[DomainMediaAsset]:
        """List all media assets for a specific variant, ordered by sort_order."""
        pass

    @abstractmethod
    async def has_main_for_variant(
        self,
        product_id: uuid.UUID,
        variant_id: uuid.UUID | None,
    ) -> bool:
        """Check if a MAIN media asset already exists for this product/variant combo."""
        pass

    @abstractmethod
    async def list_by_storage_ids(
        self, storage_object_ids: list[uuid.UUID],
    ) -> list[DomainMediaAsset]:
        """Get media assets by their storage_object_ids."""
        ...

    @abstractmethod
    async def delete_by_product(
        self, product_id: uuid.UUID,
    ) -> list[uuid.UUID]:
        """Delete all media for a product. Returns storage_object_ids for cleanup."""
        ...


class IAttributeFamilyRepository(ICatalogRepository[DomainAttributeFamily]):
    """Repository contract for the AttributeFamily aggregate."""

    @abstractmethod
    async def check_code_exists(self, code: str) -> bool:
        """Check whether a family with the given code already exists."""
        pass

    @abstractmethod
    async def check_code_exists_excluding(
        self, code: str, exclude_id: uuid.UUID
    ) -> bool:
        """Check if a code is taken by another family."""
        pass

    @abstractmethod
    async def has_children(self, family_id: uuid.UUID) -> bool:
        """Check whether a family has any child families."""
        pass

    @abstractmethod
    async def has_category_references(self, family_id: uuid.UUID) -> bool:
        """Check whether any categories reference this family."""
        pass

    @abstractmethod
    async def get_all_ordered(self) -> list[DomainAttributeFamily]:
        """Retrieve all families ordered by level and sort_order."""
        pass

    @abstractmethod
    async def get_ancestor_chain(
        self, family_id: uuid.UUID
    ) -> list[DomainAttributeFamily]:
        """Return ancestor chain [root, ..., parent, self] using WITH RECURSIVE CTE."""
        pass

    @abstractmethod
    async def get_descendant_ids(self, family_id: uuid.UUID) -> list[uuid.UUID]:
        """Return all descendant family IDs using WITH RECURSIVE CTE."""
        pass

    @abstractmethod
    async def get_category_ids_by_family_ids(
        self, family_ids: list[uuid.UUID]
    ) -> list[uuid.UUID]:
        """Return category IDs that reference any of the given family IDs."""
        pass


class IFamilyAttributeBindingRepository(ICatalogRepository[DomainFamilyAttributeBinding]):
    """Repository contract for the FamilyAttributeBinding aggregate."""

    @abstractmethod
    async def check_binding_exists(
        self, family_id: uuid.UUID, attribute_id: uuid.UUID
    ) -> bool:
        """Return True if a binding for this pair already exists."""
        pass

    @abstractmethod
    async def get_by_family_and_attribute(
        self, family_id: uuid.UUID, attribute_id: uuid.UUID
    ) -> DomainFamilyAttributeBinding | None:
        """Retrieve a binding by the family+attribute pair."""
        pass

    @abstractmethod
    async def list_ids_by_family(self, family_id: uuid.UUID) -> set[uuid.UUID]:
        """Return the set of binding IDs belonging to the given family."""
        pass

    @abstractmethod
    async def get_bindings_for_families(
        self, family_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, list[DomainFamilyAttributeBinding]]:
        """Batch-load all bindings for a list of family IDs."""
        pass

    @abstractmethod
    async def bulk_update_sort_order(
        self, updates: list[tuple[uuid.UUID, int]]
    ) -> None:
        """Bulk-update sort_order for multiple bindings."""
        pass

    @abstractmethod
    async def has_bindings_for_attribute(self, attribute_id: uuid.UUID) -> bool:
        """Check whether any family binds this attribute (for deletion guard)."""
        pass


class IFamilyAttributeExclusionRepository(ICatalogRepository[DomainFamilyAttributeExclusion]):
    """Repository contract for the FamilyAttributeExclusion aggregate."""

    @abstractmethod
    async def check_exclusion_exists(
        self, family_id: uuid.UUID, attribute_id: uuid.UUID
    ) -> bool:
        """Return True if an exclusion for this pair already exists."""
        pass

    @abstractmethod
    async def get_exclusions_for_families(
        self, family_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, set[uuid.UUID]]:
        """Batch-load all exclusions for a list of family IDs.

        Returns a dict mapping family_id to a set of excluded attribute_ids.
        """
        pass


# ═══════════════════════════════════════════════════════════════════════════
# Read-only query interfaces (CQRS read side)
# ═══════════════════════════════════════════════════════════════════════════
#
# These interfaces define the contracts for query handlers in the
# application layer.  They allow query handlers to depend on abstractions
# rather than on AsyncSession or ORM models directly, satisfying the
# Dependency Inversion Principle (DIP) and the Clean Architecture
# dependency rule (application -> domain, never application -> infra).
#
# Concrete implementations live in the infrastructure layer and are
# free to use SQLAlchemy, raw SQL, Elasticsearch, or any other data
# source.  The application layer only sees the interface and the read
# models defined in ``application.queries.read_models``.
#
# NOTE: Import of read model types uses a TYPE_CHECKING guard so this
# module has no runtime dependency on the application layer (domain
# must not depend on application at runtime).  The annotations are
# strings resolved only by type-checkers.
# ═══════════════════════════════════════════════════════════════════════════

if TYPE_CHECKING:
    from src.modules.catalog.application.queries.read_models import (
        AttributeGroupListReadModel as _AttrGroupListRM,
    )
    from src.modules.catalog.application.queries.read_models import (
        AttributeGroupReadModel as _AttrGroupRM,
    )
    from src.modules.catalog.application.queries.read_models import (
        AttributeListReadModel as _AttrListRM,
    )
    from src.modules.catalog.application.queries.read_models import (
        AttributeReadModel as _AttrRM,
    )
    from src.modules.catalog.application.queries.read_models import (
        AttributeValueListReadModel as _AttrValueListRM,
    )
    from src.modules.catalog.application.queries.read_models import (
        BrandListReadModel as _BrandListRM,
    )
    from src.modules.catalog.application.queries.read_models import (
        BrandReadModel as _BrandRM,
    )
    from src.modules.catalog.application.queries.read_models import (
        CategoryListReadModel as _CategoryListRM,
    )
    from src.modules.catalog.application.queries.read_models import (
        CategoryNode as _CategoryNodeRM,
    )
    from src.modules.catalog.application.queries.read_models import (
        CategoryReadModel as _CategoryRM,
    )
    from src.modules.catalog.application.queries.read_models import (
        ProductAttributeReadModel as _ProdAttrRM,
    )
    from src.modules.catalog.application.queries.read_models import (
        ProductListReadModel as _ProductListRM,
    )
    from src.modules.catalog.application.queries.read_models import (
        ProductReadModel as _ProductRM,
    )
    from src.modules.catalog.application.queries.read_models import (
        ProductVariantReadModel as _VariantRM,
    )
    from src.modules.catalog.application.queries.read_models import (
        SKUReadModel as _SKURM,
    )
    from src.modules.catalog.application.queries.read_models import (
        StorefrontCardReadModel as _SFCardRM,
    )
    from src.modules.catalog.application.queries.read_models import (
        StorefrontComparisonReadModel as _SFCompRM,
    )
    from src.modules.catalog.application.queries.read_models import (
        StorefrontFilterListReadModel as _SFFilterRM,
    )
    from src.modules.catalog.application.queries.read_models import (
        StorefrontFormReadModel as _SFFormRM,
    )


class IBrandReadRepository(ABC):
    """Read-only query interface for brands.

    Implementations fetch brand data for the CQRS read side and return
    pure read-model DTOs defined in ``application.queries.read_models``.
    """

    @abstractmethod
    async def get_brand(self, brand_id: uuid.UUID) -> _BrandRM | None:
        """Retrieve a single brand read model by ID, or ``None``."""
        pass

    @abstractmethod
    async def list_brands(self, *, offset: int = 0, limit: int = 20) -> _BrandListRM:
        """Return a paginated list of brands."""
        pass


class ICategoryReadRepository(ABC):
    """Read-only query interface for categories.

    Provides both flat paginated listing and the full recursive tree.
    """

    @abstractmethod
    async def get_category(self, category_id: uuid.UUID) -> _CategoryRM | None:
        """Retrieve a single category read model by ID, or ``None``."""
        pass

    @abstractmethod
    async def list_categories(
        self, *, offset: int = 0, limit: int = 20
    ) -> _CategoryListRM:
        """Return a paginated category list ordered by level and sort order."""
        pass

    @abstractmethod
    async def get_category_tree(self) -> list[_CategoryNodeRM]:
        """Return the full category hierarchy as a list of root nodes."""
        pass


class IAttributeGroupReadRepository(ABC):
    """Read-only query interface for attribute groups."""

    @abstractmethod
    async def get_attribute_group(self, group_id: uuid.UUID) -> _AttrGroupRM | None:
        """Retrieve a single attribute group read model by ID."""
        pass

    @abstractmethod
    async def list_attribute_groups(
        self, *, offset: int = 0, limit: int = 20
    ) -> _AttrGroupListRM:
        """Return a paginated list of attribute groups."""
        pass


class IAttributeReadRepository(ABC):
    """Read-only query interface for attributes and their values."""

    @abstractmethod
    async def get_attribute(self, attribute_id: uuid.UUID) -> _AttrRM | None:
        """Retrieve a single attribute read model by ID."""
        pass

    @abstractmethod
    async def list_attributes(
        self,
        *,
        offset: int = 0,
        limit: int = 20,
        group_id: uuid.UUID | None = None,
    ) -> _AttrListRM:
        """Return a paginated list of attributes, optionally filtered by group."""
        pass

    @abstractmethod
    async def list_attribute_values(
        self,
        attribute_id: uuid.UUID,
        *,
        offset: int = 0,
        limit: int = 50,
    ) -> _AttrValueListRM:
        """Return a paginated list of values for a given attribute."""
        pass


class IProductReadRepository(ABC):
    """Read-only query interface for products and their child entities.

    Covers single-product detail, paginated listing, variants, SKUs,
    product attribute assignments, and media assets.
    """

    @abstractmethod
    async def get_product(self, product_id: uuid.UUID) -> _ProductRM | None:
        """Retrieve a full product read model by ID (with variants, SKUs, attributes).

        Returns ``None`` if the product does not exist or is soft-deleted.
        """
        pass

    @abstractmethod
    async def list_products(
        self,
        *,
        offset: int = 0,
        limit: int = 50,
        status: str | None = None,
        brand_id: uuid.UUID | None = None,
    ) -> _ProductListRM:
        """Return a paginated, optionally filtered, product list."""
        pass

    @abstractmethod
    async def list_variants(
        self,
        product_id: uuid.UUID,
        *,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[_VariantRM], int]:
        """Return paginated variants for a product with total count."""
        pass

    @abstractmethod
    async def list_skus(
        self,
        product_id: uuid.UUID,
        *,
        variant_id: uuid.UUID | None = None,
        offset: int = 0,
        limit: int | None = 50,
    ) -> tuple[list[_SKURM], int]:
        """Return paginated SKUs for a product with total count."""
        pass

    @abstractmethod
    async def list_product_attributes(
        self,
        product_id: uuid.UUID,
        *,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[_ProdAttrRM], int]:
        """Return paginated product attribute assignments with total count."""
        pass


class IStorefrontQueryService(ABC):
    """Read-only query interface for storefront-facing attribute projections.

    Each method returns a pre-shaped read model tailored to a specific
    storefront use case (filter panel, product card, comparison table,
    creation form).  Implementations may apply caching transparently.
    """

    @abstractmethod
    async def get_filterable_attributes(self, category_id: uuid.UUID) -> _SFFilterRM:
        """Return filterable attributes with their dictionary values."""
        pass

    @abstractmethod
    async def get_card_attributes(self, category_id: uuid.UUID) -> _SFCardRM:
        """Return visible-on-card attributes grouped by attribute group."""
        pass

    @abstractmethod
    async def get_comparison_attributes(self, category_id: uuid.UUID) -> _SFCompRM:
        """Return comparable attributes for the comparison table."""
        pass

    @abstractmethod
    async def get_form_attributes(self, category_id: uuid.UUID) -> _SFFormRM:
        """Return the full attribute set for the product creation form."""
        pass
