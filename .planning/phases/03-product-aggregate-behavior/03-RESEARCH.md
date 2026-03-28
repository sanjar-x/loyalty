# Phase 3: Product Aggregate Behavior - Research

**Researched:** 2026-03-28
**Domain:** Product aggregate behavioral invariants testing (Python/attrs/pytest)
**Confidence:** HIGH

## Summary

Phase 3 proves the Product aggregate's complex behavioral invariants through pure unit tests. The Product aggregate (lines 1662-2221 in `entities.py`) is the most complex entity in the catalog domain -- it owns ProductVariant child entities (which own SKUs), enforces a 5-state FSM with readiness checks, computes variant hashes for SKU uniqueness, cascades soft-delete through a 3-level hierarchy, and emits 8 distinct domain events at lifecycle points. All of these behaviors are implemented in-memory and can be tested as pure synchronous unit tests.

The codebase already provides all necessary infrastructure: ProductBuilder, SKUBuilder, and ProductVariantBuilder from Phase 1, the AggregateRoot mixin with `domain_events`/`add_domain_event()`/`clear_domain_events()`, and an established test pattern from the identity module (class-per-behavior, descriptive methods, builder-based setup). The Product aggregate's `_ALLOWED_TRANSITIONS` dict fully defines the FSM, `compute_variant_hash()` uses SHA-256 with sorted attributes, and soft_delete cascades through the `variants` property with idempotent no-op on already-deleted entities.

A notable gap: the CONTEXT.md D-04 identifies that no `restore()` method exists to reverse soft-delete cascades. The success criteria mention "restoring reverses the cascade" but the entities have no such method. The planner must decide whether to implement `restore()` or flag this as out of scope.

**Primary recommendation:** Create a single test file `test_product_aggregate.py` with 5-6 test classes grouped by behavior domain (FSM, variant hash, soft-delete, variant/SKU management, domain events, attribute governance surface). Use ProductBuilder + SKUBuilder for tree construction. All tests are pure sync -- no async, no database.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Phase 3 tests only what the domain entity enforces -- `ProductAttributeValue.create()` shape and basic construction. Template governance chain validation testing belongs in Phase 5.
- **D-02:** DOM-06 requirement traceability: Phase 3 covers the entity-side surface (PAV exists, has correct fields); Phase 5 covers the handler-side validation.
- **D-03:** Test only the existing `soft_delete()` cascade behavior: Product.soft_delete() -> sets deleted_at on all active Variants -> each Variant cascades to its active SKUs. Verify idempotency.
- **D-04:** No `restore()` method exists. Flag this as a gap for the planner.
- **D-05:** Test that `soft_delete()` on a PUBLISHED product raises `CannotDeletePublishedProductError`.
- **D-06:** Test ALL valid FSM paths: DRAFT->ENRICHING, ENRICHING->DRAFT, ENRICHING->READY_FOR_REVIEW, READY_FOR_REVIEW->ENRICHING, READY_FOR_REVIEW->PUBLISHED, PUBLISHED->ARCHIVED, ARCHIVED->DRAFT.
- **D-07:** Test ALL invalid transitions raise `InvalidStatusTransitionError` -- combinatorial.
- **D-08:** Test readiness checks: READY_FOR_REVIEW and PUBLISHED require at least one active SKU. PUBLISHED additionally requires at least one priced SKU.
- **D-09:** Test `published_at` set only on first PUBLISHED transition and retained through subsequent cycles.
- **D-10:** Test `__setattr__` guard: direct `product.status = X` raises `AttributeError`.
- **D-11:** Test `Product.add_sku()` rejects duplicate variant attribute combinations across ALL variants via `DuplicateVariantCombinationError`.
- **D-12:** Test `compute_variant_hash()` determinism: same attributes in different order produce same hash. Different variant_ids with empty attributes produce different hashes.
- **D-13:** Test that soft-deleted SKUs do NOT participate in uniqueness checks.
- **D-14:** Verify event type, aggregate_id, and key payload fields for every emitted event.
- **D-15:** Events to test: ProductCreatedEvent, ProductUpdatedEvent, ProductDeletedEvent, ProductStatusChangedEvent, VariantAddedEvent, VariantDeletedEvent, SKUAddedEvent, SKUDeletedEvent.
- **D-16:** Test event accumulation and `clear_domain_events()`.
- **D-17:** Test `remove_variant()` raises `LastVariantRemovalError` for the only active variant.
- **D-18:** Test `find_variant()` and `find_sku()` return None for soft-deleted entities.
- **D-19:** Tests go in `backend/tests/unit/modules/catalog/domain/test_product_aggregate.py`.
- **D-20:** Use Phase 1 builders. Pure unit tests -- no database, no async.

