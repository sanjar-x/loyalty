# Phase 3: Product Aggregate Behavior - Context

**Gathered:** 2026-03-28 (auto mode)
**Status:** Ready for planning

<domain>
## Phase Boundary

Prove the Product aggregate's complex behavioral invariants are correct through pure unit tests: FSM state transitions, variant hash uniqueness enforcement, soft-delete cascading through Product→Variant→SKU hierarchy, attribute governance chain validation scope, and domain event emission at correct lifecycle points. This phase tests aggregate-level *behavior* — Phase 2 already covered individual entity factory/update methods and value objects.

</domain>

<decisions>
## Implementation Decisions

### Attribute Governance Scope (DOM-06)
- **D-01:** Phase 3 tests only what the domain entity enforces — `ProductAttributeValue.create()` shape and basic construction. The template governance chain (Category → effective template → bindings → attribute assignment validation) is enforced at the command handler level, not in domain entities, so governance validation testing belongs in Phase 5 (Product & Variant Command Handlers).
- **D-02:** DOM-06 requirement traceability: Phase 3 covers the *entity-side* surface (PAV exists, has correct fields); Phase 5 covers the *handler-side* validation (template lookup, binding check, rejection of unbound attributes).

### Soft-Delete Cascade Testing (DOM-04)
- **D-03:** Test only the existing `soft_delete()` cascade behavior: Product.soft_delete() → sets deleted_at on all active Variants → each Variant cascades to its active SKUs. Verify idempotency (already-deleted entities are skipped).
- **D-04:** The success criteria mentions "restoring reverses the cascade" but no `restore()` method exists on Product, ProductVariant, or SKU. Flag this as a gap for the planner — either implement a `restore()` method as part of this phase, or revise the success criteria. Planner decides based on codebase research.
- **D-05:** Test that `soft_delete()` on a PUBLISHED product raises `CannotDeletePublishedProductError` — the product must be ARCHIVED first.

### FSM Transition Testing (DOM-02)
- **D-06:** Test ALL valid FSM paths: DRAFT→ENRICHING, ENRICHING→DRAFT, ENRICHING→READY_FOR_REVIEW, READY_FOR_REVIEW→ENRICHING, READY_FOR_REVIEW→PUBLISHED, PUBLISHED→ARCHIVED, ARCHIVED→DRAFT.
- **D-07:** Test ALL invalid transitions raise `InvalidStatusTransitionError` — every state × every disallowed target (combinatorial).
- **D-08:** Test readiness checks thoroughly: transitioning to READY_FOR_REVIEW or PUBLISHED requires at least one active (non-deleted) SKU. Transitioning to PUBLISHED additionally requires at least one priced SKU. Build full Product→Variant→SKU trees using builders.
- **D-09:** Test that `published_at` is set only on first transition to PUBLISHED and not cleared on subsequent transitions (e.g., PUBLISHED→ARCHIVED→DRAFT→...→PUBLISHED should retain original `published_at`).
- **D-10:** Test the `__setattr__` guard: direct `product.status = X` raises `AttributeError`, forcing use of `transition_status()`.

### Variant Hash Uniqueness (DOM-03)
- **D-11:** Test that `Product.add_sku()` rejects duplicate variant attribute combinations across ALL variants (not just within the same variant) via `DuplicateVariantCombinationError`.
- **D-12:** Test `compute_variant_hash()` determinism: same attributes in different order produce the same hash. Different variant_ids with empty attributes produce different hashes.
- **D-13:** Test that soft-deleted SKUs do NOT participate in uniqueness checks — a deleted SKU's hash should not block a new SKU with the same combination.

### Domain Event Emission (DOM-07)
- **D-14:** Verify event type, aggregate_id, and key payload fields (product_id, old_status, new_status, variant_id, sku_id, slug) for every emitted event. Skip non-essential fields (timestamps) to avoid over-coupling.
- **D-15:** Events to test on Product aggregate: ProductCreatedEvent (on create), ProductUpdatedEvent (on update), ProductDeletedEvent (on soft_delete), ProductStatusChangedEvent (on transition_status), VariantAddedEvent (on add_variant), VariantDeletedEvent (on remove_variant), SKUAddedEvent (on add_sku), SKUDeletedEvent (on remove_sku).
- **D-16:** Test event accumulation: multiple operations on the same aggregate accumulate events in order; `clear_domain_events()` resets the list.

