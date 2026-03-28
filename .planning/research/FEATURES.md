# Feature Research: EAV Catalog Hardening

**Domain:** Testing, Validation, and Correctness for a Production-Ready EAV Catalog
**Researched:** 2026-03-28
**Confidence:** HIGH

## Feature Landscape

This is a hardening milestone, not a feature milestone. "Features" here mean testing and validation capabilities that make the existing EAV catalog production-ready. The catalog already has 46 command handlers, 22 query handlers, 11 router files, and a rich domain model. What it lacks is proof that any of it works correctly (1.1% test-to-source ratio, 44 of 46 commands untested).

### Table Stakes (Must Have or the Catalog Is Unreliable)

Features users (downstream developers, the order system) expect. Missing these means the catalog cannot be trusted as a foundation.

| Feature | Why Expected | Complexity | Notes |
|---------|-------------|------------|-------|
| Domain entity unit tests (Product aggregate) | Product is the central aggregate root -- FSM transitions, variant/SKU management, hash computation, soft-delete cascading, domain event emission all need proof of correctness | HIGH | Product.create(), transition_status(), add_variant(), remove_variant(), add_sku(), remove_sku(), find_sku(), soft_delete(), update(), compute_variant_hash() -- each with happy path + error paths. ~40-60 test cases. |
| Domain entity unit tests (Brand, Category, Attribute) | Every entity has factory methods with validation, update methods with guarded fields, and deletion guards -- all untested | MEDIUM | Brand (create, update, validate_deletable), Category (create_root, create_child, update, effective_template inheritance, max depth), Attribute (create, update, BehaviorFlags), AttributeValue (create, update), AttributeTemplate (create, update) |
| Value object unit tests (Money, BehaviorFlags, ProductStatus FSM) | Money enforces non-negative amounts, currency matching, compare_at > price invariant. BehaviorFlags validates search_weight range. ProductStatus defines the lifecycle FSM. Bugs here corrupt pricing and status across the entire catalog | MEDIUM | Money: construction, from_primitives(), comparison operators, cross-currency rejection. BehaviorFlags: weight range. ProductStatus: enum completeness. Also slug validation, i18n validation, validation_rules per data type |
| Command handler unit tests (all 46 handlers) | 44 of 46 handlers are untested. These orchestrate all write operations -- product creation, variant management, SKU matrix generation, attribute assignment, category tree management. A bug in any handler silently corrupts catalog data | HIGH | Each handler needs: happy path, FK-not-found, slug/code conflict, authorization-relevant validation, UoW commit verification, domain event emission. Mock repositories and UoW. Estimated 200-300 test cases total |
| Query handler unit/integration tests (all 22 handlers) | Query handlers bypass the domain layer and read directly from ORM. Untested queries may return incorrect read models, wrong pagination, or stale data -- directly impacting storefront display and admin UI | MEDIUM | Key queries: get_product (with variants/SKUs), list_products (pagination, filtering), get_product_completeness (template requirement matching), storefront queries (filterable, card, comparison, form attributes), get_category_tree (hierarchical ordering) |
| Integration tests for Product repository (CRUD + eager loading) | The Product repository has the most complex mapping: Product -> Variants -> SKUs -> variant_attributes, with soft-delete filtering, pessimistic locking (get_for_update_with_variants), and Data Mapper conversions. ORM-to-domain and domain-to-ORM fidelity must be verified | HIGH | Test: add product with variants and SKUs, get with eager loading, update with new SKUs, soft-delete cascading, optimistic locking (version field), variant_attributes roundtrip through JSONB/link table |
| Integration tests for Category repository (tree operations) | Category repo has unique operations: hierarchical slug propagation (update_descendants_full_slug), effective_template_id propagation via recursive CTE. These are SQL-heavy and cannot be verified with mocks | MEDIUM | Test: create tree 3 levels deep, rename parent slug (verify descendants updated), set template on parent (verify CTE propagation), delete leaf vs delete parent-with-children guard |
| Integration tests for Brand/Attribute/AttributeValue repositories | Simpler CRUD but still need: slug/code uniqueness enforcement, has_products/has_product_attribute_values deletion guards, bulk operations (get_many, check_codes_exist) | MEDIUM | Lower risk than Product but still untested. Focus on uniqueness constraint behavior and FK guard queries |
| API contract integration tests (catalog endpoints) | 11 router files expose the catalog API. Without endpoint tests, request schema validation, response shape, HTTP status codes, and RBAC enforcement are unverified. The order system will depend on these contracts | HIGH | Test each endpoint's happy path + key error cases. Verify: Pydantic input validation, correct HTTP status codes (201, 404, 409, 422), response schema shape (camelCase aliasing), RequirePermission enforcement. Use httpx AsyncClient with DI override |
| Data integrity validation (schema constraints + migrations) | EAV systems are notorious for constraint-free data. Verify that unique indexes, FK constraints, check constraints, and NOT NULL constraints actually exist in the database schema and match domain rules | MEDIUM | Inspect alembic migrations or live schema. Verify: brands(slug) unique, brands(name) unique, categories(slug, parent_id) unique, products(slug) unique, sku_attribute_values FK integrity, product_attribute_values FK integrity. Test constraint violation behavior |
| Product status FSM integration test (full lifecycle) | The FSM (DRAFT -> ENRICHING -> READY_FOR_REVIEW -> PUBLISHED -> ARCHIVED -> DRAFT) has readiness checks that span multiple aggregates (active SKUs, priced SKUs, media assets). This cross-aggregate validation can only be fully tested with integration tests | MEDIUM | Create product, add variant, add SKU with price, add media, walk through every valid transition. Verify: can't publish without active SKU, can't publish without priced SKU, can't publish without media, can't delete published product, can archive published, can revert to draft from archived |
| Domain event emission verification | 27 domain events defined. Events are emitted during entity operations and persisted to the Outbox. If events are missing or have wrong payloads, downstream consumers (future ES sync, notifications) will break silently | LOW | Test that each entity operation emits the expected event with correct fields. This is naturally covered by entity unit tests if they assert on domain_events property after each operation |
| Soft-delete correctness across the aggregate | Products, Variants, and SKUs all support soft-delete. Cascade behavior (product soft-delete -> variant soft-delete -> SKU soft-delete) must be verified. Queries must correctly filter out deleted records | MEDIUM | Unit tests: verify cascade in domain entity. Integration tests: verify repository queries exclude deleted records. Verify deleted_at timestamps are set, verify idempotent re-deletion |

