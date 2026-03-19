# Architecture Plan -- MT-18: Add ProductAttributeValueRepository implementation

> **Pipeline run:** 20260318-121109
> **Micro-task:** MT-18
> **Layer:** Infrastructure
> **Module:** catalog
> **FR Reference:** FR-003
> **Depends on:** MT-5 (domain entities incl. ProductAttributeValue), MT-16 (ORM ProductAttributeValueModel)

---

## Research findings

Skipped -- this MT follows the exact same Data Mapper repository pattern already established in `AttributeValueRepository` and `CategoryAttributeBindingRepository`. No new library APIs are involved beyond `select`, `delete` from SQLAlchemy which are already used throughout the codebase.

---

## Design decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Follow CategoryAttributeBindingRepository pattern | Yes | Both are child-entity repos (not aggregate roots) with an `exists` method checking a two-column pair. Nearly identical structure. |
| No `update` method | Omit | Interface `IProductAttributeValueRepository` does not define `update`. Product attribute assignments are immutable -- delete and re-add. |
| `exists` checks `(product_id, attribute_id)` pair | Yes | Matches interface contract and DB unique constraint `uix_product_single_attribute_value`. |

---

## File plan

### `src/modules/catalog/infrastructure/repositories/product_attribute_value.py` -- CREATE

**Purpose:** Data Mapper repository translating between `ProductAttributeValue` domain entity and `ProductAttributeValueModel` ORM model.
**Layer:** Infrastructure

#### Classes / functions:

**`ProductAttributeValueRepository`** (new)

- Inherits from: `IProductAttributeValueRepository` (from `src.modules.catalog.domain.interfaces`)
- Constructor args:
  - `session: AsyncSession` -- SQLAlchemy async session scoped to the current request
- Private methods:
  - `_to_domain(self, orm: OrmProductAttributeValue) -> DomainProductAttributeValue` -- maps ORM row to domain entity
  - `_to_orm(self, domain: DomainProductAttributeValue) -> OrmProductAttributeValue` -- maps domain entity to new ORM row (no update variant needed since interface has no update method)
- Public methods:
  - `async add(self, entity: DomainProductAttributeValue) -> DomainProductAttributeValue` -- persist new row, flush, return mapped domain entity
  - `async get(self, pav_id: uuid.UUID) -> DomainProductAttributeValue | None` -- get by PK using `session.get()`, return mapped or None
  - `async delete(self, pav_id: uuid.UUID) -> None` -- delete by PK using `delete()` statement
  - `async list_by_product(self, product_id: uuid.UUID) -> list[DomainProductAttributeValue]` -- select all rows where `product_id` matches, return list of domain entities
  - `async exists(self, product_id: uuid.UUID, attribute_id: uuid.UUID) -> bool` -- check if `(product_id, attribute_id)` pair exists, return bool
- DI scope: REQUEST (provided via Dishka, not wired in this MT)
- Events raised: none
- Error conditions: none (no ValueError on delete -- follows same pattern as `AttributeValueRepository.delete` which is silent on missing rows)

#### Imports:

```python
"""
ProductAttributeValue repository -- Data Mapper implementation.

Translates between :class:`~src.modules.catalog.domain.entities.ProductAttributeValue`
(domain) and the ``product_attribute_values`` ORM table. Provides duplicate-guard
checks scoped to the (product_id, attribute_id) pair.
"""

import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.domain.entities import ProductAttributeValue as DomainProductAttributeValue
from src.modules.catalog.domain.interfaces import IProductAttributeValueRepository
from src.modules.catalog.infrastructure.models import (
    ProductAttributeValueModel as OrmProductAttributeValue,
)
```

#### Structural sketch (pseudo-code only):

