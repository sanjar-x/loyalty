# Architecture Plan -- MT-2: Add Product and SKU domain entities

> **Pipeline run:** 20260318-121109
> **Micro-task:** MT-2
> **Layer:** Domain
> **Module:** catalog
> **FR Reference:** FR-001, FR-002, FR-005, FR-006
> **Depends on:** MT-1

---

## Research findings

- **attrs** (current): `from attr import dataclass` is used throughout the codebase for domain entities. This decorator creates mutable attrs classes (equivalent to `@attr.s(auto_attribs=True)`). Mutable list fields must use `field(factory=list)` to avoid shared mutable default. `__attrs_post_init__` is available for post-init logic.
- **attrs**: `AggregateRoot` mixin provides `__attrs_post_init__` that initializes `_domain_events`. Child entities that do NOT extend `AggregateRoot` do not get this automatically -- they are plain `@dataclass` attrs classes.
- **hashlib** (stdlib): `hashlib.sha256(data).hexdigest()` returns a 64-character hex string. Allowed in domain layer as it is stdlib.
- **datetime** (stdlib): `datetime.now(UTC)` for timestamps. Already used in `DomainEvent`. Import from `datetime import UTC, datetime`.

---

## Design decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Product as AggregateRoot | Extends `AggregateRoot` via `@dataclass` from `attr` | Product is the aggregate root owning SKUs. Follows Brand/Category pattern. Even though events are deferred, the infrastructure is ready. |
| SKU as child entity | Plain `@dataclass` from `attr`, no AggregateRoot | SKU is owned by Product, not an independent aggregate. Follows AttributeValue pattern. |
| FSM transition table | `dict[ProductStatus, set[ProductStatus]]` class-level constant | Clean, readable FSM definition. Method `transition_status` validates against it and raises `InvalidStatusTransitionError`. |
| variant_hash algorithm | `hashlib.sha256` over sorted `(attr_id, attr_value_id)` tuples | Deterministic regardless of insertion order. Sorting by attribute_id UUID ensures consistency. 64-char hex string matches ORM `String(64)` column. |
| variant_attributes type | `list[tuple[uuid.UUID, uuid.UUID]]` | Each tuple is `(attribute_id, attribute_value_id)`. Simple stdlib types only. Matches MT acceptance criteria. |
| Optimistic locking | `version: int` field on both Product and SKU | Domain carries version; repository maps to ORM `version_id_col`. Version incremented by repository on save, not by domain entity. |
| Soft delete | `deleted_at: datetime | None` field, `soft_delete()` method | Sets `deleted_at = datetime.now(UTC)`. Already used in ORM models. |
| SKU price validation | Validated in SKU `__attrs_post_init__` and in `Product.add_sku()` | compare_at_price must be strictly greater than price when both are set. |
| published_at on PUBLISHED transition | Set inside `transition_status` | Only set when transitioning TO PUBLISHED, not cleared on other transitions. |
| Deferred imports for exceptions | Inline imports inside methods | Follows existing Brand entity pattern (e.g., `from ...exceptions import InvalidLogoStateException` inside method body). Avoids circular imports. |

---

## File plan

### `src/modules/catalog/domain/entities.py` -- MODIFY

**Purpose:** Add `Product` (AggregateRoot) and `SKU` (child entity) classes to the existing domain entities module.
**Layer:** Domain

#### Classes:

**`SKU`** (new child entity)
- Decorator: `@dataclass` from `attr`
- Does NOT extend `AggregateRoot`
- Fields:
  - `id: uuid.UUID`
  - `product_id: uuid.UUID`
  - `sku_code: str`
  - `variant_hash: str`
  - `price: Money`
  - `compare_at_price: Money | None = None`
  - `is_active: bool = True`
  - `version: int = 1`
  - `deleted_at: datetime | None = None`
  - `created_at: datetime = field(factory=lambda: datetime.now(UTC))`
  - `updated_at: datetime = field(factory=lambda: datetime.now(UTC))`
  - `variant_attributes: list[tuple[uuid.UUID, uuid.UUID]] = field(factory=list)`
- Validation in `__attrs_post_init__`:
  - If `compare_at_price is not None` and `price` is not None, validate `compare_at_price > price`. Raise `ValueError("compare_at_price must be greater than price")`.
