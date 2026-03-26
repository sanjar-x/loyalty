# Deep Code Review: Catalog EAV-система

**Reviewer:** External Senior Code Reviewer (AI-assisted)
**Date:** 2026-03-27
**Scope:** `src/modules/catalog/` — Domain, Infrastructure, Application, Presentation, Tests
**Branch:** `dev`

---

## Summary Table

| #   | Sev | Category       | File:Line                                 | Title                                                                     |
| --- | --- | -------------- | ----------------------------------------- | ------------------------------------------------------------------------- |
| 1   | P0  | Concurrency    | create_brand.py:74-76                     | TOCTOU race on slug uniqueness in all Create handlers                     |
| 2   | P1  | Concurrency    | delete_brand.py:55                        | Delete handlers use `get()` instead of `get_for_update()`                 |
| 3   | P1  | Correctness    | constants.py:40                           | STOREFRONT_CACHE_TTL=0 + post-commit invalidation = permanent stale cache |
| 4   | P1  | Data Model     | entities.py:604-677                       | AttributeGroup.code not guarded by `__setattr__`                          |
| 5   | P1  | Error Handling | exceptions.py (missing)                   | Missing `AttributeGroupNotFoundError` + no group_id FK validation         |
| 6   | P1  | Data Model     | models.py:59                              | ORM `uix_brands_name` not checked in handlers → raw IntegrityError        |
| 7   | P1  | Testing        | tests/\*\*/catalog/                       | 97% of handlers have ZERO test coverage                                   |
| 8   | P2  | Correctness    | entities.py:139-167                       | Brand.name accepts empty string                                           |
| 9   | P2  | Correctness    | entities.py:264 (all entities)            | sort_order accepts negative values in domain layer                        |
| 10  | P2  | Architecture   | events.py (missing)                       | No events for Brand/Category create/update                                |
| 11  | P2  | Architecture   | queries/\*.py (28 imports)                | All query handlers import ORM models (infra→app leak)                     |
| 12  | P2  | Correctness    | generate_sku_matrix.py:168-169            | SKU code collision fix not re-checked for uniqueness                      |
| 13  | P2  | Performance    | image_backend_client.py:30                | New HTTP client created per request                                       |
| 14  | P2  | Concurrency    | update_product.py:128                     | UpdateProductHandler missing pessimistic lock                             |
| 15  | P2  | Concurrency    | add_sku.py:97                             | AddSKUHandler missing pessimistic lock                                    |
| 16  | P2  | Security       | schemas.py:171,599                        | No URL validation on logo_url / source_url (SSRF risk)                    |
| 17  | P2  | Security       | create_product.py:156-174                 | Unbounded JSONB in media `image_variants`                                 |
| 18  | P2  | Correctness    | entities.py:1259,1375                     | SKU/Variant.update() bumps updated_at even with no changes                |
| 19  | P2  | Correctness    | entities.py:367-375                       | effective_template_id split responsibility (entity vs handler)            |
| 20  | P3  | Correctness    | create_brand.py:72                        | Handler generates uuid4, bypassing entity's uuid7 factory                 |
| 21  | P3  | Performance    | schemas.py:600                            | No max_length on Product tags array                                       |
| 22  | P3  | Correctness    | delete_product.py:52-60                   | Soft-delete does not clean up media assets                                |
| 23  | P1  | Data Model     | models.py:145-146                         | Category cascade="all, delete-orphan" contradicts ondelete="RESTRICT"     |
| 24  | P1  | Correctness    | entities.py:1197-1257                     | SKU.update() allows variant_hash change without uniqueness check          |
| 25  | P1  | Correctness    | entities.py:1666-1690                     | No ProductDeletedEvent emitted on soft-delete                             |
| 26  | P1  | Concurrency    | set_attribute_value_active.py:102-112     | Post-commit DB query + swallowed exception = stale cache forever          |
| 27  | P2  | Data Model     | models.py:351-353 + 831-832               | Attribute.values cascade contradicts downstream RESTRICT FKs              |
| 28  | P2  | Correctness    | entities.py:260-331                       | Category.create_root/create_child don't validate name_i18n                |
| 29  | P2  | Correctness    | bulk_assign_product_attributes.py:107-152 | Missing intra-batch duplicate guard                                       |
| 30  | P2  | Security       | router_storefront.py:162                  | Cache-Control: public on authenticated /form-attributes                   |
| 31  | P2  | Performance    | generate_sku_matrix.py:163-183            | N+1 query: check_sku_code_exists in loop (up to 1000 queries)             |
| 32  | P2  | Performance    | router_skus.py:177-232                    | SKU ownership check fetches ALL SKUs (limit=None), done 2x                |
| 33  | P2  | Correctness    | bind_attribute_to_template.py:157-163     | Post-commit unprotected DB query → 500 after successful write             |
| 34  | P3  | Data Model     | models.py:319-321                         | search_weight has no DB CHECK constraint (1-10)                           |
| 35  | P3  | Performance    | models.py:530                             | published_at column has no index (used in filter+sort)                    |