### Claude's Discretion
- Exact test method grouping within the aggregate test file (by behavior vs by method)
- Number of invalid FSM transition combinations to test (full matrix vs representative sample)
- Whether to test edge cases like add_sku to a soft-deleted variant
- Helper function design for building Product -> Variant -> SKU trees in tests

### Deferred Ideas (OUT OF SCOPE)
- **restore() method:** Product/Variant/SKU lack a restore() method to reverse soft-delete cascade. Planner to decide based on codebase research.
- **Optimistic locking version_id_col:** Inspection deferred to Phase 7 planning.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DOM-02 | Unit tests for Product FSM transitions -- all valid paths and all invalid paths | FSM table is `Product._ALLOWED_TRANSITIONS` (5 states, 7 valid transitions). `transition_status()` validates against this table, checks readiness for READY_FOR_REVIEW/PUBLISHED, sets `published_at` on first PUBLISHED. Code at lines 1943-1998. |
| DOM-03 | Unit tests for variant hash uniqueness enforcement and collision detection | `Product.compute_variant_hash()` uses SHA-256 with variant_id prefix and sorted attribute pairs. `Product.add_sku()` checks uniqueness across ALL variants. Code at lines 2086-2155, 2197-2221. |
| DOM-04 | Unit tests for soft-delete cascade behavior across Product->Variant->SKU hierarchy | `Product.soft_delete()` cascades to variants (line 1910-1941), `ProductVariant.soft_delete()` cascades to SKUs (line 1548-1558), `SKU.soft_delete()` is leaf-level (line 1322-1334). All idempotent. Published products cannot be deleted. |
| DOM-06 | Unit tests for attribute template governance chain | Per D-01/D-02, Phase 3 only tests `ProductAttributeValue.create()` shape (lines 1212-1258). Full governance chain testing deferred to Phase 5 command handler tests. |
| DOM-07 | Unit tests for domain event emission -- correct events emitted at correct lifecycle points | 8 Product-related events defined in `events.py`. Product emits events from: `create()`, `update()`, `soft_delete()`, `transition_status()`, `add_variant()`, `remove_variant()`, `add_sku()`, `remove_sku()`. AggregateRoot mixin at `shared/interfaces/entities.py`. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | 9.0.2 | Test runner | Already installed and configured in `backend/pyproject.toml` |
| attrs | 25.4.0+ | Domain entity definitions | All entities use `@dataclass` / `@frozen` from attrs |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest-randomly | 4.0.1 | Randomize test order | Already installed; catches hidden order dependencies |
| pytest-timeout | 2.4.0 | Per-test timeout (30s) | Already configured; prevents hung tests |

**Installation:**
No new packages needed. All dependencies are already installed from Phase 1.

## Architecture Patterns

### Recommended Project Structure
```
backend/tests/unit/modules/catalog/domain/
  __init__.py                             # existing (empty marker -- may need creating)
  test_category_effective_family.py       # existing (9 tests, 1 known failure)
  test_product_aggregate.py              # NEW -- all Phase 3 tests
```

