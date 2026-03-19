# Architecture Plan -- MT-4: Add Product domain exceptions

> **Pipeline run:** 20260318-121109
> **Micro-task:** MT-4
> **Layer:** Domain
> **Module:** catalog
> **FR Reference:** FR-001, FR-002, FR-003, FR-005, FR-006
> **Depends on:** MT-2

---

## Research findings

- No Context7 research needed. This micro-task is pure domain layer (stdlib + shared base exceptions only). No library APIs involved.
- SQLAlchemy `StaleDataError` is caught in the infrastructure/repository layer and re-raised as `ConcurrencyError` -- but `ConcurrencyError` itself is a plain domain exception inheriting from `ConflictError`.

---

## Design decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Exception constructor signatures | Match exact kwargs used in entities.py deferred imports | Product entity already calls `InvalidStatusTransitionError(current_status=..., target_status=..., allowed_transitions=...)`, `DuplicateVariantCombinationError(product_id=..., variant_hash=...)`, `SKUNotFoundError(sku_id=...)` -- constructors must accept these exact keyword arguments |
| ProductStatus type in InvalidStatusTransitionError | Accept `ProductStatus` enum values, format with `.value` in message and details | Keeps error details serializable (strings) while accepting domain enum types |
| ConcurrencyError genericity | Generic `entity_type: str` + `entity_id: uuid.UUID` | Reusable for Product, SKU, or any future aggregate that uses optimistic locking |
| Section placement | After existing "Product & SKU aggregate exceptions" section header | The section header already exists in exceptions.py at line 67; add new classes there, keeping existing `ProductNotFoundError` and `SKUOutOfStockError` |

---

## File plan

### `src/modules/catalog/domain/exceptions.py` -- MODIFY

**Purpose:** Add all Product/SKU-specific exception classes required by the Product aggregate root and future command handlers.
**Layer:** Domain

#### Classes to add (in order, after existing `SKUOutOfStockError` at line 94):

**`InvalidStatusTransitionError`** (new)
- Inherits from: `UnprocessableEntityError` (from `src.shared.exceptions`)
- Constructor args:
  - `current_status: ProductStatus` -- the product's current status
  - `target_status: ProductStatus` -- the requested target status
  - `allowed_transitions: list[ProductStatus]` -- valid transitions from current status
- Message: `"Cannot transition from '{current_status.value}' to '{target_status.value}'."`
- Error code: `"INVALID_STATUS_TRANSITION"`
- Details: `{"current_status": current_status.value, "target_status": target_status.value, "allowed_transitions": [s.value for s in allowed_transitions]}`
- NOTE: Must import `ProductStatus` from `src.modules.catalog.domain.value_objects`. This is a domain-to-domain import within the same module, which is allowed.

**`ProductSlugConflictError`** (new)
- Inherits from: `ConflictError` (from `src.shared.exceptions`)
- Constructor args:
  - `slug: str` -- the conflicting slug
- Message: `"Product with slug '{slug}' already exists."`
- Error code: `"PRODUCT_SLUG_CONFLICT"`
- Details: `{"slug": slug}`

**`SKUNotFoundError`** (new)
- Inherits from: `NotFoundError` (from `src.shared.exceptions`)
- Constructor args:
  - `sku_id: uuid.UUID | str` -- the SKU identifier that was not found
- Message: `"SKU with ID {sku_id} not found."`
- Error code: `"SKU_NOT_FOUND"`
- Details: `{"sku_id": str(sku_id)}`

**`SKUCodeConflictError`** (new)
- Inherits from: `ConflictError` (from `src.shared.exceptions`)
- Constructor args:
  - `sku_code: str` -- the conflicting SKU code
  - `product_id: uuid.UUID` -- the product owning this SKU
- Message: `"SKU with code '{sku_code}' already exists for this product."`
- Error code: `"SKU_CODE_CONFLICT"`
- Details: `{"sku_code": sku_code, "product_id": str(product_id)}`

**`DuplicateVariantCombinationError`** (new)
- Inherits from: `ConflictError` (from `src.shared.exceptions`)
- Constructor args:
  - `product_id: uuid.UUID` -- the product with the duplicate
  - `variant_hash: str` -- the computed SHA-256 hash that collided
- Message: `"A variant with the same attribute combination already exists."`
- Error code: `"DUPLICATE_VARIANT_COMBINATION"`
- Details: `{"product_id": str(product_id), "variant_hash": variant_hash}`

**`DuplicateProductAttributeError`** (new)
- Inherits from: `ConflictError` (from `src.shared.exceptions`)
- Constructor args:
  - `product_id: uuid.UUID` -- the product
  - `attribute_id: uuid.UUID` -- the duplicate attribute