### Variant Management
- **D-17:** Test `remove_variant()` raises `LastVariantRemovalError` when attempting to delete the only active variant.
- **D-18:** Test `find_variant()` and `find_sku()` return None for soft-deleted entities.

### Test Organization (carried from Phases 1-2)
- **D-19:** Tests go in `backend/tests/unit/modules/catalog/domain/test_product_aggregate.py` — a dedicated file for aggregate behavior distinct from the entity-level `test_product.py` from Phase 2.
- **D-20:** Use Phase 1 builders (ProductBuilder, SKUBuilder, etc.) for test data construction. Pure unit tests — no database, no async.

### Claude's Discretion
- Exact test method grouping within the aggregate test file (by behavior vs by method)
- Number of invalid FSM transition combinations to test (full matrix vs representative sample)
- Whether to test edge cases like add_sku to a soft-deleted variant (expected to fail via find_variant returning None)
- Helper function design for building Product→Variant→SKU trees in tests

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Domain entities (source of truth)
- `backend/src/modules/catalog/domain/entities.py` — Product aggregate (line 1663+), ProductVariant (line 1406+), SKU (line 1267+), ProductAttributeValue (line 1213+). Contains FSM table, soft_delete cascade, variant hash computation, add_variant/remove_variant/add_sku/remove_sku
- `backend/src/modules/catalog/domain/events.py` — All 27 domain events. Product events: ProductCreatedEvent, ProductStatusChangedEvent, ProductUpdatedEvent, ProductDeletedEvent, VariantAddedEvent, VariantDeletedEvent, SKUAddedEvent, SKUDeletedEvent
- `backend/src/modules/catalog/domain/exceptions.py` — Domain exceptions: InvalidStatusTransitionError, DuplicateVariantCombinationError, CannotDeletePublishedProductError, VariantNotFoundError, LastVariantRemovalError, SKUNotFoundError, ProductNotReadyError
- `backend/src/modules/catalog/domain/value_objects.py` — ProductStatus enum (DRAFT, ENRICHING, READY_FOR_REVIEW, PUBLISHED, ARCHIVED), Money, BehaviorFlags

### Test infrastructure (built in Phase 1)
- `backend/tests/factories/product_builder.py` — ProductBuilder for constructing test products
- `backend/tests/factories/variant_builder.py` — VariantBuilder (if exists)
- `backend/tests/factories/sku_builder.py` — SKUBuilder (if exists)
- `backend/tests/factories/builders.py` — Base builder patterns

### Existing test patterns
- `backend/tests/unit/modules/identity/domain/test_entities.py` — TestIdentity class pattern (reference for domain event testing)
- `backend/tests/unit/modules/catalog/domain/` — Phase 2 entity tests (adjacent files)

### Shared kernel
- `backend/src/shared/interfaces/entities.py` — AggregateRoot mixin with add_domain_event/clear_domain_events/domain_events

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Phase 1 builders (ProductBuilder, SKUBuilder, etc.) — construct Product→Variant→SKU trees with sensible defaults
- AggregateRoot mixin `domain_events` property — use to assert event emission
- Existing TestIdentity pattern in identity module — model for event assertion style

### Established Patterns
- Product.create() auto-creates one default variant — tests start with a 1-variant product
- `__setattr__` guard pattern (DDD-01) on Product.status — forces use of transition_status()
- `object.__setattr__` used internally to bypass guard for FSM mutation
- Soft-delete is idempotent — calling soft_delete() on already-deleted entity is a no-op
- variant_hash includes variant_id — different variants with empty attributes get different hashes

### Integration Points
- New test file: `backend/tests/unit/modules/catalog/domain/test_product_aggregate.py`
- Imports from `src.modules.catalog.domain.entities` (Product, ProductVariant, SKU, ProductAttributeValue)
- Imports from `src.modules.catalog.domain.events` (all Product/Variant/SKU events)
- Imports from `src.modules.catalog.domain.exceptions` (all aggregate-related exceptions)
- Uses builders from `tests.factories.*_builder`

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. Auto-mode selected recommended defaults for all gray areas.

</specifics>

<deferred>
## Deferred Ideas

- **restore() method:** Product/Variant/SKU lack a restore() method to reverse soft-delete cascade. If needed, it should be implemented as part of this phase or flagged for a future phase. Planner to decide based on codebase research.
- **Optimistic locking version_id_col:** STATE.md notes this needs inspection during Phase 7 planning — not Phase 3 scope.

</deferred>

---

*Phase: 03-product-aggregate-behavior*
*Context gathered: 2026-03-28*