### Pattern 1: Test Class Per Behavior Domain
**What:** Group tests by behavior, not by method. Each class covers one aggregate behavioral invariant.
**When to use:** For the aggregate test file where multiple behaviors intersect on the same entity.
**Example:**
```python
# Source: Pattern derived from identity module test_entities.py + CONTEXT.md decisions
import uuid
import pytest

from tests.factories.product_builder import ProductBuilder
from tests.factories.sku_builder import SKUBuilder
from src.modules.catalog.domain.entities import Product, ProductAttributeValue
from src.modules.catalog.domain.value_objects import ProductStatus, Money
from src.modules.catalog.domain.exceptions import (
    InvalidStatusTransitionError,
    ProductNotReadyError,
    DuplicateVariantCombinationError,
    CannotDeletePublishedProductError,
    VariantNotFoundError,
    LastVariantRemovalError,
    SKUNotFoundError,
)
from src.modules.catalog.domain.events import (
    ProductCreatedEvent,
    ProductUpdatedEvent,
    ProductDeletedEvent,
    ProductStatusChangedEvent,
    VariantAddedEvent,
    VariantDeletedEvent,
    SKUAddedEvent,
    SKUDeletedEvent,
)


class TestProductFSM:
    """Product status finite state machine transitions."""

    def test_draft_to_enriching(self):
        product = ProductBuilder().build()
        # Need an active SKU for some transitions but not DRAFT->ENRICHING
        product.transition_status(ProductStatus.ENRICHING)
        assert product.status == ProductStatus.ENRICHING


class TestVariantHashUniqueness:
    """Variant attribute combination collision detection."""

    def test_duplicate_combination_rejected(self):
        product = ProductBuilder().build()
        variant = product.variants[0]
        attr_id, val_id = uuid.uuid4(), uuid.uuid4()
        product.add_sku(variant.id, sku_code="SKU-1",
                       variant_attributes=[(attr_id, val_id)])
        with pytest.raises(DuplicateVariantCombinationError):
            product.add_sku(variant.id, sku_code="SKU-2",
                           variant_attributes=[(attr_id, val_id)])
```

### Pattern 2: Helper Function for Product-Variant-SKU Trees
**What:** A module-level helper that builds a complete Product with a priced SKU, ready for FSM transitions requiring readiness.
**When to use:** Whenever tests need a product that can transition to READY_FOR_REVIEW or PUBLISHED.
**Example:**
```python
def _product_with_priced_sku() -> Product:
    """Build a product with one variant and one priced active SKU."""
    product = ProductBuilder().build()
    variant = product.variants[0]
    product.add_sku(
        variant.id,
        sku_code="SKU-TEST",
        price=Money(amount=10000, currency="RUB"),
    )
    product.clear_domain_events()  # Reset events from setup
    return product
```

### Pattern 3: Combinatorial FSM Invalid Transition Matrix
**What:** Use a parameterized approach to test all invalid FSM transitions.
**When to use:** For D-07 (test all invalid transitions).
**Example:**
```python
# All 5 states
ALL_STATUSES = list(ProductStatus)

# Valid transitions from the source code
VALID_TRANSITIONS = {
    ProductStatus.DRAFT: {ProductStatus.ENRICHING},
    ProductStatus.ENRICHING: {ProductStatus.DRAFT, ProductStatus.READY_FOR_REVIEW},
    ProductStatus.READY_FOR_REVIEW: {ProductStatus.ENRICHING, ProductStatus.PUBLISHED},
    ProductStatus.PUBLISHED: {ProductStatus.ARCHIVED},
    ProductStatus.ARCHIVED: {ProductStatus.DRAFT},
}

INVALID_TRANSITIONS = [
    (src, tgt)
    for src in ALL_STATUSES
    for tgt in ALL_STATUSES
    if tgt not in VALID_TRANSITIONS.get(src, set()) and src != tgt
]

class TestProductFSMInvalid:
    @pytest.mark.parametrize("src_status,tgt_status", INVALID_TRANSITIONS)
    def test_invalid_transition_raises(self, src_status, tgt_status):
        # Build product and advance to src_status via valid path
        ...
```