- Methods:
  - `soft_delete() -> None` -- sets `deleted_at = datetime.now(UTC)`, sets `updated_at = datetime.now(UTC)`
  - `update(*, sku_code: str | None = None, price: Money | None = None, compare_at_price: Money | None | ... = ..., is_active: bool | None = None, variant_attributes: list[tuple[uuid.UUID, uuid.UUID]] | None = None, variant_hash: str | None = None) -> None` -- updates mutable fields, re-validates compare_at_price > price if either changed, sets `updated_at`
- DI scope: N/A (domain entity)
- Events raised: none (child entity)

**`Product`** (new aggregate root)
- Decorator: `@dataclass` from `attr`
- Extends: `AggregateRoot` (from `src.shared.interfaces.entities`)
- Class-level constant:
  ```
  _ALLOWED_TRANSITIONS: dict[ProductStatus, set[ProductStatus]]
  ```
  Mapping:
  - `DRAFT -> {ENRICHING}`
  - `ENRICHING -> {DRAFT, READY_FOR_REVIEW}`
  - `READY_FOR_REVIEW -> {ENRICHING, PUBLISHED}`
  - `PUBLISHED -> {ARCHIVED}`
  - `ARCHIVED -> {DRAFT}`
- Fields:
  - `id: uuid.UUID`
  - `slug: str`
  - `title_i18n: dict[str, str]`
  - `description_i18n: dict[str, str]`
  - `status: ProductStatus`
  - `brand_id: uuid.UUID`
  - `primary_category_id: uuid.UUID`
  - `supplier_id: uuid.UUID | None = None`
  - `country_of_origin: str | None = None`
  - `tags: list[str] = field(factory=list)`
  - `version: int = 1`
  - `deleted_at: datetime | None = None`
  - `created_at: datetime = field(factory=lambda: datetime.now(UTC))`
  - `updated_at: datetime = field(factory=lambda: datetime.now(UTC))`
  - `published_at: datetime | None = None`
  - `skus: list[SKU] = field(factory=list)`
- Factory method:
  - `create(cls, *, slug: str, title_i18n: dict[str, str], brand_id: uuid.UUID, primary_category_id: uuid.UUID, description_i18n: dict[str, str] | None = None, supplier_id: uuid.UUID | None = None, country_of_origin: str | None = None, tags: list[str] | None = None, product_id: uuid.UUID | None = None) -> Product`
    - Sets `status=ProductStatus.DRAFT`, `version=1`, `skus=[]`
    - Generates UUID via `uuid.uuid7()` (with uuid4 fallback) if product_id not provided
    - Validates `title_i18n` is non-empty
- Methods:
  - `update(*, title_i18n: dict[str, str] | None = None, description_i18n: dict[str, str] | None = None, slug: str | None = None, brand_id: uuid.UUID | None = None, primary_category_id: uuid.UUID | None = None, supplier_id: uuid.UUID | None = ..., country_of_origin: str | None = ..., tags: list[str] | None = None) -> None`
    - Uses sentinel `...` for nullable fields (supplier_id, country_of_origin) to distinguish "not provided" from "set to None"
    - Validates title_i18n is non-empty if provided
    - Sets `updated_at = datetime.now(UTC)`
  - `soft_delete() -> None` -- sets `deleted_at = datetime.now(UTC)`, sets `updated_at = datetime.now(UTC)`
  - `transition_status(new_status: ProductStatus) -> None`
    - Looks up `_ALLOWED_TRANSITIONS[self.status]`
    - If `new_status` not in allowed set, raises `InvalidStatusTransitionError` (deferred import from exceptions)
    - Sets `self.status = new_status`
    - If `new_status == ProductStatus.PUBLISHED`, sets `self.published_at = datetime.now(UTC)`
    - Sets `self.updated_at = datetime.now(UTC)`
  - `add_sku(*, sku_code: str, price: Money, compare_at_price: Money | None = None, is_active: bool = True, variant_attributes: list[tuple[uuid.UUID, uuid.UUID]] | None = None) -> SKU`
    - Computes `variant_hash` using `_compute_variant_hash(variant_attributes or [])`
    - Checks uniqueness: iterates `self.skus` (non-deleted only), if any existing SKU has same `variant_hash`, raises `DuplicateVariantCombinationError` (deferred import)
    - Creates `SKU` instance with generated `uuid.uuid7()` id
    - Appends to `self.skus`
    - Sets `self.updated_at = datetime.now(UTC)`
    - Returns the new SKU
  - `find_sku(sku_id: uuid.UUID) -> SKU | None` -- finds SKU by id in `self.skus` (non-deleted only)
  - `remove_sku(sku_id: uuid.UUID) -> None` -- finds SKU, calls `sku.soft_delete()`, sets `self.updated_at`
  - `_compute_variant_hash(variant_attributes: list[tuple[uuid.UUID, uuid.UUID]]) -> str` (static method)
    - Sorts `variant_attributes` by first element (attribute_id)
    - Concatenates as `"attr_id:value_id|attr_id:value_id|..."`
    - Returns `hashlib.sha256(concatenated.encode()).hexdigest()`
    - If empty list, returns hash of empty string (deterministic sentinel for zero-variant SKU)

