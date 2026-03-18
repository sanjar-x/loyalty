# Architecture Plan -- MT-8: Add UpdateProduct command handler

> **Pipeline run:** 20260318-121109
> **Micro-task:** MT-8
> **Layer:** Application
> **Module:** catalog
> **FR Reference:** FR-001, FR-005
> **Depends on:** MT-2, MT-4, MT-5

---

## Research findings

- **Dishka DI** (reagento/dishka): Command handlers receive repository interfaces and IUnitOfWork via constructor injection at REQUEST scope. No `container.resolve()` calls inside business logic.
- **Existing pattern** (UpdateBrandHandler, UpdateAttributeHandler): All update handlers follow fetch -> validate -> mutate -> repo.update -> uow.commit flow within `async with self._uow:` block.
- **_SENTINEL pattern**: Already established in `entities.py` (line 908) for nullable fields (`supplier_id`, `country_of_origin`) where callers need to distinguish "leave unchanged" from "set to None". The command dataclass must mirror this pattern.
- **Optimistic locking**: MT spec requires optional domain-level version check. If `command.version` is provided and does not match `product.version`, raise `ConcurrencyError` before mutation. This is an API-level guard complementing SQLAlchemy's `version_id_col` at the DB level.

---

## Design decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Sentinel for nullable command fields | Use `_SENTINEL = object()` in command module for `supplier_id` and `country_of_origin` | Mirrors the domain entity's sentinel pattern; allows distinguishing "not provided" from "set to None" at the API boundary |
| Version check placement | Before calling `product.update()` | Fail fast -- no point mutating if version is stale. Domain entity does not own version check logic (version is managed by repo/infrastructure) |
| Slug uniqueness check | Only when slug is being changed (slug != current) | Follows UpdateBrandHandler pattern exactly (line 86-90 of update_brand.py) |
| Return type | `UpdateProductResult` with `id: uuid.UUID` only | CQRS: command handlers return minimal data (void or ID). Full product data retrieved via query side. Consistent with `UpdateAttributeResult`. |
| No domain events | Skip event emission | Per pm-spec.md research summary: "domain_events_product_lifecycle is P2" |
| No logger injection | Omit ILogger from constructor | UpdateAttributeHandler omits logger; UpdateBrandHandler includes it. Keep it simple for now -- consistent with the attribute pattern which is the closer match. |

---

## File plan

### `src/modules/catalog/application/commands/update_product.py` -- CREATE

**Purpose:** UpdateProduct command dataclass and handler. Validates version (optimistic lock), checks slug uniqueness on change, delegates mutation to `Product.update()`, persists via repository and UoW.
**Layer:** Application

#### Classes / functions:

**`_SENTINEL`** (new, module-level constant)
- Type: `object`
- Value: `object()`
- Purpose: Distinguish "not provided" from "set to None" for `supplier_id` and `country_of_origin` fields in the command.

**`UpdateProductCommand`** (new)
- Decorator: `@dataclass(frozen=True)`
- Fields:
  - `product_id: uuid.UUID` -- UUID of the product to update (required)
  - `title_i18n: dict[str, str] | None = None` -- new multilingual title, or None to keep
  - `description_i18n: dict[str, str] | None = None` -- new description, or None to keep
  - `slug: str | None = None` -- new slug, or None to keep
  - `brand_id: uuid.UUID | None = None` -- new brand, or None to keep
  - `primary_category_id: uuid.UUID | None = None` -- new category, or None to keep
  - `supplier_id: uuid.UUID | None | object = _SENTINEL` -- new supplier, None to clear, sentinel to keep
  - `country_of_origin: str | None | object = _SENTINEL` -- new country, None to clear, sentinel to keep
  - `tags: list[str] | None = None` -- new tags, or None to keep
  - `version: int | None = None` -- expected version for optimistic lock, or None to skip check
- DI scope: N/A (data object)

**`UpdateProductResult`** (new)
- Decorator: `@dataclass(frozen=True)`
- Fields:
  - `id: uuid.UUID` -- UUID of the updated product

**`UpdateProductHandler`** (new)
- Constructor args:
  - `product_repo: IProductRepository` -- for fetch, slug check, persist
  - `uow: IUnitOfWork` -- transactional boundary
- Public methods:
  - `async handle(command: UpdateProductCommand) -> UpdateProductResult` -- execute the update
- DI scope: REQUEST (registered via provider, not in this file)
- Events raised: none (deferred)
- Error conditions:
  - `ProductNotFoundError` -- product_id does not exist
  - `ConcurrencyError` -- version mismatch (entity_type="Product", expected=command.version, actual=product.version)
  - `ProductSlugConflictError` -- new slug already taken by another product
  - `ValueError` -- from Product.update() if title_i18n is empty

#### Handler logic (pseudo-code):

```python
async def handle(self, command):
    async with self._uow:
        product = await self._product_repo.get(command.product_id)
        if product is None:
            raise ProductNotFoundError(product_id=command.product_id)

        # Optimistic locking: API-level version guard
        if command.version is not None and command.version != product.version:
            raise ConcurrencyError(
                entity_type="Product",
                entity_id=product.id,
                expected_version=command.version,
                actual_version=product.version,
            )

        # Slug uniqueness check (only if changing)
        if command.slug is not None and command.slug != product.slug:
            if await self._product_repo.check_slug_exists_excluding(
                command.slug, command.product_id
            ):
                raise ProductSlugConflictError(slug=command.slug)

        # Delegate mutation to domain entity
        product.update(
            title_i18n=command.title_i18n,
            description_i18n=command.description_i18n,
            slug=command.slug,
            brand_id=command.brand_id,
            primary_category_id=command.primary_category_id,
            supplier_id=command.supplier_id,
            country_of_origin=command.country_of_origin,
            tags=command.tags,
        )

        await self._product_repo.update(product)
        await self._uow.commit()

    return UpdateProductResult(id=product.id)
```