### Anti-Patterns to Avoid
- **Testing internal state directly instead of behavior:** Do not inspect `product._variants` list directly; use `product.variants` property and `product.find_variant()`.
- **Not clearing events between setup and assertion:** Always call `product.clear_domain_events()` after builder setup if testing event emission from a subsequent operation.
- **Constructing SKU directly instead of via Product.add_sku():** SKU objects should only be created through the aggregate's `add_sku()` method; direct `SKU(...)` construction bypasses hash computation and uniqueness checks.
- **Forgetting that Product.create() auto-creates one default variant and emits ProductCreatedEvent:** The builder calls `Product.create()`, which always yields a product with 1 variant and 1 event already accumulated.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Product construction | Manual `Product(...)` calls | `ProductBuilder().build()` | Product.create() auto-creates variant, emits event, validates slug/i18n |
| SKU construction | Manual `SKU(...)` calls | `SKUBuilder().for_product(p).build()` or `product.add_sku()` | Hash computation and cross-variant uniqueness checks only run through `add_sku()` |
| Variant construction | Direct `ProductVariant(...)` | `product.add_variant(...)` | Proper variant is attached to aggregate and VariantAddedEvent is emitted |
| FSM traversal to target state | Setting `product.status` directly | Chain of `transition_status()` calls with required setup (SKUs for readiness) | Guard prevents direct assignment; FSM rules require valid path + readiness |

**Key insight:** The Product aggregate enforces all invariants through its public API methods. Bypassing them (e.g., `object.__setattr__`) in tests would not test actual behavior.

## Common Pitfalls

### Pitfall 1: FSM Readiness Requirements Block Transitions
**What goes wrong:** Tests attempting ENRICHING -> READY_FOR_REVIEW or READY_FOR_REVIEW -> PUBLISHED fail with `ProductNotReadyError` because the product has no active SKUs (or no priced SKUs for PUBLISHED).
**Why it happens:** Product.create() creates a product with one variant but ZERO SKUs. Readiness checks in `transition_status()` require at least one active non-deleted SKU.
**How to avoid:** Always add at least one active SKU (via `product.add_sku()`) before transitioning to READY_FOR_REVIEW. For PUBLISHED, the SKU must also have a non-None price.
**Warning signs:** `ProductNotReadyError` in tests that seem like they should pass.

### Pitfall 2: Event Accumulation From Builder Setup
**What goes wrong:** Asserting "exactly 1 event emitted" after an operation, but finding 2+ events because `Product.create()` emitted `ProductCreatedEvent` and `add_sku()` emitted `SKUAddedEvent` during setup.
**Why it happens:** ProductBuilder calls Product.create() which emits ProductCreatedEvent. Further setup (add_sku, add_variant) emits more events.
**How to avoid:** Call `product.clear_domain_events()` after all setup and before the action being tested.
**Warning signs:** `assert len(events) == 1` failing with `len == 3`.

### Pitfall 3: __setattr__ Guard Requires __initialized Flag
**What goes wrong:** Expecting `product.status = ...` to always raise, but it doesn't during construction.
**Why it happens:** The guard checks `getattr(self, "_Product__initialized", False)` which is only set to True in `__attrs_post_init__()`. During attrs' generated `__init__()`, the flag is False.
**How to avoid:** Only test the guard on fully constructed Product instances (after `create()` or builder `build()`). The guard is intentionally inactive during construction.
**Warning signs:** Guard test passes but only because the product was freshly constructed.

### Pitfall 4: variant_hash Includes variant_id
**What goes wrong:** Tests expect two SKUs with identical attributes on different variants to collide, but they don't.
**Why it happens:** `compute_variant_hash()` prepends `str(variant_id):` to the hash payload. Different variants with the same attribute set produce different hashes. This is intentional -- it allows each variant to independently have its own "no attributes" SKU.
**How to avoid:** Test hash collisions within the same variant. Cross-variant collision only happens if explicitly checking the same variant_id + attributes combination.
**Warning signs:** `DuplicateVariantCombinationError` not raised when expected across variants.