### Differentiators (Competitive Advantage in Quality)

Features that elevate the catalog from "tested" to "confidently production-ready." Not strictly required for basic correctness, but significantly reduce risk.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| N+1 query detection in integration tests | EAV systems are notorious for N+1 queries due to the pivot table pattern. Detect them automatically during test runs rather than discovering them in production via slow page loads | LOW | Use SQLAlchemy event hooks or `sqlalchemy.testing.mock` to count queries per test. Flag tests that exceed expected query count. Critical for: get_product_with_variants, list_products, storefront queries |
| Property-based testing for variant hash uniqueness | The variant_hash (SHA-256 of sorted attribute pairs) is the SKU deduplication mechanism. A collision means two different attribute combinations produce the same hash, causing silent data loss. Property-based testing can explore the hash space far better than hand-written cases | MEDIUM | Use hypothesis library. Generate random attribute_id/value_id pairs, verify: (1) different inputs produce different hashes, (2) same inputs in different order produce same hash, (3) different variant_ids with same attributes produce different hashes |
| Optimistic locking (version field) concurrency tests | Products and SKUs have a `version` field for optimistic locking. Without testing, concurrent updates could silently overwrite each other. The ConcurrencyError exception exists but may never be triggered if the repository doesn't actually check versions | MEDIUM | Integration test: load product twice, update both copies, verify second save raises ConcurrencyError. Verify version is incremented on each save |
| Test data builders (Object Mother / Builder pattern) | 46 command handlers each need test data. Without builders, test files will be 80% boilerplate and 20% assertions. Builders make tests readable and maintainable | MEDIUM | Build factories for: Product (with variants, SKUs, attributes), Brand, Category (with tree), Attribute (with values), AttributeTemplate (with bindings). Use polyfactory (already in deps) or hand-rolled builders |
| API response schema snapshot tests | Lock down API response shapes so that changes to read models or Pydantic schemas are caught before they break frontend integrations | LOW | Serialize response JSON, compare against stored snapshot. Catch: accidental field removal, type changes, missing camelCase aliasing. Particularly important for storefront endpoints that the main frontend consumes |
| Completeness checker integration test | get_product_completeness compares product attributes against template requirements. This spans 4 tables (product, category, template_bindings, product_attribute_values). A bug here means the enrichment workflow shows wrong status | MEDIUM | Create template with required/recommended/optional attributes, assign some to product, verify completeness result matches expectations. Edge cases: no template on category, empty template, all attributes filled |
| Migration integrity audit | Verify that alembic migration history is linear, all migrations apply cleanly to an empty database, and the resulting schema matches the ORM models | LOW | Run alembic upgrade head on an empty testcontainer database. Use alembic check to verify no model/schema drift. This catches schema rot early |
| Bulk operation correctness tests | bulk_create_brands, bulk_create_categories, bulk_create_attributes, bulk_assign_product_attributes, generate_sku_matrix -- these batch operations have complex validation and partial-failure semantics | MEDIUM | Test: all succeed, some fail (duplicate codes), all fail. Verify atomicity (all-or-nothing within UoW). SKU matrix generation: verify cartesian product correctness, MAX_SKU_COMBINATIONS limit |
| Storefront query caching correctness | Storefront queries use Redis cache (storefront_cache_key patterns, STOREFRONT_CACHE_TTL). Cached results must be invalidated when underlying data changes | MEDIUM | Integration test: query storefront, update attribute, query again (should reflect change after cache TTL or invalidation). Verify cache keys are correctly scoped to category_id |