- Message: `"Attribute is already assigned to this product."`
- Error code: `"DUPLICATE_PRODUCT_ATTRIBUTE"`
- Details: `{"product_id": str(product_id), "attribute_id": str(attribute_id)}`

**`ProductAttributeValueNotFoundError`** (new)
- Inherits from: `NotFoundError` (from `src.shared.exceptions`)
- Constructor args:
  - `product_id: uuid.UUID | str` -- the product
  - `attribute_id: uuid.UUID | str` -- the attribute whose value was not found
- Message: `"Product attribute value not found."`
- Error code: `"PRODUCT_ATTRIBUTE_VALUE_NOT_FOUND"`
- Details: `{"product_id": str(product_id), "attribute_id": str(attribute_id)}`

**`ConcurrencyError`** (new)
- Inherits from: `ConflictError` (from `src.shared.exceptions`)
- Constructor args:
  - `entity_type: str` -- e.g. "Product", "SKU"
  - `entity_id: uuid.UUID` -- the entity that had a version mismatch
  - `expected_version: int` -- the version the caller expected
  - `actual_version: int` -- the version found in the database
- Message: `"Concurrent modification detected for {entity_type} {entity_id}."`
- Error code: `"CONCURRENCY_ERROR"`
- Details: `{"entity_type": entity_type, "entity_id": str(entity_id), "expected_version": expected_version, "actual_version": actual_version}`

#### Imports to add:

```python
from src.modules.catalog.domain.value_objects import ProductStatus
```

This import is added at the top of the file alongside the existing imports. It is a same-module domain import (domain -> domain within catalog), which is allowed.

#### Structural sketch (pseudo-code only):

```python
# After existing SKUOutOfStockError class (line ~94), add:

class InvalidStatusTransitionError(UnprocessableEntityError):
    """Raised when a product status transition violates the FSM."""

    def __init__(
        self,
        current_status: ProductStatus,
        target_status: ProductStatus,
        allowed_transitions: list[ProductStatus],
    ):
        super().__init__(
            message=f"Cannot transition from '{current_status.value}' to '{target_status.value}'.",
            error_code="INVALID_STATUS_TRANSITION",
            details={
                "current_status": current_status.value,
                "target_status": target_status.value,
                "allowed_transitions": [s.value for s in allowed_transitions],
            },
        )

# ... remaining classes follow the same pattern
```

---

## Dependency registration

No DI changes required for this micro-task. Exceptions are instantiated directly (not injected).

## Migration plan

No database changes required for this micro-task.

## Integration points

No cross-module integration in this micro-task. All exceptions are internal to the catalog domain.

## Risks & edge cases

| Risk | Impact | Mitigation |
|------|--------|------------|
| Constructor signature mismatch with deferred imports in entities.py | Runtime `TypeError` when Product methods raise exceptions | Constructor kwargs MUST match exactly: `InvalidStatusTransitionError(current_status=, target_status=, allowed_transitions=)`, `DuplicateVariantCombinationError(product_id=, variant_hash=)`, `SKUNotFoundError(sku_id=)` |
| Circular import from importing ProductStatus | Import error at module load time | Not a risk: exceptions.py importing from value_objects.py is a one-way dependency (value_objects does not import from exceptions) |
| `ProductStatus.value` serialization | Details dict must contain JSON-serializable values | Using `.value` (str) on enum, not the enum instance itself |

## Acceptance verification

How senior-backend should verify this MT is correctly implemented:

```bash
uv run pytest tests/unit/ tests/architecture/ -v
uv run ruff check .
uv run mypy .
```

**Specific checks:**
- [ ] `InvalidStatusTransitionError` accepts `current_status`, `target_status`, `allowed_transitions` kwargs matching Product.change_status() usage
- [ ] `ProductSlugConflictError` accepts `slug: str`
- [ ] `SKUNotFoundError` accepts `sku_id: uuid.UUID | str` matching Product.remove_sku() usage
- [ ] `SKUCodeConflictError` accepts `sku_code: str` and `product_id: uuid.UUID`
- [ ] `DuplicateVariantCombinationError` accepts `product_id` and `variant_hash` matching Product.add_sku() usage
- [ ] `DuplicateProductAttributeError` accepts `product_id` and `attribute_id`
- [ ] `ProductAttributeValueNotFoundError` accepts `product_id` and `attribute_id`
- [ ] `ConcurrencyError` accepts `entity_type`, `entity_id`, `expected_version`, `actual_version`
- [ ] All exception classes have Google-style docstrings
- [ ] Domain layer has zero framework imports (only stdlib + shared exceptions + same-module value_objects)
- [ ] All existing tests pass (`uv run pytest tests/unit/ tests/architecture/ -v`)
- [ ] Linter passes (`uv run ruff check .`)
- [ ] Type checker passes (`uv run mypy .`)