### Pitfall 5: Soft-Delete Idempotency Hides Bugs
**What goes wrong:** Calling `soft_delete()` on an already-deleted entity silently returns (no-op), making it hard to detect double-delete logic errors.
**Why it happens:** All three levels (Product, Variant, SKU) check `if self.deleted_at is not None: return` at the top of `soft_delete()`.
**How to avoid:** When testing cascade, verify the exact count of entities with non-None `deleted_at` rather than just calling soft_delete and checking one entity.
**Warning signs:** Test passes but doesn't actually verify the cascade happened.

### Pitfall 6: FSM Path Building for Advanced States
**What goes wrong:** Tests need a product in PUBLISHED or ARCHIVED state but can't directly set it -- must traverse the full FSM path.
**Why it happens:** The `__setattr__` guard prevents `product.status = ProductStatus.PUBLISHED`. The only way is `transition_status()` which requires valid path + readiness.
**How to avoid:** Create a helper function that builds a product and walks it through the FSM to the desired state. For PUBLISHED: DRAFT -> ENRICHING -> READY_FOR_REVIEW -> PUBLISHED (with SKU setup between steps). For ARCHIVED: add PUBLISHED -> ARCHIVED.
**Warning signs:** Tests are verbose with repeated FSM traversal code.

## Code Examples

### Building a Product Ready for Any FSM State
```python
# Verified from entities.py source code
from tests.factories.product_builder import ProductBuilder
from src.modules.catalog.domain.value_objects import Money, ProductStatus


def _advance_to(product, target: ProductStatus) -> None:
    """Walk the product through the FSM to the target state.

    Adds a priced SKU if needed for readiness checks.
    Clears events after reaching target.
    """
    paths = {
        ProductStatus.DRAFT: [],
        ProductStatus.ENRICHING: [ProductStatus.ENRICHING],
        ProductStatus.READY_FOR_REVIEW: [
            ProductStatus.ENRICHING,
            ProductStatus.READY_FOR_REVIEW,
        ],
        ProductStatus.PUBLISHED: [
            ProductStatus.ENRICHING,
            ProductStatus.READY_FOR_REVIEW,
            ProductStatus.PUBLISHED,
        ],
        ProductStatus.ARCHIVED: [
            ProductStatus.ENRICHING,
            ProductStatus.READY_FOR_REVIEW,
            ProductStatus.PUBLISHED,
            ProductStatus.ARCHIVED,
        ],
    }
    # Ensure SKU exists for readiness transitions
    if target in (
        ProductStatus.READY_FOR_REVIEW,
        ProductStatus.PUBLISHED,
        ProductStatus.ARCHIVED,
    ):
        variant = product.variants[0]
        if not any(s.deleted_at is None for s in variant.skus):
            product.add_sku(
                variant.id,
                sku_code="SKU-SETUP",
                price=Money(amount=10000, currency="RUB"),
            )
    for step in paths[target]:
        product.transition_status(step)
    product.clear_domain_events()
```

### Testing Event Emission Pattern
```python
# Source: Established pattern from identity module test_entities.py
class TestProductDomainEvents:
    def test_create_emits_product_created_event(self):
        product = ProductBuilder().build()
        events = product.domain_events
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, ProductCreatedEvent)
        assert event.product_id == product.id
        assert event.slug == product.slug
        assert event.aggregate_id == str(product.id)

    def test_transition_status_emits_status_changed(self):
        product = ProductBuilder().build()
        product.clear_domain_events()
        product.transition_status(ProductStatus.ENRICHING)
        events = product.domain_events
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, ProductStatusChangedEvent)
        assert event.product_id == product.id
        assert event.old_status == "draft"
        assert event.new_status == "enriching"
```