#### New imports to add (at top of file):

```python
import hashlib
from datetime import UTC, datetime

from attr import Factory, dataclass, field

from src.modules.catalog.domain.value_objects import (
    # ... existing imports ...
    Money,
    ProductStatus,
)
```

Note: The existing file already imports `from attr import dataclass`. We need to also import `field` (or `Factory`) for list defaults. Check if `field` is already imported; if not, add it. Also add `hashlib`, `datetime`, and `UTC`.

#### Structural sketch (pseudo-code only):

```python
# Place SKU before Product since Product references SKU in its fields.

@dataclass
class SKU:
    """Stock Keeping Unit -- a specific product variant.

    Child entity owned by the Product aggregate. Each SKU represents
    a unique combination of variant attributes (e.g. size + color)
    identified by its ``variant_hash``.

    Attributes:
        id: Unique SKU identifier.
        product_id: FK to the owning Product aggregate.
        sku_code: Human-readable stock-keeping code.
        variant_hash: SHA-256 hash of sorted variant attribute pairs.
        price: Base price as a Money value object.
        compare_at_price: Previous/original price for strikethrough display.
        is_active: Whether the variant is available for sale.
        version: Optimistic locking version counter.
        deleted_at: Soft-delete timestamp, or None if active.
        created_at: Creation timestamp.
        updated_at: Last modification timestamp.
        variant_attributes: List of (attribute_id, attribute_value_id) tuples.
    """
    id: uuid.UUID
    product_id: uuid.UUID
    sku_code: str
    variant_hash: str
    price: Money
    compare_at_price: Money | None = None
    is_active: bool = True
    version: int = 1
    deleted_at: datetime | None = None
    created_at: datetime = field(factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(factory=lambda: datetime.now(UTC))
    variant_attributes: list[tuple[uuid.UUID, uuid.UUID]] = field(factory=list)

    def __attrs_post_init__(self) -> None:
        if self.compare_at_price is not None:
            if not self.compare_at_price > self.price:
                raise ValueError("compare_at_price must be greater than price")

    # update(), soft_delete() methods...


@dataclass
class Product(AggregateRoot):
    """Product aggregate root -- central catalog entity.

    Owns SKU child entities, enforces status lifecycle transitions (FSM),
    and computes variant hashes for SKU uniqueness. Carries version
    for optimistic locking and supports soft-delete.

    Attributes:
        id: Unique product identifier.
        slug: URL-safe unique identifier for routing.
        title_i18n: Multilingual product title.
        description_i18n: Multilingual product description.
        status: Current lifecycle state (FSM).
        brand_id: FK to the Brand aggregate.
        primary_category_id: FK to the primary Category.
        supplier_id: FK to the Supplier, or None.
        country_of_origin: ISO 3166-1 alpha-2 country code, or None.
        tags: List of searchable tags.
        version: Optimistic locking version counter.
        deleted_at: Soft-delete timestamp, or None if active.
        created_at: Creation timestamp.
        updated_at: Last modification timestamp.
        published_at: Timestamp of first publication, or None.
        skus: List of owned SKU child entities.
    """
    _ALLOWED_TRANSITIONS: ClassVar[dict[ProductStatus, set[ProductStatus]]] = {
        ProductStatus.DRAFT: {ProductStatus.ENRICHING},
        ProductStatus.ENRICHING: {ProductStatus.DRAFT, ProductStatus.READY_FOR_REVIEW},
        ProductStatus.READY_FOR_REVIEW: {ProductStatus.ENRICHING, ProductStatus.PUBLISHED},
        ProductStatus.PUBLISHED: {ProductStatus.ARCHIVED},
        ProductStatus.ARCHIVED: {ProductStatus.DRAFT},
    }

    id: uuid.UUID
    slug: str
    # ... all fields ...
    skus: list[SKU] = field(factory=list)

    @classmethod
    def create(cls, ...) -> Product: ...

    def transition_status(self, new_status: ProductStatus) -> None:
        allowed = self._ALLOWED_TRANSITIONS.get(self.status, set())
        if new_status not in allowed:
            from src.modules.catalog.domain.exceptions import InvalidStatusTransitionError
            raise InvalidStatusTransitionError(
                current_status=self.status,
                target_status=new_status,
                allowed_transitions=list(allowed),
            )
        self.status = new_status
        if new_status == ProductStatus.PUBLISHED:
            self.published_at = datetime.now(UTC)
        self.updated_at = datetime.now(UTC)

    def add_sku(self, ...) -> SKU:
        variant_hash = self._compute_variant_hash(variant_attributes or [])
        for existing in self.skus:
            if existing.deleted_at is None and existing.variant_hash == variant_hash:
                from src.modules.catalog.domain.exceptions import DuplicateVariantCombinationError
                raise DuplicateVariantCombinationError(
                    product_id=self.id, variant_hash=variant_hash
                )
        sku = SKU(id=..., product_id=self.id, sku_code=sku_code, variant_hash=variant_hash, price=price, ...)
        self.skus.append(sku)
        self.updated_at = datetime.now(UTC)
        return sku

    @staticmethod
    def _compute_variant_hash(variant_attributes: list[tuple[uuid.UUID, uuid.UUID]]) -> str:
        sorted_attrs = sorted(variant_attributes, key=lambda x: str(x[0]))
        payload = "|".join(f"{str(a)}:{str(v)}" for a, v in sorted_attrs)
        return hashlib.sha256(payload.encode()).hexdigest()
```

