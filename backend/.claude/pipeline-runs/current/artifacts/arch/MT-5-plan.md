# Architecture Plan -- MT-5: Define IProductRepository and IProductAttributeValueRepository interfaces

> **Pipeline run:** 20260318-121109
> **Micro-task:** MT-5
> **Layer:** Domain
> **Module:** catalog
> **FR Reference:** FR-001, FR-003
> **Depends on:** MT-2, MT-3

---

## Research findings

- **No external library research required.** This MT modifies only domain-layer abstract interfaces using stdlib (`abc`, `uuid`) and domain entity imports. No framework APIs are involved.
- **Existing patterns** in `src/modules/catalog/domain/interfaces.py` are the authoritative reference: `IBrandRepository` for slug-based queries and `IAttributeValueRepository` / `ICategoryAttributeBindingRepository` for child-entity repositories.

---

## Design decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| IProductRepository generic type | `ICatalogRepository[Product]` (import `Product` from domain entities, replacing `Any`) | Type safety; follows IBrandRepository/ICategoryRepository pattern. The placeholder used `Any` which breaks type checking. |
| list_products return type | `tuple[list[Product], int]` (entities + total count) | Consistent with pagination pattern. Repository returns domain entities; query handlers map to read models. Total count enables pagination metadata. |
| list_products filter params | `limit: int, offset: int, status: ProductStatus | None, brand_id: uuid.UUID | None` | Matches MT-15 query handler needs and MT-20 router query params. Optional filters default to None. |
| get_with_skus method | Separate method returning `Product | None` with SKUs eagerly loaded | Infrastructure concern (eager loading) exposed as a domain contract because command handlers (AddSKU, UpdateSKU, DeleteSKU) need the full aggregate with children loaded. |
| IProductAttributeValueRepository base class | Standalone `ABC` (not `ICatalogRepository`) | Follows `IAttributeValueRepository` and `ICategoryAttributeBindingRepository` pattern -- child entity repos do not extend the generic CRUD base. |
| exists method signature | `exists(product_id, attribute_id) -> bool` | Needed by AssignProductAttributeHandler (MT-14) to check duplicate assignment before creating. Matches `ICategoryAttributeBindingRepository.exists()` pattern. |
| list_by_product method | `list_by_product(product_id) -> list[ProductAttributeValue]` | Needed by ListProductAttributesHandler (MT-15) for read-side query. |
| Import of ProductStatus in interfaces | Import from `value_objects` | Needed for `list_products` status filter parameter type annotation. |

---

## File plan

### `src/modules/catalog/domain/interfaces.py` -- MODIFY

**Purpose:** Replace the placeholder `IProductRepository` with a fully typed interface and add `IProductAttributeValueRepository`.

**Layer:** Domain

#### Changes to imports:

Add these imports at the top of the file (alongside existing entity imports):

```python
from src.modules.catalog.domain.entities import Product as DomainProduct
from src.modules.catalog.domain.entities import ProductAttributeValue as DomainProductAttributeValue
from src.modules.catalog.domain.value_objects import ProductStatus
```

Remove `Any` from the `typing` import line (it will no longer be needed).

#### Class: `IProductRepository` (modify existing -- replace placeholder)

**`IProductRepository`** (modify existing)
- Inherits from: `ICatalogRepository[DomainProduct]` (replacing `ICatalogRepository[Any]`)
- Inherits CRUD methods from base: `add`, `get`, `update`, `delete`
- Additional abstract methods:
  - `get_by_slug(slug: str) -> DomainProduct | None` -- Retrieve a product by its URL slug.
  - `check_slug_exists(slug: str) -> bool` -- Check whether a product with the given slug already exists.
  - `check_slug_exists_excluding(slug: str, exclude_id: uuid.UUID) -> bool` -- Check if a slug is taken by another product (excluding given ID).
  - `get_for_update(product_id: uuid.UUID) -> DomainProduct | None` -- Retrieve a product with a pessimistic lock (SELECT FOR UPDATE).
  - `get_with_skus(product_id: uuid.UUID) -> DomainProduct | None` -- Retrieve a product with eagerly loaded SKU child entities.
  - `list_products(limit: int, offset: int, status: ProductStatus | None = None, brand_id: uuid.UUID | None = None) -> tuple[list[DomainProduct], int]` -- List products with pagination and optional filters; returns (items, total_count). Excludes soft-deleted products.
- DI scope: N/A (interface only; implementation is REQUEST scoped)
- Events raised: none
- Error conditions: none (interface only)

#### Class: `IProductAttributeValueRepository` (new)