### Testing Variant Hash Determinism
```python
# Source: Product.compute_variant_hash() at entities.py:2197-2221
import uuid

class TestVariantHashUniqueness:
    def test_hash_deterministic_regardless_of_order(self):
        variant_id = uuid.uuid4()
        attr_a, val_a = uuid.uuid4(), uuid.uuid4()
        attr_b, val_b = uuid.uuid4(), uuid.uuid4()

        hash_ab = Product.compute_variant_hash(
            variant_id, [(attr_a, val_a), (attr_b, val_b)]
        )
        hash_ba = Product.compute_variant_hash(
            variant_id, [(attr_b, val_b), (attr_a, val_a)]
        )
        assert hash_ab == hash_ba

    def test_different_variants_empty_attrs_different_hash(self):
        v1, v2 = uuid.uuid4(), uuid.uuid4()
        assert Product.compute_variant_hash(v1, []) != Product.compute_variant_hash(v2, [])
```

### Testing Soft-Delete Cascade
```python
# Source: Product.soft_delete() at entities.py:1910-1941
class TestSoftDeleteCascade:
    def test_product_soft_delete_cascades_to_variants_and_skus(self):
        product = ProductBuilder().build()
        variant = product.variants[0]
        product.add_sku(variant.id, sku_code="SKU-1")
        product.clear_domain_events()

        product.soft_delete()

        assert product.deleted_at is not None
        assert product.variants[0].deleted_at is not None
        assert product.variants[0].skus[0].deleted_at is not None
```

## Detailed Behavior Map

This section maps every testable behavior from the source code to help the planner create precise tasks.

### FSM Behavior (Product.transition_status, lines 1943-1998)

| From State | To State | Valid? | Readiness Check | Notes |
|------------|----------|--------|-----------------|-------|
| DRAFT | ENRICHING | Yes | None | Simplest transition |
| ENRICHING | DRAFT | Yes | None | Rollback path |
| ENRICHING | READY_FOR_REVIEW | Yes | >= 1 active SKU | `ProductNotReadyError` if no SKUs |
| READY_FOR_REVIEW | ENRICHING | Yes | None | Send back for more work |
| READY_FOR_REVIEW | PUBLISHED | Yes | >= 1 active SKU with price | `ProductNotReadyError` if no priced SKU |
| PUBLISHED | ARCHIVED | Yes | None | Take off sale |
| ARCHIVED | DRAFT | Yes | None | Restart lifecycle |
| Any -> self | Invalid | - | - | Same-state transitions are implicitly invalid |
| DRAFT -> any except ENRICHING | Invalid | - | - | `InvalidStatusTransitionError` |
| PUBLISHED -> any except ARCHIVED | Invalid | - | - | Cannot go back from PUBLISHED |

**published_at behavior:** Set to `datetime.now(UTC)` only when `new_status == PUBLISHED and self.published_at is None`. Once set, never cleared -- survives PUBLISHED -> ARCHIVED -> DRAFT -> ... -> PUBLISHED cycle.

### Soft-Delete Cascade (3 levels)

| Level | Method | Guards | Cascade Target | Event |
|-------|--------|--------|----------------|-------|
| Product | `Product.soft_delete()` | Rejects PUBLISHED status; idempotent if already deleted | All active variants | `ProductDeletedEvent` |
| Variant | `ProductVariant.soft_delete()` | Idempotent if already deleted | All active SKUs in variant | None (no events from variant itself) |
| SKU | `SKU.soft_delete()` | Idempotent if already deleted | None (leaf) | None (no events from SKU itself) |

### Variant/SKU Management Methods

| Method | Guards | Events | Lines |
|--------|--------|--------|-------|
| `add_variant()` | None (always succeeds if i18n valid) | `VariantAddedEvent` | 2004-2040 |
| `remove_variant()` | `VariantNotFoundError` if not found/deleted; `LastVariantRemovalError` if only active variant | `VariantDeletedEvent` | 2056-2080 |
| `add_sku()` | `VariantNotFoundError` if variant not found; `DuplicateVariantCombinationError` if hash collision | `SKUAddedEvent` | 2086-2155 |
| `remove_sku()` | `SKUNotFoundError` if not found/deleted | `SKUDeletedEvent` | 2172-2195 |
| `find_variant()` | Returns None for non-existent or soft-deleted | None | 2042-2054 |
| `find_sku()` | Returns None for non-existent or soft-deleted | None | 2157-2170 |

