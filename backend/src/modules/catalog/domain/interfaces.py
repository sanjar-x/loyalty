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
from src.modules.catalog.domain.entities import (
    AttributeTemplate as DomainAttributeTemplate,
)
from src.modules.catalog.domain.entities import AttributeValue as DomainAttributeValue
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


class IImageBackendClient(ABC):
    """Port for server-to-server media deletion calls.

    The application layer depends on this abstraction; the concrete
    HTTP adapter lives in the infrastructure layer.
    """

    @abstractmethod
    async def delete(self, storage_object_id: uuid.UUID) -> None:
        """Delete a media file by its storage object ID. Best-effort."""
        pass


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
    async def has_products(self, brand_id: uuid.UUID) -> bool:
        """Check whether any non-deleted products reference this brand."""
        pass

    @abstractmethod
    async def check_name_exists(self, name: str) -> bool:
        """Check whether a brand with the given name already exists."""
        pass

    @abstractmethod
    async def check_name_exists_excluding(
        self, name: str, exclude_id: uuid.UUID
    ) -> bool:
        """Check if a name is taken by another brand (excluding given ID)."""
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

    @abstractmethod
    async def propagate_effective_template_id(
        self, category_id: uuid.UUID, effective_template_id: uuid.UUID | None
    ) -> list[uuid.UUID]:
        """Propagate effective_template_id to inheriting descendants via recursive CTE.

        Only updates children (and their descendants) where template_id IS NULL.
        Stops at nodes that have their own template_id.
        Returns affected category IDs (excluding root) for cache invalidation.
        """
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
    async def get_many(self, ids: list[uuid.UUID]) -> dict[uuid.UUID, DomainAttribute]:
        """Retrieve multiple attributes by their UUIDs. Missing IDs are omitted."""
        pass

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
    async def has_product_attribute_values(self, attribute_id: uuid.UUID) -> bool:
        """Check whether any products reference this attribute."""
        pass


class IAttributeValueRepository(ABC):
    """Repository contract for AttributeValue entities (children of Attribute)."""

    @abstractmethod
    async def get_many(
        self, ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, DomainAttributeValue]:
        """Retrieve multiple attribute values by their UUIDs. Missing IDs are omitted."""
        pass

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
    async def has_product_references(self, value_id: uuid.UUID) -> bool:
        """Check whether any products reference this attribute value."""
        pass

    @abstractmethod
    async def list_ids_by_attribute(self, attribute_id: uuid.UUID) -> set[uuid.UUID]:
        """Return the set of value IDs belonging to the given attribute."""
        pass

    @abstractmethod
    async def check_codes_exist(
        self, attribute_id: uuid.UUID, codes: list[str]
    ) -> set[str]:
        """Return the subset of codes that already exist for this attribute."""
        pass

    @abstractmethod
    async def check_slugs_exist(
        self, attribute_id: uuid.UUID, slugs: list[str]
    ) -> set[str]:
        """Return the subset of slugs that already exist for this attribute."""
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

    @abstractmethod
    async def check_assignments_exist_bulk(
        self, product_id: uuid.UUID, attribute_ids: list[uuid.UUID]
    ) -> set[uuid.UUID]:
        """Return set of attribute_ids that already have assignments for this product."""
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
    async def list_by_storage_ids(
        self,
        storage_object_ids: list[uuid.UUID],
    ) -> list[DomainMediaAsset]:
        """Get media assets by their storage_object_ids."""
        ...

    @abstractmethod
    async def delete_by_product(
        self,
        product_id: uuid.UUID,
    ) -> list[uuid.UUID]:
        """Delete all media for a product. Returns storage_object_ids for cleanup."""
        ...

    @abstractmethod
    async def bulk_update_sort_order(
        self,
        product_id: uuid.UUID,
        updates: list[tuple[uuid.UUID, int]],
    ) -> int:
        """Bulk-update sort_order for media assets belonging to a product.

        Returns the number of rows updated. If fewer rows than updates,
        some media_ids did not belong to the given product.
        """
        ...

    @abstractmethod
    async def check_main_exists(
        self,
        product_id: uuid.UUID,
        variant_id: uuid.UUID | None,
        exclude_media_id: uuid.UUID | None = None,
    ) -> bool:
        """Check if a MAIN media asset exists for the given product+variant scope."""
        ...


class IAttributeTemplateRepository(ICatalogRepository[DomainAttributeTemplate]):
    """Repository contract for the AttributeTemplate aggregate."""

    @abstractmethod
    async def check_code_exists(self, code: str) -> bool:
        """Check whether a template with the given code already exists."""
        pass

    @abstractmethod
    async def has_category_references(self, template_id: uuid.UUID) -> bool:
        """Check whether any categories reference this template."""
        pass

    @abstractmethod
    async def get_category_ids_by_template_ids(
        self, template_ids: list[uuid.UUID]
    ) -> list[uuid.UUID]:
        """Return category IDs that reference any of the given template IDs."""
        pass


class ITemplateAttributeBindingRepository(
    ICatalogRepository[DomainTemplateAttributeBinding]
):
    """Repository contract for the TemplateAttributeBinding aggregate."""

    @abstractmethod
    async def check_binding_exists(
        self, template_id: uuid.UUID, attribute_id: uuid.UUID
    ) -> bool:
        """Return True if a binding for this pair already exists."""
        pass

    @abstractmethod
    async def list_ids_by_template(self, template_id: uuid.UUID) -> set[uuid.UUID]:
        """Return the set of binding IDs belonging to the given template."""
        pass

    @abstractmethod
    async def get_bindings_for_templates(
        self, template_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, list[DomainTemplateAttributeBinding]]:
        """Batch-load all bindings for a list of template IDs."""
        pass

    @abstractmethod
    async def bulk_update_sort_order(
        self, updates: list[tuple[uuid.UUID, int]]
    ) -> None:
        """Bulk-update sort_order for multiple bindings."""
        pass

    @abstractmethod
    async def has_bindings_for_attribute(self, attribute_id: uuid.UUID) -> bool:
        """Check whether any template binds this attribute (for deletion guard)."""
        pass

    @abstractmethod
    async def get_template_ids_for_attribute(
        self, attribute_id: uuid.UUID
    ) -> list[uuid.UUID]:
        """Return template IDs that bind the given attribute."""
        pass
