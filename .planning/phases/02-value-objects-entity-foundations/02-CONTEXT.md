# Phase 2: Value Objects & Entity Foundations - Context

**Gathered:** 2026-03-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Prove every entity factory method, update method, and value object is correct through pure unit tests with zero infrastructure dependencies. This phase writes test cases — it does NOT build infrastructure (Phase 1 already delivered builders, FakeUoW, and hypothesis strategies).

</domain>

<decisions>
## Implementation Decisions

### Test File Structure
- **D-01:** One test file per entity, consistent with Phase 1 D-12 (class-per-entity). Files: `test_brand.py`, `test_category.py`, `test_product.py`, `test_variant.py`, `test_sku.py`, `test_attribute.py`, `test_attribute_template.py`, `test_attribute_group.py`, `test_value_objects.py`.
- **D-02:** All files under `backend/tests/unit/modules/catalog/domain/` mirroring the source structure.

### Coverage Depth
- **D-03:** Focus on business-critical validation paths first — factory methods, state transitions, and invariant enforcement. Exhaustive edge cases can be added later.
- **D-04:** Priority order for test coverage: (1) product creation, (2) variant/SKU generation, (3) EAV attribute assignment, (4) price management, (5) status transitions.
- **D-05:** The 2,220-line entities.py is too large to exhaustively test in one phase. Cover the critical business rules, not every possible invalid input.

### Test Patterns (from Phase 1)
- **D-06:** Use Phase 1 builders (BrandBuilder, ProductBuilder, etc.) for test data construction.
- **D-07:** Class-per-entity organization: TestBrand, TestProduct, TestSKU, etc. with descriptive test methods.
- **D-08:** Pure unit tests only — no database, no async, no FakeUoW. Domain entities are sync.

### Claude's Discretion
- Exact test method names and grouping within each class
- How many invalid-input test cases per factory method
- Whether to test private helper methods or only public API
- Value object edge case selection (which Unicode, which boundary values)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Domain entities (source of truth for what to test)
- `backend/src/modules/catalog/domain/entities.py` — All 9+ entity/aggregate classes, factory methods, update methods, validation logic (2,220 lines)
- `backend/src/modules/catalog/domain/value_objects.py` — Money, BehaviorFlags, enums, SLUG_RE, REQUIRED_LOCALES, constants
- `backend/src/modules/catalog/domain/exceptions.py` — Domain exceptions raised by validation

### Test infrastructure (built in Phase 1)
- `backend/tests/factories/brand_builder.py` — BrandBuilder pattern to follow
- `backend/tests/factories/product_builder.py` — ProductBuilder for test data
- `backend/tests/factories/strategies/primitives.py` — Hypothesis strategies for value objects
- `backend/tests/factories/strategies/entity_strategies.py` — Entity strategies

### Existing test patterns
- `backend/tests/unit/modules/identity/domain/test_entities.py` — TestIdentity class pattern to follow
- `backend/tests/unit/modules/catalog/domain/` — May have existing tests to build on

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- All 8 entity builders from Phase 1 — use for constructing test data
- Hypothesis strategies (primitives, entities) — use for property-based tests where appropriate
- Existing TestIdentity pattern in identity module — model for catalog entity tests

### Established Patterns
- Entity factory methods: `Entity.create(...)` with validation in attrs `__attrs_post_init__`
- Update methods: `entity.update(...)` with guarded fields and validation
- Domain events: emitted via `self.add_domain_event(Event(...))` during create/update
- Product auto-creates one default variant on `Product.create()`

### Integration Points
- New test files go under `backend/tests/unit/modules/catalog/domain/`
- Tests import from `src.modules.catalog.domain.entities`
- Tests use builders from `tests.factories.*_builder`

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. User wants business-critical paths first, exhaustive edge cases later.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 02-value-objects-entity-foundations*
*Context gathered: 2026-03-28*