---

## Findings

### [P0] Concurrency: TOCTOU race on slug/code uniqueness in ALL Create handlers

**File:** `src/modules/catalog/application/commands/create_brand.py:74-76`
**Code:**
```python
async with self._uow:
    if await self._brand_repo.check_slug_exists(command.slug):
        raise BrandSlugConflictError(slug=command.slug)
    brand = Brand.create(...)
    brand = await self._brand_repo.add(brand)
    await self._uow.commit()
```

**Problem:** Check-then-act pattern without row-level locking. Two concurrent requests with the same slug both pass `check_slug_exists` → False before either commits. The second `commit()` fails with a raw `IntegrityError` (unique constraint violation on the DB index) instead of a clean `BrandSlugConflictError`. This affects **every** Create handler in the module: `CreateBrandHandler`, `CreateCategoryHandler`, `CreateAttributeHandler` (code+slug), `CreateProductHandler`, `AddAttributeValueHandler` (code+slug), `CreateAttributeTemplateHandler`, `BindAttributeToTemplateHandler`.

**Сценарий:**
1. Request A: `POST /brands {slug: "nike"}` → `check_slug_exists("nike")` → False
2. Request B: `POST /brands {slug: "nike"}` → `check_slug_exists("nike")` → False (A not committed yet)
3. Request A: `commit()` → success
4. Request B: `commit()` → `IntegrityError` → **500 Internal Server Error**

**Fix:** Catch `IntegrityError` at the repository layer and translate to the domain exception:
```python
from sqlalchemy.exc import IntegrityError

async def add(self, entity: DomainBrand) -> DomainBrand:
    try:
        ...
        await self._session.flush()
    except IntegrityError as e:
        if "uix_brands_slug" in str(e.orig):
            raise BrandSlugConflictError(slug=entity.slug) from e
        raise
```

**Impact:** Under concurrent load, duplicate slug/code creation produces 500 errors instead of 409 Conflict responses. Every admin user creating brands/categories/attributes simultaneously can hit this.

---

### [P1] Concurrency: DeleteBrandHandler uses `get()` without pessimistic lock

**File:** `src/modules/catalog/application/commands/delete_brand.py:55`
**Code:**
```python
async with self._uow:
    brand = await self._brand_repo.get(command.brand_id)  # No lock!
    if brand is None:
        raise BrandNotFoundError(...)
    has_products = await self._brand_repo.has_products(command.brand_id)
    brand.validate_deletable(has_products=has_products)
    await self._brand_repo.delete(command.brand_id)
    await self._uow.commit()
```

**Problem:** The deletion guard `has_products` is checked without a `FOR UPDATE` lock. Between the check and the delete, a concurrent transaction could create a product referencing this brand. The DB FK (`ondelete="RESTRICT"`) prevents actual data corruption, but the error surfaces as a raw `IntegrityError` (500) instead of `BrandHasProductsError` (409). Same pattern in `DeleteCategoryHandler`.

**Сценарий:**
1. Thread A: `has_products(brand_id)` → False
2. Thread B: creates a product with `brand_id`
3. Thread A: `delete(brand_id)` → FK violation → **500 IntegrityError**

**Fix:** `brand = await self._brand_repo.get_for_update(command.brand_id)`

**Impact:** Race condition window where brand deletion fails with 500 instead of 409.

---

### [P1] Correctness: STOREFRONT_CACHE_TTL=0 combined with post-commit invalidation = permanent stale cache

**File:** `src/modules/catalog/application/constants.py:40-46`
**Code:**
```python
STOREFRONT_CACHE_TTL = 0
"""TTL in seconds for storefront attribute cache entries (0 = no expiration)."""
```