### Anti-Features (Things to Deliberately NOT Do During Hardening)

Things that seem productive but would derail the hardening milestone.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|--------------|-----------------|-------------|
| Refactor away from EAV pattern | "EAV is an anti-pattern, use JSONB columns instead" | EAV is a deliberate architectural choice with existing infrastructure (templates, bindings, completeness checker). Refactoring now would touch every layer and delay the order system by months | Keep EAV; harden what exists. The pattern's weaknesses are mitigated by the rich domain model and template system already built |
| Add search/filtering backend | "We need Elasticsearch for product discovery" | Search is a separate bounded context. Mixing it into the hardening milestone creates a moving target -- you can't test what's still being built | Defer to a dedicated search milestone. The storefront query handlers already exist and should be tested as-is |
| Frontend test coverage | "Zero frontend tests is a risk" | True, but this milestone is backend catalog only. Frontend testing requires different tools (Vitest, Playwright), different expertise, and different scope | Keep as a separate milestone per PROJECT.md out-of-scope |
| Performance optimization | "Fix the COUNT(*) pagination and N+1 queries" | Optimization without tests is dangerous -- you might "fix" performance while breaking correctness. Testing must come first | Test first, detect N+1s via instrumentation, then optimize in a later phase with tests as a safety net |
| Add new catalog features (reviews, ratings, wishlists) | "While we're in the catalog, let's add X" | Scope creep. Every new feature is untested code added to an already-untested module. The goal is to prove existing code works, not add more unproven code | After hardening, new features can be built with TDD because test infrastructure will exist |
| End-to-end tests through the full frontend-to-backend stack | "Real users use the UI, so test the UI" | E2E tests are slow, brittle, and the frontend is full of stubs (cart, checkout, favorites are all non-functional). E2E tests on top of stubs test nothing | Focus on API contract tests (httpx AsyncClient) which verify the backend's public interface without frontend dependencies |
| 100% code coverage target | "We should aim for complete coverage" | Coverage percentage is a vanity metric. 100% coverage with weak assertions proves nothing. The god-class entity file alone is 2,220 lines -- covering every branch there while also covering 46 handlers would take unreasonable time | Target meaningful coverage: all command handlers, all domain entity methods, critical query handlers. Prioritize by risk (product/SKU operations > attribute group reordering) |
| Automated load/stress testing | "We need to verify it handles production traffic" | The system has no users yet. Load testing without correctness testing is measuring the speed of a broken system | Defer until after correctness is established and the order system exists to generate realistic load patterns |

## Feature Dependencies

```
[Value Object Tests (Money, BehaviorFlags, etc.)]
    |
    v
[Domain Entity Unit Tests (Product, Brand, Category, etc.)]
    |
    +---> [Domain Event Emission Verification] (covered by entity tests)
    |
    v
[Test Data Builders / Factories]
    |
    +---> [Command Handler Unit Tests (46 handlers)]
    |         |
    |         +---> [Soft-Delete Correctness Tests] (covered in handler + entity tests)
    |
    +---> [Query Handler Tests (22 handlers)]
    |
    v
[Repository Integration Tests (Product, Category, Brand, Attribute)]
    |
    +---> [Optimistic Locking Tests]
    |
    +---> [N+1 Query Detection]
    |
    v
[API Contract Integration Tests (11 routers)]
    |
    +---> [API Response Snapshot Tests]
    |
    v
[Cross-Cutting Integration Tests]
    +---> [Product Status FSM Full Lifecycle]
    +---> [Completeness Checker Integration]
    +---> [Bulk Operation Correctness]
    +---> [Storefront Query Caching]

[Data Integrity Validation (schema audit)] -- independent, can run in parallel

[Migration Integrity Audit] -- independent, can run in parallel
```

