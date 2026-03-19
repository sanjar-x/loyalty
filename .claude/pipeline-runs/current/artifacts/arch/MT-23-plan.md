# Architecture Plan -- MT-23: Add ProductProvider DI registration and bootstrap wiring

> **Pipeline run:** 20260318-121109
> **Micro-task:** MT-23
> **Layer:** Cross-cutting
> **Module:** catalog
> **FR Reference:** FR-001, FR-002, FR-003
> **Depends on:** MT-17, MT-18, MT-20, MT-21, MT-22

---

## Research findings

Skipped -- pure DI wiring following existing patterns already established in the codebase. No new library APIs involved. The existing `BrandProvider`, `AttributeProvider`, etc. in `dependencies.py` demonstrate the exact Dishka `Provider` / `Scope.REQUEST` / `CompositeDependencySource = provide(...)` pattern.

---

## Design decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Extend existing ProductProvider vs create new | Extend existing `ProductProvider` class at line 296 of `dependencies.py` | A `ProductProvider` already exists with `product_repo` and `create_product_handler`. Add the remaining registrations to it. |
| Separate SKU provider? | No, keep all in `ProductProvider` | SKU is part of the Product aggregate; follows the pattern of `AttributeValueProvider` being grouped with attribute-related concerns. |
| container.py changes | None needed | `ProductProvider` is already imported and included in `create_container()` at line 26 and line 67. No changes required. |

---

## File plan

### `src/modules/catalog/presentation/dependencies.py` -- MODIFY

**Purpose:** Add all missing Product/SKU/ProductAttribute handler and repository registrations to the existing `ProductProvider` class.

#### What to change:

**1. Add new imports** (add these AFTER the existing `CreateProductHandler` import at line 34, keeping alphabetical order within the import block):

```python
from src.modules.catalog.application.commands.add_sku import AddSKUHandler
from src.modules.catalog.application.commands.assign_product_attribute import (
    AssignProductAttributeHandler,
)
from src.modules.catalog.application.commands.change_product_status import (
    ChangeProductStatusHandler,
)
from src.modules.catalog.application.commands.delete_product import DeleteProductHandler
from src.modules.catalog.application.commands.delete_sku import DeleteSKUHandler
from src.modules.catalog.application.commands.remove_product_attribute import (
    RemoveProductAttributeHandler,
)
from src.modules.catalog.application.commands.update_product import UpdateProductHandler
from src.modules.catalog.application.commands.update_sku import UpdateSKUHandler
```

**2. Add new query imports** (add these AFTER existing query imports, maintaining alphabetical order):

```python
from src.modules.catalog.application.queries.get_product import GetProductHandler
from src.modules.catalog.application.queries.list_product_attributes import (
    ListProductAttributesHandler,
)
from src.modules.catalog.application.queries.list_products import ListProductsHandler
from src.modules.catalog.application.queries.list_skus import ListSKUsHandler
```

**3. Add domain interface import** (add to the existing `from src.modules.catalog.domain.interfaces import (...)` block at line 105):

```python
IProductAttributeValueRepository,
```

This import already has `IProductRepository` -- just add `IProductAttributeValueRepository` to the tuple.

**4. Add infrastructure repository import** (add to the existing `from src.modules.catalog.infrastructure.repositories import (...)` block at line 114):

```python
ProductAttributeValueRepository,
```

This import already has `ProductRepository` -- just add `ProductAttributeValueRepository` to the tuple.

**5. Replace the existing `ProductProvider` class** (currently lines 296-305) with the full version:

```python
class ProductProvider(Provider):
    """DI provider for product-related repositories, command handlers, and query handlers."""

    product_repo: CompositeDependencySource = provide(
        ProductRepository, scope=Scope.REQUEST, provides=IProductRepository
    )
    product_attribute_value_repo: CompositeDependencySource = provide(
        ProductAttributeValueRepository,
        scope=Scope.REQUEST,
        provides=IProductAttributeValueRepository,
    )

    # Command handlers
    create_product_handler: CompositeDependencySource = provide(
        CreateProductHandler, scope=Scope.REQUEST
    )
    update_product_handler: CompositeDependencySource = provide(
        UpdateProductHandler, scope=Scope.REQUEST
    )
    delete_product_handler: CompositeDependencySource = provide(
        DeleteProductHandler, scope=Scope.REQUEST
    )
    change_product_status_handler: CompositeDependencySource = provide(
        ChangeProductStatusHandler, scope=Scope.REQUEST
    )
    add_sku_handler: CompositeDependencySource = provide(
        AddSKUHandler, scope=Scope.REQUEST
    )
    update_sku_handler: CompositeDependencySource = provide(
        UpdateSKUHandler, scope=Scope.REQUEST
    )
    delete_sku_handler: CompositeDependencySource = provide(
        DeleteSKUHandler, scope=Scope.REQUEST
    )
    assign_product_attribute_handler: CompositeDependencySource = provide(
        AssignProductAttributeHandler, scope=Scope.REQUEST
    )
    remove_product_attribute_handler: CompositeDependencySource = provide(
        RemoveProductAttributeHandler, scope=Scope.REQUEST
    )

    # Query handlers
    get_product_handler: CompositeDependencySource = provide(
        GetProductHandler, scope=Scope.REQUEST
    )
    list_products_handler: CompositeDependencySource = provide(
        ListProductsHandler, scope=Scope.REQUEST
    )
    list_skus_handler: CompositeDependencySource = provide(
        ListSKUsHandler, scope=Scope.REQUEST
    )
    list_product_attributes_handler: CompositeDependencySource = provide(
        ListProductAttributesHandler, scope=Scope.REQUEST
    )
```