**Problem:** Storefront caches have **zero TTL** (infinite lifetime). They rely entirely on explicit invalidation. But invalidation happens **outside** the transaction (after `commit()`), and failures are silently swallowed:
```python
# update_category.py:188-193
try:
    await self._cache.delete(CATEGORY_TREE_CACHE_KEY)
except Exception as e:
    self._logger.warning("Failed to invalidate ...", error=str(e))
```
If Redis is briefly unavailable when invalidation runs, the stale cache persists **forever** — there is no TTL safety net and no retry mechanism.

**Сценарий:**
1. Admin updates a category template binding
2. Transaction commits successfully
3. Redis connection times out during cache invalidation
4. `self._logger.warning(...)` is logged but nobody notices
5. Storefront serves stale attribute data **indefinitely**

**Fix:** Set a safety-net TTL: `STOREFRONT_CACHE_TTL = 3600` (1 hour). Even if invalidation fails, caches self-heal within bounded time.

**Impact:** Permanent stale data on the storefront with no automatic recovery mechanism.

---

### [P1] Data Model: AttributeGroup.code not guarded by `__setattr__`

**File:** `src/modules/catalog/domain/entities.py:604-677`
**Code:**
```python
@dataclass
class AttributeGroup(AggregateRoot):
    id: uuid.UUID
    code: str           # Documented as immutable — but NO __setattr__ guard!
    name_i18n: dict[str, str]
    sort_order: int
    # No __setattr__ override, unlike Brand/Category/AttributeTemplate/Product
```

**Problem:** `Brand`, `Category`, `AttributeTemplate`, and `Product` all protect immutable fields via `__setattr__` overrides. `AttributeGroup` documents `code` as immutable ("immutable after creation") but has no enforcement. `group.code = "new-code"` succeeds silently, and the ORM propagates the change to the database.

**Сценарий:**
1. Developer accidentally writes `group.code = "new"` in a handler
2. `repo.update(group)` persists the change
3. All code-based lookups (`get_by_code`) return unexpected results

**Fix:**
```python
def __setattr__(self, name: str, value: object) -> None:
    if name == "code" and getattr(self, "_AttributeGroup__initialized", False):
        raise AttributeError("Cannot set 'code' directly on AttributeGroup.")
    super().__setattr__(name, value)

def __attrs_post_init__(self) -> None:
    super().__attrs_post_init__()
    object.__setattr__(self, "_AttributeGroup__initialized", True)
```

**Impact:** Violated immutability invariant; accidental code mutation breaks referential integrity.

---

### [P1] Error Handling: Missing `AttributeGroupNotFoundError` + no group_id FK validation

**File:** `src/modules/catalog/domain/exceptions.py` (class entirely absent)
**File:** `src/modules/catalog/application/commands/create_attribute.py:117-133`
**Code:**
```python
# create_attribute.py — group_id passed without existence check
attribute = Attribute.create(
    ...
    group_id=command.group_id,  # What if this UUID doesn't exist?
    ...
)
```

**Problem:** There is no `AttributeGroupNotFoundError` exception in the domain. Neither `CreateAttributeHandler` nor `UpdateAttributeHandler` validates that `group_id` references an existing group. If the group doesn't exist, the DB FK constraint triggers an unhandled `IntegrityError`.

**Сценарий:**
1. `POST /attributes { group_id: "nonexistent-uuid", ... }`
2. Handler passes it through to `Attribute.create()`
3. Repository `flush()` → FK violation → **500 IntegrityError** instead of 404

**Fix:**
```python
# exceptions.py
class AttributeGroupNotFoundError(NotFoundError):
    def __init__(self, group_id: uuid.UUID | str):
        super().__init__(
            message=f"Attribute group with ID {group_id} not found.",
            error_code="ATTRIBUTE_GROUP_NOT_FOUND",
            details={"group_id": str(group_id)},
        )

# create_attribute.py handler
if command.group_id is not None:
    group = await self._group_repo.get(command.group_id)
    if group is None:
        raise AttributeGroupNotFoundError(group_id=command.group_id)
```

**Impact:** Raw database errors leak to API consumers instead of clean 404 responses.

---

### [P1] Data Model: ORM `uix_brands_name` not validated in handlers

**File:** `src/modules/catalog/infrastructure/models.py:59`
**Code:**
```python
__table_args__ = (
    Index("uix_brands_name", "name", unique=True),
    ...
)
```

**Problem:** The ORM declares a unique index on `name`, but neither `CreateBrandHandler` nor `UpdateBrandHandler` checks for name uniqueness before persisting. A duplicate name produces an unhandled `IntegrityError`.

