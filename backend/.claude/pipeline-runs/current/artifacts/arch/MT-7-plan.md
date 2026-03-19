# Architecture Plan -- MT-7: Add CreateProduct command handler

> **Pipeline run:** 20260318-121109
> **Micro-task:** MT-7
> **Layer:** Application
> **Module:** catalog
> **FR Reference:** FR-001
> **Depends on:** MT-2, MT-4, MT-5

---

## Research findings

- **Dishka DI**: Handlers receive interfaces via constructor injection at REQUEST scope. No `@inject` decorator needed on the handler class itself -- Dishka resolves constructor args automatically when the handler is requested.
- **attrs / stdlib dataclasses**: Command DTOs use stdlib `@dataclass(frozen=True)` (not attrs). Domain entities use attrs `@dataclass`. This is the established convention across all existing command handlers.
- **Domain events for Product are DEFERRED** (per pm-spec.md decisions section). The handler must NOT emit domain events or call `uow.register_aggregate()`.

---

## Design decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Command DTO type | stdlib `@dataclass(frozen=True)` | Matches all existing command handlers (CreateAttributeCommand, CreateBrandCommand, etc.) |
| Result DTO type | stdlib `@dataclass(frozen=True)` | Matches CreateAttributeResult pattern |
| Domain events | Skip entirely | Product events deferred to P2 per enhancement plan. No `add_domain_event()`, no `register_aggregate()`. |
| Slug uniqueness check | `IProductRepository.check_slug_exists` | Same pattern as CreateAttributeHandler -- check before create, raise domain exception on conflict. |
| Return type | `CreateProductResult` with `product_id: uuid.UUID` | CQRS: command returns ID only. |

---

## File plan

### `src/modules/catalog/application/commands/create_product.py` -- CREATE

**Purpose:** Defines the CreateProduct command, result, and handler following CQRS write-side pattern.
**Layer:** Application

#### Classes / functions:

**`CreateProductCommand`** (new)
- Decorator: `@dataclass(frozen=True)`
- Fields:
  - `title_i18n: dict[str, str]` -- Multilingual product title (required, at least one entry)
  - `slug: str` -- URL-safe unique identifier
  - `brand_id: uuid.UUID` -- FK to Brand aggregate
  - `primary_category_id: uuid.UUID` -- FK to primary Category
  - `description_i18n: dict[str, str]` -- default `field(default_factory=dict)`
  - `supplier_id: uuid.UUID | None` -- default `None`
  - `country_of_origin: str | None` -- default `None`
  - `tags: list[str]` -- default `field(default_factory=list)`
- DI scope: N/A (plain DTO)

**`CreateProductResult`** (new)
- Decorator: `@dataclass(frozen=True)`
- Fields:
  - `product_id: uuid.UUID`
- DI scope: N/A (plain DTO)

**`CreateProductHandler`** (new)
- Inherits from: nothing (plain class, same as CreateAttributeHandler)
- Constructor args:
  - `product_repo: IProductRepository` -- injected by Dishka
  - `uow: IUnitOfWork` -- injected by Dishka
- Public methods:
  - `async handle(command: CreateProductCommand) -> CreateProductResult`
    1. Enter UoW context: `async with self._uow:`
    2. Check slug uniqueness: `await self._product_repo.check_slug_exists(command.slug)`
    3. If slug exists, raise `ProductSlugConflictError(slug=command.slug)`
    4. Create product via factory: `Product.create(slug=..., title_i18n=..., brand_id=..., primary_category_id=..., description_i18n=..., supplier_id=..., country_of_origin=..., tags=...)`
    5. Persist: `await self._product_repo.add(product)`
    6. NO domain events (deferred) -- do NOT call `uow.register_aggregate()`
    7. Commit: `await self._uow.commit()`
    8. Return `CreateProductResult(product_id=product.id)`
- DI scope: REQUEST
- Events raised: none (deferred)
- Error conditions:
  - `ProductSlugConflictError` -- when slug already exists
  - `ValueError` -- propagated from `Product.create()` if `title_i18n` is empty

#### Imports:
```python
import uuid
from dataclasses import dataclass, field

from src.modules.catalog.domain.entities import Product
from src.modules.catalog.domain.exceptions import ProductSlugConflictError
from src.modules.catalog.domain.interfaces import IProductRepository
from src.shared.interfaces.uow import IUnitOfWork
```

#### Structural sketch (pseudo-code only):
```python
@dataclass(frozen=True)
class CreateProductCommand:
    title_i18n: dict[str, str]
    slug: str
    brand_id: uuid.UUID
    primary_category_id: uuid.UUID
    description_i18n: dict[str, str] = field(default_factory=dict)
    supplier_id: uuid.UUID | None = None
    country_of_origin: str | None = None
    tags: list[str] = field(default_factory=list)

@dataclass(frozen=True)
class CreateProductResult:
    product_id: uuid.UUID

class CreateProductHandler:
    def __init__(self, product_repo: IProductRepository, uow: IUnitOfWork):
        ...

    async def handle(self, command: CreateProductCommand) -> CreateProductResult:
        # 1. async with self._uow
        # 2. check slug uniqueness
        # 3. Product.create(...)
        # 4. repo.add(product)
        # 5. uow.commit()
        # 6. return CreateProductResult(product_id=product.id)
        ...
```

---

## Dependency registration

| Class | Provider group | Scope | In file |
|-------|---------------|-------|---------|
| `CreateProductHandler` | catalog provider | `REQUEST` | `src/bootstrap/container.py` |

Note: The handler must be registered in the Dishka container so that presentation-layer routes can resolve it. Follow the same registration pattern used for `CreateAttributeHandler`.

## Migration plan

No database changes required for this micro-task.

## Integration points

No cross-module integration in this micro-task. Domain events are deferred.

## Risks & edge cases

| Risk | Impact | Mitigation |
|------|--------|------------|
| Slug collision under concurrent requests | Two products could pass the uniqueness check simultaneously | DB-level unique constraint on `products.slug` will catch the race condition; repository should translate the DB integrity error to `ProductSlugConflictError` (infrastructure concern, not this MT's scope) |
| Empty `title_i18n` passed from presentation layer | `Product.create()` raises `ValueError` | Handler lets the ValueError propagate; presentation layer should validate before calling handler |
| Missing DI registration | Handler cannot be resolved at runtime | Ensure `CreateProductHandler` is added to the Dishka container in container.py |

## Acceptance verification

```bash
uv run pytest tests/unit/ tests/architecture/ -v
uv run ruff check .
uv run mypy .
```

**Specific checks:**
- [ ] `CreateProductCommand` is a frozen stdlib dataclass with fields: title_i18n, slug, brand_id, primary_category_id, description_i18n (default={}), supplier_id (default=None), country_of_origin (default=None), tags (default=[])
- [ ] `CreateProductResult` is a frozen stdlib dataclass with `product_id: uuid.UUID`
- [ ] Handler validates slug uniqueness via `IProductRepository.check_slug_exists`
- [ ] Handler creates Product via `Product.create()` factory method
- [ ] Handler uses UoW pattern: `async with self._uow:` -> `repo.add()` -> `uow.commit()`
- [ ] No domain events emitted (no `add_domain_event`, no `register_aggregate`)
- [ ] Domain layer has zero framework imports
- [ ] No cross-module imports
- [ ] All writes go through UoW
- [ ] Google-style docstrings on all public classes and methods
- [ ] All existing tests pass
- [ ] Linter and type-checker pass