#### Imports:
```python
import uuid
from dataclasses import dataclass

from src.modules.catalog.domain.exceptions import (
    ConcurrencyError,
    ProductNotFoundError,
    ProductSlugConflictError,
)
from src.modules.catalog.domain.interfaces import IProductRepository
from src.shared.interfaces.uow import IUnitOfWork
```

#### Notes on sentinel forwarding:
- The command's `supplier_id` and `country_of_origin` fields use `_SENTINEL` as defaults.
- These are passed directly to `Product.update()` which also uses the same sentinel pattern.
- However, the command's sentinel and the entity's sentinel are different objects. This means we must handle forwarding carefully.
- **Solution:** Import `_SENTINEL` from `entities.py` module OR define a local one and conditionally pass. The cleanest approach: use the **same sentinel** from entities.py. But entities.py defines it as a module-level variable, not exported.
- **Revised approach:** Do NOT define a separate sentinel in the command module. Instead, use the same sentinel from `src.modules.catalog.domain.entities` (`_SENTINEL`). Import it. This ensures identity comparison (`is not _SENTINEL`) works correctly end-to-end.
- **Alternative (cleaner):** The handler should conditionally pass kwargs to `product.update()`. Build a kwargs dict, only including `supplier_id` / `country_of_origin` if they are not the command's sentinel. This way the command module has its own sentinel that never crosses into domain.

**Final decision:** Use a local sentinel in the command module. In the handler, check `command.supplier_id is not _SENTINEL` and build kwargs conditionally. This keeps the command module decoupled from the domain entity's internal sentinel.

#### Revised handler logic for sentinel handling:

```python
async def handle(self, command):
    async with self._uow:
        # ... fetch, version check, slug check ...

        # Build kwargs, forwarding sentinel fields only when provided
        update_kwargs: dict[str, Any] = {}
        if command.title_i18n is not None:
            update_kwargs["title_i18n"] = command.title_i18n
        if command.description_i18n is not None:
            update_kwargs["description_i18n"] = command.description_i18n
        if command.slug is not None:
            update_kwargs["slug"] = command.slug
        if command.brand_id is not None:
            update_kwargs["brand_id"] = command.brand_id
        if command.primary_category_id is not None:
            update_kwargs["primary_category_id"] = command.primary_category_id
        if command.supplier_id is not _SENTINEL:
            update_kwargs["supplier_id"] = command.supplier_id
        if command.country_of_origin is not _SENTINEL:
            update_kwargs["country_of_origin"] = command.country_of_origin
        if command.tags is not None:
            update_kwargs["tags"] = command.tags

        product.update(**update_kwargs)

        await self._product_repo.update(product)
        await self._uow.commit()

    return UpdateProductResult(id=product.id)
```

Updated imports to include `Any`:
```python
import uuid
from dataclasses import dataclass
from typing import Any

from src.modules.catalog.domain.exceptions import (
    ConcurrencyError,
    ProductNotFoundError,
    ProductSlugConflictError,
)
from src.modules.catalog.domain.interfaces import IProductRepository
from src.shared.interfaces.uow import IUnitOfWork
```

---

## Dependency registration

No DI changes required for this micro-task. The handler will be registered in MT-23 (ProductProvider).

## Migration plan

No database changes required for this micro-task.

## Integration points

No cross-module integration in this micro-task. No domain events emitted (deferred to P2).

## Risks & edge cases

| Risk | Impact | Mitigation |
|------|--------|------------|
| Sentinel identity mismatch between command and entity layers | supplier_id/country_of_origin not forwarded correctly to Product.update() | Handler builds kwargs dict conditionally; only includes sentinel fields when caller explicitly set them |
| Version=0 passed by client (valid but unusual) | Could match a real version 0 if somehow stored | Product.version starts at 1 (set in create factory), so version=0 will always raise ConcurrencyError -- correct behavior |
| Slug changed to one that matches current slug | Unnecessary uniqueness check against self | check_slug_exists_excluding uses exclude_id=product_id, so self-match is excluded -- safe |
| Empty title_i18n dict passed | ValueError from Product.update() propagates unhandled | This is expected behavior -- presentation layer should validate before calling, but domain enforces as last guard |
| Concurrent updates with same version | First committer wins at DB level (version_id_col), second gets StaleDataError -> ConcurrencyError from repository | Correct behavior -- API-level check catches most cases early, DB-level catches race conditions |

## Acceptance verification

```bash
uv run pytest tests/unit/ tests/architecture/ -v
uv run ruff check .
uv run mypy .
```

**Specific checks:**
- [ ] UpdateProductCommand is a frozen dataclass with product_id and all updatable fields as optional, plus optional version field
- [ ] Handler fetches product via repo.get, raises ProductNotFoundError if missing
- [ ] If version is provided and does not match product.version, raises ConcurrencyError
- [ ] Handler calls product.update() with only the fields that were explicitly provided
- [ ] Handler validates slug uniqueness if slug is being changed (and differs from current)
- [ ] UoW commit pattern used (async with self._uow -> repo.update -> uow.commit)
- [ ] Domain layer has zero framework imports
- [ ] No cross-module imports (events only)
- [ ] All writes go through UoW
- [ ] File is at `src/modules/catalog/application/commands/update_product.py`