**Сценарий:**
1. Brand "Nike" exists
2. `POST /brands { name: "Nike", slug: "nike-2" }` → passes slug check → `IntegrityError` on name → **500**

**Fix:** Either add `check_name_exists()` to `IBrandRepository` and validate in handlers, or remove the unique index if name uniqueness is not a business requirement.

**Impact:** Duplicate brand name creation produces 500 errors.

---

### [P1] Testing: 97% of handlers have ZERO test coverage

**Test files found:**
```
tests/integration/.../commands/test_create_brand.py       (1 of 39 commands)
tests/integration/.../repositories/test_brand.py
tests/integration/.../repositories/test_brand_extended.py
tests/integration/.../repositories/test_category.py
tests/integration/.../repositories/test_category_effective_family.py
tests/integration/.../repositories/test_category_extended.py
tests/unit/.../test_sync_product_media.py
tests/unit/.../domain/test_category_effective_family.py
tests/unit/.../infrastructure/test_image_backend_client.py
```

**Handlers:** 39 commands + 22 queries = 61 total handlers.
**Tested:** 1 command handler (CreateBrand). **0 query handlers.**

**ZERO tests for:**
- Product aggregate (FSM transitions, variant/SKU management, hash computation)
- All attribute CRUD handlers (create, update, delete)
- All attribute value handlers (add, bulk_add, update, delete, reorder)
- All template/binding handlers
- All product handlers except partial brand-related tests
- ALL 22 query handlers
- ALL presentation layer routers
- Concurrency scenarios (optimistic locking, TOCTOU)
- EAV attribute assignment (assign, bulk_assign)

**Impact:** Any of the bugs in this review could be caught by tests. Without automated coverage, regressions are undetectable before production.

---

### [P2] Correctness: Brand.name accepts empty string

**File:** `src/modules/catalog/domain/entities.py:139-167`
**Code:**
```python
@classmethod
def create(cls, name: str, slug: str, ...) -> Brand:
    _validate_slug(slug, "Brand")
    # name is never validated!
    return cls(id=brand_id or _generate_id(), name=name, ...)
```

**Problem:** `Brand.create()` and `Brand.update()` accept `name=""` without validation. Other entities (Category, Attribute, AttributeGroup) validate their `name_i18n` for non-emptiness, but Brand's plain `name: str` is unchecked.

**Fix:** `if not name or not name.strip(): raise ValueError("Brand name must be non-empty")`

**Impact:** Blank brand names in storefront/admin UI.

---

### [P2] Correctness: sort_order accepts negative values across all entities

**File:** `src/modules/catalog/domain/entities.py` (Category, AttributeGroup, Attribute, ProductVariant, SKU, TemplateAttributeBinding)

**Problem:** No domain entity validates `sort_order >= 0`. Pydantic schemas enforce `ge=0`, but code paths bypassing the presentation layer (internal commands, migration scripts, tests) can set negative values, violating the documented "lower = first" ordering invariant.

**Fix:** Add `if sort_order < 0: raise ValueError(...)` to each entity's factory method and update method.

**Impact:** Negative sort orders cause unpredictable display ordering.

---

### [P2] Architecture: Missing events for Brand create/update, Category create/update

**File:** `src/modules/catalog/domain/events.py`

**Problem:** Event audit shows `BrandDeletedEvent` and `CategoryDeletedEvent` exist, but there are no `BrandCreatedEvent`, `BrandUpdatedEvent`, `CategoryCreatedEvent`, or `CategoryUpdatedEvent`. The create/update handlers do not emit any domain events. Downstream consumers (search index sync, audit logs) cannot learn about brand/category creation or modification.

**Impact:** Incomplete event sourcing; downstream systems miss create/update operations.

---

### [P2] Architecture: All 22 query handlers import ORM models directly

**File:** 28 import statements across `src/modules/catalog/application/queries/`
**Example:**
```python
# get_brand.py:16
from src.modules.catalog.infrastructure.models import Brand as OrmBrand
```

**Problem:** Query handlers in the **application** layer directly import **infrastructure** ORM models. This violates hexagonal architecture's dependency rule. 28 import statements across all query handlers.

**Impact:** Tight coupling between application and infrastructure layers. ORM refactoring requires application-layer changes.

---

### [P2] Correctness: generate_sku_matrix collision fix not re-checked