#### Important note on `ClassVar`:

The `_ALLOWED_TRANSITIONS` is a class-level constant, not an instance field. It must be annotated with `ClassVar` to exclude it from attrs' generated `__init__`. Import `from typing import ClassVar`.

#### Placement in file:

- Add `SKU` class BEFORE the `Product` class (since Product references SKU in its type annotations).
- Place both after the existing `CategoryAttributeBinding` class (end of current file).

#### Complete import block after modification:

```python
import hashlib
import uuid
from datetime import UTC, datetime
from typing import Any, ClassVar

from attr import dataclass, field

from src.modules.catalog.domain.value_objects import (
    DEFAULT_SEARCH_WEIGHT,
    MAX_SEARCH_WEIGHT,
    MIN_SEARCH_WEIGHT,
    AttributeDataType,
    AttributeLevel,
    AttributeUIType,
    MediaProcessingStatus,
    Money,
    ProductStatus,
    RequirementLevel,
    validate_validation_rules,
)
from src.shared.interfaces.entities import AggregateRoot
```

---

## Dependency registration

No DI changes required for this micro-task.

## Migration plan

No database changes required for this micro-task.

## Integration points

No cross-module integration in this micro-task.

- Domain events for Product lifecycle are **deferred** per enhancement plan (P2). No events emitted.

## Risks & edge cases