```python
class ProductAttributeValueRepository(IProductAttributeValueRepository):
    """Data Mapper repository for ProductAttributeValue child entities.

    Args:
        session: SQLAlchemy async session scoped to the current request.
    """

    def __init__(self, session: AsyncSession):
        self._session = session

    def _to_domain(self, orm: OrmProductAttributeValue) -> DomainProductAttributeValue:
        """Map an ORM row to a domain entity."""
        return DomainProductAttributeValue(
            id=orm.id,
            product_id=orm.product_id,
            attribute_id=orm.attribute_id,
            attribute_value_id=orm.attribute_value_id,
        )

    def _to_orm(self, domain: DomainProductAttributeValue) -> OrmProductAttributeValue:
        """Map a domain entity to an ORM row."""
        orm = OrmProductAttributeValue()
        orm.id = domain.id
        orm.product_id = domain.product_id
        orm.attribute_id = domain.attribute_id
        orm.attribute_value_id = domain.attribute_value_id
        return orm

    async def add(self, entity: DomainProductAttributeValue) -> DomainProductAttributeValue:
        """Persist a new product attribute assignment and return the refreshed domain entity."""
        orm = self._to_orm(entity)
        self._session.add(orm)
        await self._session.flush()
        return self._to_domain(orm)

    async def get(self, pav_id: uuid.UUID) -> DomainProductAttributeValue | None:
        """Retrieve a product attribute value by primary key, or ``None``."""
        orm = await self._session.get(OrmProductAttributeValue, pav_id)
        if orm:
            return self._to_domain(orm)
        return None

    async def delete(self, pav_id: uuid.UUID) -> None:
        """Delete a product attribute assignment by primary key."""
        statement = delete(OrmProductAttributeValue).where(OrmProductAttributeValue.id == pav_id)
        await self._session.execute(statement)

    async def list_by_product(self, product_id: uuid.UUID) -> list[DomainProductAttributeValue]:
        """List all attribute assignments for a given product."""
        statement = select(OrmProductAttributeValue).where(
            OrmProductAttributeValue.product_id == product_id
        )
        result = await self._session.execute(statement)
        return [self._to_domain(orm) for orm in result.scalars().all()]

    async def exists(self, product_id: uuid.UUID, attribute_id: uuid.UUID) -> bool:
        """Check whether a product+attribute pair already exists (duplicate guard)."""
        statement = (
            select(OrmProductAttributeValue.id)
            .where(
                OrmProductAttributeValue.product_id == product_id,
                OrmProductAttributeValue.attribute_id == attribute_id,
            )
            .limit(1)
        )
        result = await self._session.execute(statement)
        return result.first() is not None
```

---

### `src/modules/catalog/infrastructure/repositories/__init__.py` -- MODIFY

**Purpose:** Add `ProductAttributeValueRepository` to the package exports.
**Layer:** Infrastructure

#### Changes:

Add one new import and one new `__all__` entry:

```python
# ADD this import after the ProductRepository import:
from src.modules.catalog.infrastructure.repositories.product_attribute_value import (
    ProductAttributeValueRepository,
)

# ADD "ProductAttributeValueRepository" to __all__ list (alphabetical position: after "ProductRepository")
```

The final `__init__.py` should have these imports (in order):

1. `AttributeRepository`
2. `AttributeGroupRepository`
3. `AttributeValueRepository`
4. `BrandRepository`
5. `CategoryRepository`
6. `CategoryAttributeBindingRepository`
7. `ProductRepository`
8. `ProductAttributeValueRepository` (NEW)

And `__all__` should list all 8 names in alphabetical order.

---

## Dependency registration

No DI changes required for this micro-task. DI wiring will be handled in a later MT (bootstrap/container.py).

## Migration plan

No database changes required for this micro-task. The `product_attribute_values` table already exists via ORM model `ProductAttributeValueModel`.

## Integration points

No cross-module integration in this micro-task.

## Risks & edge cases

| Risk | Impact | Mitigation |
|------|--------|------------|
| ORM model field name mismatch between `ProductAttributeValueModel` and domain `ProductAttributeValue` | Mapper produces wrong values | Field names are identical on both sides: `id`, `product_id`, `attribute_id`, `attribute_value_id`. Verified by reading both definitions. |
| `list_by_product` returns unordered results | Non-deterministic ordering in API responses | Acceptable for MVP. If ordering is needed later, add `.order_by(OrmProductAttributeValue.attribute_id)`. |

## Acceptance verification

```bash
uv run pytest tests/unit/ tests/architecture/ -v
uv run ruff check .
uv run mypy .
```

**Specific checks:**

- [ ] `ProductAttributeValueRepository` implements `IProductAttributeValueRepository` (all 5 abstract methods)
- [ ] `_to_domain()` maps all 4 fields: `id`, `product_id`, `attribute_id`, `attribute_value_id`
- [ ] `_to_orm()` maps all 4 fields: `id`, `product_id`, `attribute_id`, `attribute_value_id`
- [ ] `add` calls `self._session.add(orm)` then `await self._session.flush()` then returns `self._to_domain(orm)`
- [ ] `get` uses `await self._session.get(OrmProductAttributeValue, pav_id)`
- [ ] `delete` uses `delete(OrmProductAttributeValue).where(OrmProductAttributeValue.id == pav_id)`
- [ ] `list_by_product` uses `select(OrmProductAttributeValue).where(...product_id...)` and returns list via `result.scalars().all()`
- [ ] `exists` uses `select(OrmProductAttributeValue.id).where(product_id, attribute_id).limit(1)` and returns `result.first() is not None`
- [ ] `ProductAttributeValueRepository` is exported from `__init__.py`
- [ ] Domain layer has zero framework imports
- [ ] All existing tests pass