**File:** `src/modules/catalog/application/commands/generate_sku_matrix.py:168-169`
**Code:**
```python
if await self._product_repo.check_sku_code_exists(sku_code):
    sku_code = f"{sku_code}-{i + 1}"
    # New sku_code NEVER re-checked for uniqueness!
```

**Problem:** If the suffixed code also exists, `add_sku()` will fail with a DB unique constraint violation.

**Fix:** Use a `while` loop or add a UUID fragment for guaranteed uniqueness.

**Impact:** SKU matrix generation can fail with unhandled database errors.

---

### [P2] Performance: ImageBackendClient creates new HTTP client per request

**File:** `src/modules/catalog/infrastructure/image_backend_client.py:30`
**Code:**
```python
async with httpx.AsyncClient(timeout=10.0) as client:
    resp = await client.delete(url, ...)
```

**Problem:** Each `delete()` creates a new `httpx.AsyncClient` → new connection pool, TCP handshake, potential TLS negotiation. For bulk operations (deleting a product with 20 media assets), this is inefficient.

**Fix:** Create client once in `__init__` and reuse across requests.

**Impact:** Increased latency for media cleanup; wasteful TCP connections.

---

### [P2] Concurrency: UpdateProductHandler / AddSKUHandler missing pessimistic lock

**File:** `src/modules/catalog/application/commands/update_product.py:128`, `add_sku.py:97`
**Code:**
```python
product = await self._product_repo.get_with_variants(command.product_id)  # No FOR UPDATE
```

**Problem:** Write operations use `get_with_variants` (no lock) instead of `get_for_update_with_variants`. Slug uniqueness and duplicate variant hash checks are subject to TOCTOU races. Optimistic locking catches it eventually but produces confusing error messages and wasted work.

**Fix:** Use `get_for_update_with_variants` for all write operations on products.

**Impact:** 500 errors from unhandled IntegrityError under concurrent product modifications.

---

### [P2] Security: No URL validation on logo_url / source_url

**File:** `src/modules/catalog/presentation/schemas.py`
**Code:**
```python
logo_url: str | None = None     # No URL format validation
source_url: str | None = Field(None, max_length=1024)  # Only length check
```

**Problem:** These fields accept arbitrary strings including `file:///etc/passwd`, `http://169.254.169.254/...` (SSRF), or `javascript:` URLs.

**Fix:** `logo_url: HttpUrl | None = None` or validate scheme is `http`/`https`.

**Impact:** Potential SSRF if any downstream service fetches stored URLs; XSS if rendered unsanitized.

---

### [P2] Security: Unbounded JSONB in media `image_variants`

**File:** `src/modules/catalog/application/commands/create_product.py:156-174`
**Code:**
```python
media: list[dict] | None = None  # Completely unvalidated
...
image_variants=item.get("image_variants"),  # Stored directly in JSONB
```

**Problem:** `media` items bypass the `BoundedJsonDict` validator used elsewhere. Arbitrary size/depth JSON is stored directly in JSONB columns.

**Fix:** Validate through Pydantic schemas with `BoundedJsonDict` constraints.

**Impact:** Potential DoS via database bloat from multi-MB JSON payloads.

---

### [P2] Correctness: SKU/Variant.update() always bumps updated_at

**File:** `src/modules/catalog/domain/entities.py:1259,1375`
**Code:**
```python
def update(self, **kwargs: Any) -> None:
    ...
    self.updated_at = datetime.now(UTC)  # Always, even if kwargs is empty
```

**Problem:** `updated_at` is set unconditionally, even when no fields actually changed. Causes unnecessary DB writes and misleading audit trails.

**Fix:** Track whether any mutation occurred; only update timestamp if so.

**Impact:** False audit trail; unnecessary database writes.

---

### [P2] Correctness: effective_template_id split responsibility

**File:** `src/modules/catalog/domain/entities.py:367-375`

**Problem:** `Category.update()` partially manages `effective_template_id` (sets it when template_id is non-None, clears to None when cleared), but defers parent-inheritance logic to the handler. Any new handler calling `category.update(template_id=None)` without the re-inheritance logic (lines 159-165 of `update_category.py`) would leave `effective_template_id = None` instead of inheriting from parent.

**Impact:** Maintenance hazard; easy to break effective_template_id propagation.

---

### [P3] Correctness: CreateBrandHandler generates uuid4, bypassing entity's uuid7