### ProductAttributeValue.create() (DOM-06 entity-side surface)

Simple 4-field dataclass with factory method. No validation beyond field types. Lines 1212-1258.

## restore() Gap Analysis

**Current state:** No `restore()` method exists on Product, ProductVariant, or SKU. The success criteria state "restoring reverses the cascade" but this behavior is not implemented.

**Options for the planner:**
1. **Implement restore() as part of Phase 3** -- Add `Product.restore()` that clears `deleted_at` on the product and all its variants/SKUs. This is ~15 lines of code per entity. Also requires deciding: should restore restore ALL variants/SKUs or only those that were cascade-deleted (not independently deleted before the product was deleted)?
2. **Defer restore() and update success criteria** -- Remove the restore mention from success criteria. Simpler, but the success criteria came from the requirement spec.

**Recommendation:** Implement a simple `restore()` method that sets `deleted_at = None` and `updated_at = now` on the product, then cascades to all variants (which cascade to their SKUs). Emit a `ProductRestoredEvent` (or skip events for simplicity). This aligns with the success criteria and is a small addition. Note: a `ProductRestoredEvent` does not currently exist in `events.py`, so either create one or skip event emission on restore.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | `backend/pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `cd backend && uv run pytest tests/unit/modules/catalog/domain/test_product_aggregate.py -v --tb=short` |
| Full suite command | `cd backend && uv run pytest tests/unit/ -v --tb=short` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DOM-02 | All valid FSM transitions succeed | unit | `uv run pytest tests/unit/modules/catalog/domain/test_product_aggregate.py::TestProductFSMValid -x` | Wave 0 |
| DOM-02 | All invalid FSM transitions raise | unit | `uv run pytest tests/unit/modules/catalog/domain/test_product_aggregate.py::TestProductFSMInvalid -x` | Wave 0 |
| DOM-02 | Readiness checks (READY_FOR_REVIEW, PUBLISHED) | unit | `uv run pytest tests/unit/modules/catalog/domain/test_product_aggregate.py::TestProductFSMReadiness -x` | Wave 0 |
| DOM-02 | published_at behavior | unit | `uv run pytest tests/unit/modules/catalog/domain/test_product_aggregate.py -k published_at -x` | Wave 0 |
| DOM-02 | __setattr__ guard on status | unit | `uv run pytest tests/unit/modules/catalog/domain/test_product_aggregate.py -k setattr_guard -x` | Wave 0 |
| DOM-03 | Hash determinism and collision detection | unit | `uv run pytest tests/unit/modules/catalog/domain/test_product_aggregate.py::TestVariantHashUniqueness -x` | Wave 0 |
| DOM-03 | Soft-deleted SKUs excluded from uniqueness | unit | `uv run pytest tests/unit/modules/catalog/domain/test_product_aggregate.py -k soft_deleted_not_blocking -x` | Wave 0 |
| DOM-04 | Product soft-delete cascade to variants and SKUs | unit | `uv run pytest tests/unit/modules/catalog/domain/test_product_aggregate.py::TestSoftDeleteCascade -x` | Wave 0 |
| DOM-04 | Soft-delete idempotency | unit | `uv run pytest tests/unit/modules/catalog/domain/test_product_aggregate.py -k idempotent -x` | Wave 0 |
| DOM-04 | Cannot delete published product | unit | `uv run pytest tests/unit/modules/catalog/domain/test_product_aggregate.py -k cannot_delete_published -x` | Wave 0 |
| DOM-06 | ProductAttributeValue.create() shape | unit | `uv run pytest tests/unit/modules/catalog/domain/test_product_aggregate.py::TestProductAttributeValue -x` | Wave 0 |
| DOM-07 | All 8 event types emitted at correct points | unit | `uv run pytest tests/unit/modules/catalog/domain/test_product_aggregate.py::TestProductDomainEvents -x` | Wave 0 |
| DOM-07 | Event accumulation and clearing | unit | `uv run pytest tests/unit/modules/catalog/domain/test_product_aggregate.py -k event_accumulation -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && uv run pytest tests/unit/modules/catalog/domain/test_product_aggregate.py -v --tb=short`
- **Per wave merge:** `cd backend && uv run pytest tests/unit/ -v --tb=short`
- **Phase gate:** Full unit suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/unit/modules/catalog/domain/test_product_aggregate.py` -- covers DOM-02, DOM-03, DOM-04, DOM-06, DOM-07
- [ ] `backend/tests/unit/modules/catalog/domain/__init__.py` -- may need creating if not present (empty marker)