### Dependency Notes

- **Domain Entity Tests before Command Handler Tests:** Command handlers delegate to domain entities. If entity methods are broken, handler tests will fail for wrong reasons. Test entities first to establish a trusted foundation.
- **Test Data Builders before Handler Tests:** Without builders, writing 200-300 handler test cases is impractical. Builders pay for themselves immediately.
- **Value Object Tests before Entity Tests:** Entities compose value objects (Money in SKU, BehaviorFlags in Attribute, ProductStatus in Product). Value object bugs cascade into entity test failures.
- **Repository Integration Tests before API Tests:** API tests implicitly depend on repositories. If the repository mapping is wrong, API tests fail with confusing errors. Test the data layer first.
- **Command Handler Tests before Cross-Cutting Tests:** Cross-cutting tests (FSM lifecycle, completeness) exercise multiple handlers in sequence. They are hard to debug if individual handlers are untested.

## MVP Definition

### Launch With (v1 -- Minimum for Production Confidence)

The absolute minimum to trust the catalog before building the order system on top of it.

- [ ] Value object unit tests (Money, BehaviorFlags, slug validation, i18n validation) -- foundation for everything else, catches pricing and data type bugs
- [ ] Product aggregate unit tests (create, FSM, add/remove variant, add/remove SKU, soft-delete, variant hash) -- the core aggregate root that everything depends on
- [ ] Brand, Category, Attribute entity unit tests -- remaining aggregates with business rules
- [ ] Test data builders for Product, Brand, Category, Attribute -- enables writing handler tests efficiently
- [ ] Command handler unit tests for all 46 handlers -- proves every write operation is correct
- [ ] Product repository integration tests (CRUD + eager loading + soft-delete) -- proves ORM mapping fidelity for the most complex aggregate
- [ ] Category repository integration tests (tree operations + template propagation) -- recursive CTE is SQL-only logic
- [ ] Entity god-class split (entities.py -> entities/ package) -- prerequisite for maintainable test files; 2,220 lines in one file makes targeted testing painful
- [ ] Data integrity validation (schema constraint audit) -- one-time verification that DB constraints match domain rules

### Add After Validation (v1.x)

Features to add once core testing is in place and bugs from v1 are fixed.

- [ ] Query handler tests for all 22 handlers -- add once command-side is proven correct
- [ ] API contract integration tests for all 11 routers -- add once repository and handler layers are tested
- [ ] Product status FSM full lifecycle integration test -- add once individual handlers are tested
- [ ] Completeness checker integration test -- add once attribute template flow is tested
- [ ] Optimistic locking concurrency tests -- add once Product repository tests pass

### Future Consideration (v2+)

Features to defer until after the hardening milestone is complete.

- [ ] Property-based testing for variant hash -- defer until basic hash tests prove the mechanism works
- [ ] N+1 query detection instrumentation -- defer until after correctness; apply during performance milestone
- [ ] API response snapshot tests -- defer until API contracts stabilize after bug fixes
- [ ] Storefront query caching correctness -- defer until caching strategy is finalized
- [ ] Bulk operation stress tests -- defer until after basic bulk operation correctness is proven
- [ ] Migration integrity audit -- low risk, run once before deployment

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|-----------|-------------------|----------|
| Product aggregate unit tests | HIGH | MEDIUM | P1 |
| Value object unit tests | HIGH | LOW | P1 |
| Brand/Category/Attribute entity tests | HIGH | MEDIUM | P1 |
| Test data builders | HIGH | MEDIUM | P1 |
| Command handler unit tests (46 handlers) | HIGH | HIGH | P1 |
| Product repository integration tests | HIGH | MEDIUM | P1 |
| Category repository integration tests | HIGH | MEDIUM | P1 |
| Entity god-class split | MEDIUM | LOW | P1 |
| Data integrity validation | HIGH | LOW | P1 |
| Query handler tests (22 handlers) | MEDIUM | MEDIUM | P2 |
| API contract integration tests | MEDIUM | HIGH | P2 |
| FSM lifecycle integration test | MEDIUM | MEDIUM | P2 |
| Completeness checker test | MEDIUM | LOW | P2 |
| Optimistic locking tests | MEDIUM | LOW | P2 |
| N+1 query detection | LOW | LOW | P3 |
| Property-based hash testing | LOW | MEDIUM | P3 |
| API snapshot tests | LOW | LOW | P3 |
| Storefront caching tests | LOW | MEDIUM | P3 |
| Migration integrity audit | LOW | LOW | P3 |

