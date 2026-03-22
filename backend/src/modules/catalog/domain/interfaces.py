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

from src.modules.catalog.domain.entities import Attribute as DomainAttribute
from src.modules.catalog.domain.entities import AttributeGroup as DomainAttributeGroup
from src.modules.catalog.domain.entities import AttributeValue as DomainAttributeValue
from src.modules.catalog.domain.entities import Brand as DomainBrand
from src.modules.catalog.domain.entities import Category as DomainCategory
from src.modules.catalog.domain.entities import CategoryAttributeBinding as DomainBinding
from src.modules.catalog.domain.entities import MediaAsset as DomainMediaAsset
from src.modules.catalog.domain.entities import Product as DomainProduct
from src.modules.catalog.domain.entities import ProductAttributeValue as DomainProductAttributeValue
from src.modules.catalog.domain.value_objects import ProductStatus


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
        """Remove an aggregate by its unique identifier."""
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
    async def check_slug_exists_excluding(self, slug: str, exclude_id: uuid.UUID) -> bool:
        """Check if a slug is taken by another brand (excluding given ID)."""
        pass

    @abstractmethod
    async def get_by_slug(self, slug: str) -> DomainBrand | None:
        """Retrieve a brand by its URL slug, or ``None``."""
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
    async def update_descendants_full_slug(self, old_prefix: str, new_prefix: str) -> None:
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
    async def check_code_exists(self, code: str) -> bool:
        """Check whether an attribute with the given code already exists."""
        pass

    @abstractmethod
    async def check_slug_exists(self, slug: str) -> bool:
        """Check whether an attribute with the given slug already exists."""
        pass

    @abstractmethod
    async def check_code_exists_excluding(self, code: str, exclude_id: uuid.UUID) -> bool:
        """Check if a code is taken by another attribute (excluding given ID)."""
        pass

    @abstractmethod
    async def check_slug_exists_excluding(self, slug: str, exclude_id: uuid.UUID) -> bool:
        """Check if a slug is taken by another attribute (excluding given ID)."""
        pass

    @abstractmethod
    async def get_by_slug(self, slug: str) -> DomainAttribute | None:
        """Retrieve an attribute by its URL slug."""
        pass

    @abstractmethod
    async def has_category_bindings(self, attribute_id: uuid.UUID) -> bool:
        """Check whether the attribute is bound to at least one category."""
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
        """Remove an attribute value by its unique identifier."""
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
    async def bulk_update_sort_order(self, updates: list[tuple[uuid.UUID, int]]) -> None:
        """Bulk-update sort_order for multiple values atomically.

        Args:
            updates: List of (value_id, new_sort_order) tuples.
        """
        pass


class ICategoryAttributeBindingRepository(ABC):
    """Repository contract for CategoryAttributeBinding entities."""

    @abstractmethod
    async def add(self, entity: DomainBinding) -> DomainBinding:
        """Persist a new category-attribute binding."""
        pass

    @abstractmethod
    async def get(self, binding_id: uuid.UUID) -> DomainBinding | None:
        """Retrieve a binding by its unique identifier."""
        pass

    @abstractmethod
    async def update(self, entity: DomainBinding) -> DomainBinding:
        """Persist changes to an existing binding."""
        pass

    @abstractmethod
    async def delete(self, binding_id: uuid.UUID) -> None:
        """Remove a binding by its unique identifier."""
        pass

    @abstractmethod
    async def exists(self, category_id: uuid.UUID, attribute_id: uuid.UUID) -> bool:
        """Check whether a binding for this category+attribute pair exists."""
        pass

    @abstractmethod
    async def get_by_category_and_attribute(
        self, category_id: uuid.UUID, attribute_id: uuid.UUID
    ) -> DomainBinding | None:
        """Retrieve a binding by the category+attribute pair."""
        pass

    @abstractmethod
    async def bulk_update_sort_order(self, updates: list[tuple[uuid.UUID, int]]) -> None:
        """Bulk-update sort_order for multiple bindings atomically."""
        pass

    @abstractmethod
    async def bulk_update_requirement_level(self, updates: list[tuple[uuid.UUID, str]]) -> None:
        """Bulk-update requirement_level for multiple bindings atomically."""
        pass


class IProductRepository(ICatalogRepository[DomainProduct]):
    """Repository contract for the Product aggregate.

    Extends the generic CRUD base with slug-based lookups,
    pessimistic locking, eager SKU loading, and paginated listing
    with optional status and brand filters.
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
    async def check_slug_exists_excluding(self, slug: str, exclude_id: uuid.UUID) -> bool:
        """Check if a slug is taken by another product (excluding given ID)."""
        pass

    @abstractmethod
    async def get_for_update(self, product_id: uuid.UUID) -> DomainProduct | None:
        """Retrieve a product with a pessimistic lock (SELECT FOR UPDATE)."""
        pass

    @abstractmethod
    async def get_with_variants(self, product_id: uuid.UUID) -> DomainProduct | None:
        """Retrieve a product with eagerly loaded variant and SKU child entities."""
        pass

    @abstractmethod
    async def list_products(
        self,
        limit: int,
        offset: int,
        status: ProductStatus | None = None,
        brand_id: uuid.UUID | None = None,
    ) -> tuple[list[DomainProduct], int]:
        """List products with pagination and optional filters.

        Args:
            limit: Maximum number of products to return.
            offset: Number of products to skip.
            status: Optional filter by product lifecycle status.
            brand_id: Optional filter by brand.

        Returns:
            Tuple of (product_list, total_count). Soft-deleted products
            are excluded.
        """
        pass


class IProductAttributeValueRepository(ABC):
    """Repository contract for ProductAttributeValue entities.

    Manages product-level EAV assignments -- linking products to
    attribute dictionary values. This is a child-entity repository
    (not an aggregate root repository).
    """

    @abstractmethod
    async def add(self, entity: DomainProductAttributeValue) -> DomainProductAttributeValue:
        """Persist a new product attribute assignment."""
        pass

    @abstractmethod
    async def get(self, pav_id: uuid.UUID) -> DomainProductAttributeValue | None:
        """Retrieve a product attribute value by its unique identifier."""
        pass

    @abstractmethod
    async def delete(self, pav_id: uuid.UUID) -> None:
        """Remove a product attribute assignment by its unique identifier."""
        pass

    @abstractmethod
    async def list_by_product(self, product_id: uuid.UUID) -> list[DomainProductAttributeValue]:
        """List all attribute assignments for a given product."""
        pass

    @abstractmethod
    async def get_by_product_and_attribute(
        self, product_id: uuid.UUID, attribute_id: uuid.UUID
    ) -> DomainProductAttributeValue | None:
        """Retrieve a product attribute value by the product+attribute pair."""
        pass

    @abstractmethod
    async def exists(self, product_id: uuid.UUID, attribute_id: uuid.UUID) -> bool:
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
        """Remove a media asset by ID."""
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