None -- existing test infrastructure (pytest, builders, conftest) covers all framework needs. No new fixtures required since these are pure unit tests.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Stdlib dataclasses for entities | attrs `@dataclass` / `@frozen` | Project inception | Use `from attr import dataclass` not `from dataclasses import dataclass` |
| UUID v4 for all IDs | UUID v7 preferred (Python 3.14+) | Python 3.14 | `_generate_id()` uses uuid7 when available |
| Manual event collection | AggregateRoot mixin | Project inception | All events go through `add_domain_event()` |

## Open Questions

1. **restore() implementation scope**
   - What we know: No restore() exists on any entity. Success criteria mention it.
   - What's unclear: Whether restore should reverse ALL soft-deletes or only cascade-triggered ones.
   - Recommendation: Planner decides -- either implement simple restore (clear all deleted_at) or revise success criteria. If implementing, skip event emission since no ProductRestoredEvent exists.

2. **Number of invalid FSM combinations to test**
   - What we know: Full matrix is 5 states x 5 states = 25 combinations minus 7 valid minus 5 self-transitions = 13 invalid combinations.
   - What's unclear: Whether full matrix is desired or representative sample sufficient.
   - Recommendation: Full matrix via `@pytest.mark.parametrize`. 13 test cases is small enough to be exhaustive. Requires helper to advance product to each source state.

## Sources

### Primary (HIGH confidence)
- `backend/src/modules/catalog/domain/entities.py` lines 1662-2221 -- Product aggregate root with full FSM, variant/SKU management, soft-delete, hash computation
- `backend/src/modules/catalog/domain/events.py` -- All 8 Product/Variant/SKU events with field definitions
- `backend/src/modules/catalog/domain/exceptions.py` -- All aggregate exceptions with constructor signatures
- `backend/src/modules/catalog/domain/value_objects.py` -- ProductStatus enum (FSM states), Money value object
- `backend/src/shared/interfaces/entities.py` -- AggregateRoot mixin with domain event infrastructure
- `backend/tests/factories/product_builder.py` -- ProductBuilder with sensible defaults
- `backend/tests/factories/sku_builder.py` -- SKUBuilder that works through Product.add_sku()
- `backend/tests/factories/variant_builder.py` -- ProductVariantBuilder via create()
- `backend/tests/unit/modules/identity/domain/test_entities.py` -- Established test pattern for domain events

### Secondary (MEDIUM confidence)
- `backend/tests/unit/modules/catalog/domain/test_category_effective_family.py` -- Existing catalog domain test demonstrating style (9 tests, 1 known failure)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries already installed and verified working
- Architecture: HIGH - All source code read directly, patterns verified against actual implementation
- Pitfalls: HIGH - All pitfalls derived from actual code analysis (e.g., readiness checks, event accumulation, hash behavior)

**Research date:** 2026-03-28
**Valid until:** 2026-04-28 (stable domain code, unlikely to change during test-writing phase)