**Priority key:**
- P1: Must have for production confidence -- blocks order system
- P2: Should have, significantly reduces risk -- add when P1 is done
- P3: Nice to have, catches edge cases -- future milestone

## EAV-Specific Testing Concerns

EAV systems have unique correctness risks that traditional relational models don't. These must be explicitly addressed in the test plan.

### 1. Attribute-Value Type Mismatch
**Risk:** An attribute defined as `INTEGER` could receive a string value through the EAV pivot table because the DB stores all values as a generic reference (attribute_value_id) rather than typed columns.
**Mitigation:** The system uses dictionary attributes with pre-defined values (AttributeValue entities), not freeform values. Test that command handlers reject attribute values that don't belong to the specified attribute (attribute_value.attribute_id != command.attribute_id).

### 2. Orphaned Attribute Values
**Risk:** Deleting an attribute leaves orphaned ProductAttributeValue rows pointing to a non-existent attribute. Queries return stale or broken data.
**Mitigation:** Test deletion guards: `has_product_attribute_values()` on Attribute, `has_product_references()` on AttributeValue. Integration test: attempt to delete attribute in use, verify ConflictError.

### 3. Template-Product Consistency Drift
**Risk:** A product is created under category A (with template T1). Category A's template is later changed to T2. Product's existing attributes may no longer match the new template requirements.
**Mitigation:** Test the completeness checker's behavior when templates change after product creation. This is a known EAV consistency challenge.

### 4. Variant Hash Collision
**Risk:** Two different attribute combinations produce the same SHA-256 hash, allowing duplicate SKUs.
**Mitigation:** Unit test: verify hash determinism (same input = same output), order independence, variant_id inclusion (different variants can both have empty attributes). Property-based testing in v2.

### 5. Effective Template Inheritance Consistency
**Risk:** Category tree has template inheritance (effective_template_id). Moving a category, changing a parent's template, or deleting a template could leave effective_template_id stale across descendants.
**Mitigation:** Integration test the recursive CTE propagation in `propagate_effective_template_id()`. Test: set template on root, verify leaf inherits; change root template, verify leaf updates; remove root template, verify leaf clears.

### 6. Soft-Delete Leaks in Queries
**Risk:** A query forgets to filter `deleted_at IS NULL`, returning deleted products/variants/SKUs to the storefront or admin UI.
**Mitigation:** Integration test: create product, soft-delete it, verify it doesn't appear in list queries, get queries, or storefront queries.

## Sources

- Codebase analysis: `backend/src/modules/catalog/domain/entities.py` (2,220 lines, 9+ entity classes)
- Codebase analysis: `backend/src/modules/catalog/application/commands/` (46 command handlers)
- Codebase analysis: `backend/src/modules/catalog/application/queries/` (22 query handlers)
- Codebase analysis: `backend/tests/` (796 LOC existing catalog tests, 1.1% test-to-source ratio)
- [DDD & Testing Strategy](http://www.taimila.com/blog/ddd-and-testing-strategy/) -- aggregate as unit of testing
- [Testing Strategies in DDD](https://dev.to/ruben_alapont/testing-strategies-in-domain-driven-design-ddd-2d93) -- unit/integration/E2E layering
- [Domain-Driven Design & Unit Tests](https://www.jamesmichaelhickey.com/ddd-unit-tests/) -- Classical school for aggregate testing
- [EAV Anti-pattern Analysis](https://cedanet.com.au/antipatterns/eav.php) -- EAV constraint and integrity issues
- [EAV: A Fascinating but Dangerous Pattern](https://dev.to/giuliopanda/eav-a-fascinating-but-often-dangerous-pattern-200j) -- validation and query challenges
- [Entity-attribute-value model (Wikipedia)](https://en.wikipedia.org/wiki/Entity%E2%80%93attribute%E2%80%93value_model) -- metadata correctness criticality
- [Antipathy for EAV Data Models](https://www.sqlservercentral.com/articles/antipathy-for-entity-attribute-value-data-models) -- DRI impossibility, constraint challenges

---
*Feature research for: EAV Catalog Hardening*
*Researched: 2026-03-28*
