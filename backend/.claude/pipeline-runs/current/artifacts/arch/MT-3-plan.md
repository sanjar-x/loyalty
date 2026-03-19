# Architecture Plan -- MT-3: Add ProductAttributeValue domain entity

> **Pipeline run:** 20260318-121109
> **Micro-task:** MT-3
> **Layer:** Domain
> **Module:** catalog
> **FR Reference:** FR-003
> **Depends on:** MT-2

---

## Research findings

- **attrs** (current): `from attr import dataclass` is the standard decorator for domain entities in this codebase. Child entities (non-aggregate) use plain `@dataclass` without extending `AggregateRoot`. See `AttributeValue` at line 638 of entities.py for the canonical pattern.
- **uuid** (stdlib): `uuid.uuid4()` used for ID generation in factory methods throughout the codebase.
- No external library research needed -- this is a pure domain entity with zero framework imports.

---

## Design decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Entity vs Value Object | Child entity (has identity via `id`) | ProductAttributeValue has a unique `id` and is individually addressable for CRUD operations (assign/remove). It is not a value object. |
| AggregateRoot or not | NOT an AggregateRoot | It is a simple pivot entity managed through its own repository (IProductAttributeValueRepository in MT-5). No domain events needed. Follows AttributeValue child entity pattern. |
| Fields | id, product_id, attribute_id, attribute_value_id | Minimal pivot entity. Matches the ORM model planned in MT-16 and the SKUAttributeValueLink ORM pattern. No extra metadata fields needed for MVP. |
| Factory method | `create()` classmethod with keyword-only args | Consistent with all other entity factory methods in the codebase (Brand.create, AttributeValue.create, etc.). Generates UUID if not provided. |
| Docstring style | Google-style with Attributes section | Matches existing entity docstrings (Brand, AttributeValue, SKU). |

---

## File plan

### `src/modules/catalog/domain/entities.py` -- MODIFY

**Purpose:** Add the `ProductAttributeValue` child entity class that represents a product-level attribute assignment (linking a product to a specific attribute dictionary value).
**Layer:** Domain

#### Classes:

**`ProductAttributeValue`** (new child entity)
- Decorator: `@dataclass` from `attr` (already imported)
- Does NOT extend `AggregateRoot`
- Fields:
  - `id: uuid.UUID` -- unique identifier for this assignment
  - `product_id: uuid.UUID` -- FK reference to the Product aggregate
  - `attribute_id: uuid.UUID` -- FK reference to the Attribute entity
  - `attribute_value_id: uuid.UUID` -- FK reference to the AttributeValue entity
- Factory method:
  - `create(*, product_id: uuid.UUID, attribute_id: uuid.UUID, attribute_value_id: uuid.UUID, pav_id: uuid.UUID | None = None) -> ProductAttributeValue` -- generates uuid4 for id if not provided
- No update method (immutable assignment -- to change value, delete and re-create)
- No domain events
- DI scope: N/A (plain domain entity, not injected)

#### Placement in file:

Insert the class **after** the `AttributeValue` class (around line 700) and **before** the `CategoryAttributeBinding` class. This keeps entity-attribute-related classes grouped together logically.

#### Imports:

No new imports required. All needed imports (`uuid`, `dataclass` from `attr`) are already present in the file.

#### Structural sketch (pseudo-code only):

```python
@dataclass
class ProductAttributeValue:
    """Product-level attribute assignment (EAV pivot entity).

    Links a product to a specific attribute dictionary value.
    This is a child entity -- not an aggregate root. It does not
    collect domain events; operations are managed through the
    ProductAttributeValue repository and command handlers.

    Attributes:
        id: Unique assignment identifier.
        product_id: FK to the parent Product aggregate.
        attribute_id: FK to the Attribute dictionary entry.
        attribute_value_id: FK to the specific AttributeValue chosen.
    """

    id: uuid.UUID
    product_id: uuid.UUID
    attribute_id: uuid.UUID
    attribute_value_id: uuid.UUID

    @classmethod
    def create(
        cls,
        *,
        product_id: uuid.UUID,
        attribute_id: uuid.UUID,
        attribute_value_id: uuid.UUID,
        pav_id: uuid.UUID | None = None,
    ) -> ProductAttributeValue:
        """Factory method to construct a new ProductAttributeValue.

        Args:
            product_id: UUID of the parent Product.
            attribute_id: UUID of the Attribute being assigned.
            attribute_value_id: UUID of the chosen AttributeValue.
            pav_id: Optional pre-generated UUID; generates uuid4 if omitted.

        Returns:
            A new ProductAttributeValue instance.
        """
        return cls(
            id=pav_id or uuid.uuid4(),
            product_id=product_id,
            attribute_id=attribute_id,
            attribute_value_id=attribute_value_id,
        )
```

---

## Dependency registration

No DI changes required for this micro-task.

## Migration plan

No database changes required for this micro-task.

## Integration points

No cross-module integration in this micro-task.

## Risks & edge cases

| Risk | Impact | Mitigation |
|------|--------|------------|
| Placement in entities.py conflicts with existing class ordering | Merge conflicts if MT-2 is still being reviewed | Place after AttributeValue, before CategoryAttributeBinding. MT-2 adds Product/SKU at the end of file, so no conflict. |
| Missing `__all__` export | Other modules cannot import the entity | entities.py does not use `__all__` -- all classes are importable directly. No action needed. |

## Acceptance verification

How senior-backend should verify this MT is correctly implemented:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy .
uv run pytest tests/unit/ tests/architecture/ -v
```

**Specific checks:**
- [ ] ProductAttributeValue is an attrs `@dataclass` with fields: id, product_id, attribute_id, attribute_value_id
- [ ] ProductAttributeValue.create() factory method generates UUID via uuid.uuid4()
- [ ] Entity is NOT an AggregateRoot (no domain events, no inheritance from AggregateRoot)
- [ ] Domain layer has zero framework imports
- [ ] No cross-module imports (events only)
- [ ] All writes go through UoW (N/A for this MT -- entity only)
- [ ] Pydantic only in presentation layer (N/A for this MT)
- [ ] All existing tests pass after this change
- [ ] Linter/type-checker passes
- [ ] Google-style docstring on class and factory method