**`IProductAttributeValueRepository`** (new)
- Inherits from: `ABC`
- Constructor args: none (interface only)
- Public methods:
  - `add(entity: DomainProductAttributeValue) -> DomainProductAttributeValue` -- Persist a new product attribute assignment.
  - `get(pav_id: uuid.UUID) -> DomainProductAttributeValue | None` -- Retrieve a product attribute value by its unique identifier.
  - `delete(pav_id: uuid.UUID) -> None` -- Remove a product attribute assignment by its unique identifier.
  - `list_by_product(product_id: uuid.UUID) -> list[DomainProductAttributeValue]` -- List all attribute assignments for a given product.
  - `exists(product_id: uuid.UUID, attribute_id: uuid.UUID) -> bool` -- Check whether a product+attribute pair already exists (duplicate guard).
- DI scope: N/A (interface only; implementation is REQUEST scoped)
- Events raised: none
- Error conditions: none (interface only)

#### Full structural sketch (pseudo-code):

```python
# --- IProductRepository replacement (lines ~275-278) ---
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
    async def get_with_skus(self, product_id: uuid.UUID) -> DomainProduct | None:
        """Retrieve a product with eagerly loaded SKU child entities."""
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


# --- IProductAttributeValueRepository (new, after IProductRepository) ---
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
        """Remove a product attribute assignment by its unique identifier."""
        pass

    @abstractmethod
    async def list_by_product(
        self, product_id: uuid.UUID
    ) -> list[DomainProductAttributeValue]:
        """List all attribute assignments for a given product."""
        pass

    @abstractmethod
    async def exists(self, product_id: uuid.UUID, attribute_id: uuid.UUID) -> bool:
        """Check whether a product+attribute pair already exists."""
        pass
```

#### Imports (final state of the file's import block):

```python
import uuid
from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from src.modules.catalog.domain.entities import Attribute as DomainAttribute
from src.modules.catalog.domain.entities import AttributeGroup
from src.modules.catalog.domain.entities import AttributeValue as DomainAttributeValue
from src.modules.catalog.domain.entities import Brand as DomainBrand
from src.modules.catalog.domain.entities import Category as DomainCategory
from src.modules.catalog.domain.entities import CategoryAttributeBinding as DomainBinding
from src.modules.catalog.domain.entities import Product as DomainProduct
from src.modules.catalog.domain.entities import ProductAttributeValue as DomainProductAttributeValue
from src.modules.catalog.domain.value_objects import ProductStatus
```

Note: `Any` is removed from the `typing` import since it is no longer used.

---

## Dependency registration

No DI changes required for this micro-task. These are interfaces only; implementations will be registered in MT-23.

## Migration plan

No database changes required for this micro-task.

## Integration points

No cross-module integration in this micro-task. These are internal domain contracts within the `catalog` module.

## Risks & edge cases

| Risk | Impact | Mitigation |
|------|--------|------------|
| Circular import between entities.py and interfaces.py | Module fails to load at runtime | Already mitigated: entities.py does NOT import interfaces.py. Interfaces import entities (one-directional). Verified in existing codebase. |
| list_products returning domain entities vs DTOs | Query handlers might be tempted to leak domain entities | list_products is used by the query handler which maps to read models (MT-15). This follows the existing pattern where repos return domain entities and handlers transform them. |
| Missing `update` method on IProductAttributeValueRepository | MT-14 only needs assign (add) and remove (delete) | No update operation is specified in any MT for product attribute values. If needed later, it can be added. Keeping the interface minimal. |

## Acceptance verification

How senior-backend should verify this MT is correctly implemented:

```bash
uv run pytest tests/unit/ tests/architecture/ -v
uv run ruff check .
uv run mypy .
```

**Specific checks:**
- [ ] IProductRepository extends `ICatalogRepository[DomainProduct]` (not `ICatalogRepository[Any]`)
- [ ] IProductRepository has methods: get_by_slug, check_slug_exists, check_slug_exists_excluding, get_for_update, get_with_skus, list_products
- [ ] list_products accepts limit, offset, status (optional ProductStatus), brand_id (optional UUID) and returns `tuple[list[DomainProduct], int]`
- [ ] IProductAttributeValueRepository is a standalone ABC with methods: add, get, delete, list_by_product, exists
- [ ] exists method takes product_id and attribute_id parameters
- [ ] `Any` is no longer imported from typing
- [ ] Domain layer has zero framework imports
- [ ] No cross-module imports
- [ ] All writes go through UoW (N/A -- interfaces only)
- [ ] All existing tests pass after this change
- [ ] Linter/type-checker passes