---

### `src/bootstrap/container.py` -- NO CHANGES

**Reason:** `ProductProvider` is already imported at line 26 and included in `create_container()` at line 67. Since we are modifying the existing class (not creating a new one), no changes are needed in this file.

---

### `src/api/router.py` -- MODIFY

**Purpose:** Mount the three new product-related routers under the `/catalog` prefix.

#### What to change:

**1. Add new router imports** (add AFTER the existing `storefront_router` import at line 22):

```python
from src.modules.catalog.presentation.router_product_attributes import (
    product_attribute_router,
)
from src.modules.catalog.presentation.router_products import product_router
from src.modules.catalog.presentation.router_skus import sku_router
```

**2. Add router mounting** (add AFTER line 35 `router.include_router(storefront_router, prefix="/catalog")`):

```python
router.include_router(product_router, prefix="/catalog")
router.include_router(sku_router, prefix="/catalog")
router.include_router(product_attribute_router, prefix="/catalog")
```

---

## Dependency registration

| Class | Provider group | Scope | In file |
|-------|---------------|-------|---------|
| `ProductRepository` | `ProductProvider` | `REQUEST` | `presentation/dependencies.py` (already exists) |
| `ProductAttributeValueRepository` | `ProductProvider` | `REQUEST` | `presentation/dependencies.py` (NEW) |
| `CreateProductHandler` | `ProductProvider` | `REQUEST` | `presentation/dependencies.py` (already exists) |
| `UpdateProductHandler` | `ProductProvider` | `REQUEST` | `presentation/dependencies.py` (NEW) |
| `DeleteProductHandler` | `ProductProvider` | `REQUEST` | `presentation/dependencies.py` (NEW) |
| `ChangeProductStatusHandler` | `ProductProvider` | `REQUEST` | `presentation/dependencies.py` (NEW) |
| `AddSKUHandler` | `ProductProvider` | `REQUEST` | `presentation/dependencies.py` (NEW) |
| `UpdateSKUHandler` | `ProductProvider` | `REQUEST` | `presentation/dependencies.py` (NEW) |
| `DeleteSKUHandler` | `ProductProvider` | `REQUEST` | `presentation/dependencies.py` (NEW) |
| `AssignProductAttributeHandler` | `ProductProvider` | `REQUEST` | `presentation/dependencies.py` (NEW) |
| `RemoveProductAttributeHandler` | `ProductProvider` | `REQUEST` | `presentation/dependencies.py` (NEW) |
| `GetProductHandler` | `ProductProvider` | `REQUEST` | `presentation/dependencies.py` (NEW) |
| `ListProductsHandler` | `ProductProvider` | `REQUEST` | `presentation/dependencies.py` (NEW) |
| `ListSKUsHandler` | `ProductProvider` | `REQUEST` | `presentation/dependencies.py` (NEW) |
| `ListProductAttributesHandler` | `ProductProvider` | `REQUEST` | `presentation/dependencies.py` (NEW) |

**container.py:** No changes needed -- `ProductProvider()` already registered.

## Migration plan

No database changes required for this micro-task.

## Integration points

No cross-module integration in this micro-task. This is purely DI wiring.

## Risks & edge cases

| Risk | Impact | Mitigation |
|------|--------|------------|
| Handler constructor dependencies not resolvable | Dishka raises `NoFactoryError` at request time | Verify that all dependencies of each handler (repos, UoW, etc.) are already registered in other providers. `IUnitOfWork` comes from `DatabaseProvider`, `IProductRepository` and `IProductAttributeValueRepository` come from `ProductProvider` itself. |
| Router file variable name mismatch | Import error at startup | Verified: `product_router` in `router_products.py`, `sku_router` in `router_skus.py`, `product_attribute_router` in `router_product_attributes.py` |
| Circular import via dependencies.py | Import error at startup | No risk -- all imports flow Presentation -> Application -> Domain, which is the correct direction |

## Acceptance verification

```bash
uv run ruff check --fix .
uv run ruff format .
uv run mypy .
uv run pytest tests/unit/ tests/architecture/ -v
```

**Specific checks:**

- [ ] `ProductProvider` registers `IProductRepository -> ProductRepository`
- [ ] `ProductProvider` registers `IProductAttributeValueRepository -> ProductAttributeValueRepository`
- [ ] `ProductProvider` registers all 9 command handlers: `CreateProductHandler`, `UpdateProductHandler`, `DeleteProductHandler`, `ChangeProductStatusHandler`, `AddSKUHandler`, `UpdateSKUHandler`, `DeleteSKUHandler`, `AssignProductAttributeHandler`, `RemoveProductAttributeHandler`
- [ ] `ProductProvider` registers all 4 query handlers: `GetProductHandler`, `ListProductsHandler`, `ListSKUsHandler`, `ListProductAttributesHandler`
- [ ] `container.py` already imports and includes `ProductProvider()` (no changes needed)
- [ ] `router.py` mounts `product_router`, `sku_router`, `product_attribute_router` under `/catalog` prefix
- [ ] All existing tests pass
- [ ] Linter and type-checker pass