**File:** `src/modules/catalog/application/commands/create_brand.py:72`
**Code:**
```python
brand_id = uuid.uuid4()  # Hardcoded uuid4, not _generate_id() which prefers uuid7
```

**Problem:** The handler hardcodes `uuid4` while all other entities use `_generate_id()` (uuid7 when available). Inconsistent UUID versioning.

**Fix:** Remove `brand_id = uuid.uuid4()` and pass `brand_id=None` to let the entity factory use `_generate_id()`.

**Impact:** Brand IDs lose time-sortable ordering on Python 3.13+.

---

### [P3] Performance: No max_length on Product tags array

**File:** `src/modules/catalog/presentation/schemas.py`

**Problem:** `tags: list[str]` has no upper bound on element count or string length. An attacker can send thousands of long tags.

**Fix:** `tags: list[Annotated[str, Field(max_length=100)]] = Field(default_factory=list, max_length=100)`

**Impact:** Potential DoS via database bloat; slow GIN index maintenance.

---

### [P3] Correctness: Soft-delete product does not clean up media assets

**File:** `src/modules/catalog/application/commands/delete_product.py:52-60`

**Problem:** `Product.soft_delete()` cascades to variants/SKUs but does not clean up `media_assets` records or storage objects. Orphaned media accumulates over time.

**Fix:** Call `media_repo.delete_by_product()` during product deletion, or schedule async cleanup.

**Impact:** Storage waste from orphaned media files.

---

## Additional Findings (from parallel review agents)

### [P1] Data Model: Category cascade="all, delete-orphan" contradicts ondelete="RESTRICT"

**File:** `src/modules/catalog/infrastructure/models.py:145-146`
**Code:**
```python
children: Mapped[list[Category]] = relationship(
    "Category", back_populates="parent", cascade="all, delete-orphan"
)
# But FK has: ForeignKey("categories.id", ondelete="RESTRICT")
```

**Problem:** The FK `parent_id` has `ondelete="RESTRICT"` (line 113), which prevents deleting a parent with children. But the ORM relationship has `cascade="all, delete-orphan"`, telling SQLAlchemy to cascade deletes to children. These contradict. If SQLAlchemy fires first, it silently destroys the subtree, bypassing `validate_deletable`. If the DB fires first, you get an IntegrityError instead of `CategoryHasChildrenError`.

**Fix:** Change to `cascade="save-update, merge"` — the domain guard handles delete validation.

**Impact:** Accidental category subtree deletion bypassing domain guards.

---

### [P1] Correctness: SKU.update() allows variant_hash change without uniqueness check

**File:** `src/modules/catalog/domain/entities.py:1197-1257`
**Code:**
```python
_UPDATABLE_FIELDS: ClassVar[frozenset[str]] = frozenset({
    "sku_code", "price", "compare_at_price", "is_active",
    "variant_attributes", "variant_hash",  # Both directly mutable!
})
```

**Problem:** `SKU.update()` allows changing `variant_attributes` and `variant_hash` independently, without validating (a) hash matches attributes, (b) hash doesn't collide with another active SKU. In contrast, `Product.add_sku()` properly computes and checks. `SKU.update()` bypasses both.

**Scenario:** `sku.update(variant_hash="same_hash_as_another_sku")` — no duplicate check. Or `sku.update(variant_attributes=new_attrs)` without updating hash — inconsistency.

**Fix:** Remove `variant_attributes`/`variant_hash` from `_UPDATABLE_FIELDS`. Force changes through `Product` aggregate methods.

**Impact:** Duplicate variant combinations in DB; incorrect product displays; cart/checkout errors.

---

### [P1] Correctness: No ProductDeletedEvent emitted on soft-delete

**File:** `src/modules/catalog/domain/entities.py:1666-1690`
**Code:**
```python
def soft_delete(self) -> None:
    ...
    self.deleted_at = now
    for variant in self.variants:
        if variant.deleted_at is None:
            variant.soft_delete()
    # No domain event emitted!
```

**Problem:** Product creation emits `ProductCreatedEvent`, updates emit `ProductUpdatedEvent`, status changes emit `ProductStatusChangedEvent`, but soft-deletion emits nothing. There is no `ProductDeletedEvent` class in events.py. Downstream consumers (search index, analytics) will never learn a product was deleted.

**Fix:** Create `ProductDeletedEvent` and emit from `Product.soft_delete()`.

**Impact:** Search index retains deleted products; ghost products in downstream systems.

---

### [P1] Concurrency: Post-commit DB query + swallowed exception in set_attribute_value_active