| Risk | Impact | Mitigation |
|------|--------|------------|
| `field(factory=list)` for `skus` and `tags` | Shared mutable default if not using factory | attrs `field(factory=list)` creates new list per instance. Verified via Context7. |
| `ClassVar` annotation for `_ALLOWED_TRANSITIONS` | attrs would try to make it an instance field without ClassVar | Annotate as `ClassVar[dict[...]]` so attrs ignores it. Standard Python/attrs pattern. |
| `_compute_variant_hash` with empty variant_attributes | Hash of empty string is deterministic but all zero-variant SKUs would collide | This is correct behavior: a product should have at most one SKU with no variant attributes. If business needs multiple, the hash design must change (future). |
| `compare_at_price` validation in `__attrs_post_init__` uses `Money.__gt__` | If currencies differ between price and compare_at_price, `ValueError` raised | This is correct domain behavior: compare_at_price and price must be same currency. |
| Deferred imports for exceptions | Exceptions from MT-4 do not exist yet | senior-backend implementing MT-2 should use placeholder string references in the raises. However, `InvalidStatusTransitionError` and `DuplicateVariantCombinationError` are defined in MT-4. Since MT-2 depends only on MT-1, and MT-4 depends on MT-2, the exceptions will NOT exist when MT-2 is implemented. **Resolution:** The import is deferred (inside method body). If exception classes do not exist yet, tests for transition/add_sku logic must wait until MT-4. The entity code will be syntactically valid but raise `ImportError` at runtime if the exception path is triggered before MT-4 is done. This is acceptable because: (1) the entity file will parse and import fine, (2) unit tests for FSM and add_sku will be written after MT-4. Alternative: define minimal stub exceptions now. **Recommendation:** senior-backend should add a minimal forward-reference comment, and the code will work once MT-4 delivers the exceptions. |
| `uuid.uuid7()` availability | Python 3.14 added uuid7; the codebase already uses `uuid.uuid7() if hasattr(uuid, "uuid7") else uuid.uuid4()` fallback | Follow existing pattern. |
| attrs `@dataclass` does not call `AggregateRoot.__attrs_post_init__` automatically for Product | `AggregateRoot.__attrs_post_init__` initializes `_domain_events`. If Product defines its own `__attrs_post_init__`, it must call `super().__attrs_post_init__()`. | Product does NOT need its own `__attrs_post_init__` (no post-init validation needed). The `AggregateRoot.__attrs_post_init__` will be called automatically by attrs. |
| SKU `__attrs_post_init__` -- SKU is not AggregateRoot | SKU has its own `__attrs_post_init__` for compare_at_price validation. No conflict with AggregateRoot. | Safe: SKU does not extend AggregateRoot. |

## Acceptance verification

How senior-backend should verify this MT is correctly implemented:

```bash
uv run pytest tests/unit/ tests/architecture/ -v
uv run ruff check .
uv run mypy .
```

**Specific checks:**
- [ ] Product is an attrs `@dataclass` extending `AggregateRoot`
- [ ] Product has all fields: id, slug, title_i18n, description_i18n, status, brand_id, primary_category_id, supplier_id (nullable), country_of_origin (nullable), tags, version, deleted_at (nullable), created_at, updated_at, published_at (nullable), skus (list of SKU)
- [ ] `Product.create()` factory sets status=DRAFT, version=1, skus=[]
- [ ] `Product.update()` allows updating title_i18n, description_i18n, slug, brand_id, primary_category_id, supplier_id, country_of_origin, tags
- [ ] `Product.soft_delete()` sets deleted_at to current UTC timestamp
- [ ] `Product.transition_status()` validates FSM: DRAFT->ENRICHING OK, DRAFT->PUBLISHED raises error
- [ ] `Product.transition_status(PUBLISHED)` sets published_at
- [ ] `Product.add_sku()` creates SKU with computed variant_hash
- [ ] `Product.add_sku()` raises on duplicate variant_hash (among non-deleted SKUs)
- [ ] SKU is an attrs `@dataclass` (NOT AggregateRoot)
- [ ] SKU has all fields: id, product_id, sku_code, variant_hash, price (Money), compare_at_price (Money, nullable), is_active, version, deleted_at (nullable), created_at, updated_at, variant_attributes
- [ ] SKU validates compare_at_price > price when both set
- [ ] `Product._compute_variant_hash()` produces deterministic SHA-256 hex for same input regardless of order
- [ ] Domain layer has zero framework imports
- [ ] No cross-module imports (events only)
- [ ] All existing tests pass after this change
- [ ] Linter/type-checker passes