**File:** `src/modules/catalog/application/commands/set_attribute_value_active.py:102-112`
**Code:**
```python
# AFTER the `async with self._uow:` block exits:
try:
    template_ids = await self._binding_repo.get_template_ids_for_attribute(
        command.attribute_id
    )
    for tid in template_ids:
        await invalidate_template_effective_cache(self._cache, self._template_repo, tid)
except Exception as exc:
    self._logger.warning("cache_invalidation_failed", error=str(exc))
```

**Problem:** Two issues: (1) `get_template_ids_for_attribute()` is a DB query AFTER the UoW block exits — the session may be closed. (2) The bare `except Exception` swallows ALL failures including `SessionClosedError`. Combined with `STOREFRONT_CACHE_TTL=0`, a single failure means stale data forever.

**Fix:** Move the DB query inside the UoW block. Keep only cache deletion in try/except after commit.

**Impact:** Stale storefront caches served indefinitely after any Redis/session failure.

---

### [P2] Data Model: Attribute.values cascade contradicts downstream RESTRICT FKs

**File:** `src/modules/catalog/infrastructure/models.py:351-353`
**Code:**
```python
values: Mapped[list[AttributeValue]] = relationship(
    "AttributeValue", back_populates="attribute", cascade="all, delete-orphan"
)
```

**Problem:** ORM cascades delete of Attribute→AttributeValues, but `sku_attribute_values.attribute_value_id` has `ondelete="RESTRICT"`. Domain guard only checks `has_product_attribute_values`, not SKU-level references.

**Fix:** Also check SKU-level references in delete guard. Consider removing ORM delete cascade.

**Impact:** IntegrityError when deleting attributes with SKU-referenced values.

---

### [P2] Correctness: Category.create_root/create_child don't validate name_i18n

**File:** `src/modules/catalog/domain/entities.py:260-331`

**Problem:** Unlike `AttributeGroup.create()`, `Attribute.create()`, and `Product.create()` which all validate `name_i18n` is non-empty, `Category.create_root()` and `create_child()` accept `name_i18n={}` silently. Same for `Category.update()`.

**Fix:** `if not name_i18n: raise ValueError("name_i18n must contain at least one language entry")`

**Impact:** Categories with empty display names.

---

### [P2] Correctness: Missing intra-batch duplicate guard in bulk_assign_product_attributes

**File:** `src/modules/catalog/application/commands/bulk_assign_product_attributes.py:107-152`

**Problem:** The handler checks existing DB assignments but not duplicates within the batch itself. Two items with the same `attribute_id` both pass the check, resulting in either an IntegrityError or duplicate EAV records.

**Fix:** Add `seen_attr_ids = set()` duplicate check before processing.

**Impact:** 500 error or data corruption (multiple values for same attribute on one product).

---

### [P2] Security: Cache-Control: public on authenticated /form-attributes endpoint

**File:** `src/modules/catalog/presentation/router_storefront.py:162`
**Code:**
```python
# Requires catalog:manage permission but...
response.headers["Cache-Control"] = "public, max-age=300, s-maxage=3600"
```

**Problem:** Admin-only endpoint sends `Cache-Control: public`, telling CDNs to cache the response. An admin's response could be served to unauthenticated users.

**Fix:** `Cache-Control: private, max-age=300` for authenticated endpoints.

**Impact:** Admin-only catalog configuration data leaked through shared caches.

---

### [P2] Performance: N+1 query in generate_sku_matrix (up to 1000 queries in loop)

**File:** `src/modules/catalog/application/commands/generate_sku_matrix.py:163-183`

**Problem:** For each combination (up to 1000), a separate `check_sku_code_exists` query is executed. With 1000 combinations = 1000 sequential DB roundtrips.

**Fix:** Batch-generate all candidate codes, then `WHERE sku_code IN (...)` in one query.

**Impact:** SKU matrix generation extremely slow for large combinations; potential request timeout.

---

### [P2] Performance: SKU ownership check fetches ALL SKUs twice per update

**File:** `src/modules/catalog/presentation/router_skus.py:177-232`
**Code:**
```python
sku_list = await list_handler.handle(
    ListSKUsQuery(product_id=product_id, variant_id=variant_id, limit=None)
)
if not any(s.id == sku_id for s in sku_list.items):
    raise SKUNotFoundError(sku_id=sku_id)
```

**Problem:** Loads ALL SKUs for a variant (no limit) and does in-memory linear scan. For update_sku, this happens TWICE (before and after update).

**Fix:** Add `exists_sku_for_variant()` repository method — constant-time single-row check.

**Impact:** O(n) memory and DB load for what should be O(1).

---

### [P2] Correctness: Post-commit unprotected DB query in bind_attribute_to_template

**File:** `src/modules/catalog/application/commands/bind_attribute_to_template.py:157-163`

**Problem:** `get_category_ids_by_template_ids()` runs AFTER the UoW block exits. Unlike the cache invalidation (wrapped in try/except), this DB query is completely unprotected. Session closed → unhandled exception → 500 after successful write.

**Fix:** Move inside UoW block or wrap in try/except.

**Impact:** Intermittent 500 errors after successful binding creation.

---

### [P3] Data Model: search_weight has no DB CHECK constraint

**File:** `src/modules/catalog/infrastructure/models.py:319-321`

**Problem:** Domain validates 1-10, but no DB constraint. Direct SQL can insert invalid values.

**Fix:** `CheckConstraint("search_weight BETWEEN 1 AND 10")`

---

### [P3] Performance: published_at column missing index

**File:** `src/modules/catalog/infrastructure/models.py:530`

**Problem:** `ListProductsHandler` filters and sorts by `published_at`, but there's no index. Full table scan on large datasets.

**Fix:** Add partial index: `Index("ix_products_published_at", "published_at", postgresql_where=text("deleted_at IS NULL AND published_at IS NOT NULL"))`

---

## Scorecard

| Category           | Score (1-10) | Critical Issues |
| ------------------ | :----------: | :-------------: |
| Correctness        |      4       |        8        |
| Security           |      6       |        3        |
| Performance        |      6       |        4        |
| Architecture (DDD) |      6       |        2        |
| Error Handling     |      5       |        3        |
| Data Model         |      5       |        5        |
| Concurrency        |      3       |        7        |
| Test Coverage      |      2       |        1        |
| **Overall**        |    **4**     |     **35**      |

---

## Verdict

```
[ ] READY for production
[x] NOT READY (list P0 blockers)
```

### P0 Blockers (must fix before launch):
1. **TOCTOU race on slug/code uniqueness** — Every create handler can produce 500 errors under concurrent load. Catch `IntegrityError` and translate to domain exceptions.

### P1 Issues (10 — fix before or immediately after launch):
2. Delete handlers use `get()` instead of `get_for_update()`
3. Stale cache with no TTL safety net (STOREFRONT_CACHE_TTL=0)
4. AttributeGroup.code immutability not enforced
5. Missing group_id FK validation → raw IntegrityError
6. Brand name unique index not validated in handlers
7. ~97% handler test coverage gap (3.3% handler coverage rate)
8. Category ORM cascade="all, delete-orphan" contradicts ondelete="RESTRICT"
9. SKU.update() allows variant_hash change without uniqueness check
10. No ProductDeletedEvent emitted on soft-delete
11. Post-commit DB query + swallowed exception in set_attribute_value_active

### Recommended Fix Order:
1. **P0:** Catch IntegrityError for unique constraint violations in all repository `add()` methods
2. **P1:** Fix ORM cascade contradictions (Category children, Attribute values) → `cascade="save-update, merge"`
3. **P1:** Add `get_for_update()` to all delete handlers
4. **P1:** Set `STOREFRONT_CACHE_TTL = 3600` as safety net
5. **P1:** Move post-commit DB queries inside UoW blocks
6. **P1:** Remove `variant_attributes`/`variant_hash` from SKU._UPDATABLE_FIELDS
7. **P1:** Add `__setattr__` guard to AttributeGroup
8. **P1:** Add `ProductDeletedEvent` and emit from `Product.soft_delete()`
9. **P1:** Add AttributeGroupNotFoundError + validate group_id in attribute handlers
10. **P1:** Add check_name_exists for Brand or remove unique index
11. **P2:** Add Brand.name validation, Category name_i18n validation, sort_order >= 0
12. **P2:** Add missing domain events (Brand/Category create/update)
13. **P2:** Fix Cache-Control: public on authenticated /form-attributes endpoint
14. **P2:** Add intra-batch duplicate guard in bulk_assign_product_attributes
15. **P2:** Batch check_sku_code_exists in generate_sku_matrix
16. **P1:** Start test coverage: Product FSM, SKU uniqueness, delete guards, optimistic locking
