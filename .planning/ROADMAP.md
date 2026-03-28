# Roadmap: EAV Catalog Hardening

## Overview

This milestone proves the existing EAV Catalog module is correct and thoroughly tested before building cart, checkout, and order management on top of it. The work proceeds bottom-up through the hexagonal architecture: pure domain model tests first (zero dependencies, fastest feedback), then command handler orchestration tests (mocked repos), then repository integration tests (real PostgreSQL), then API contract tests (full HTTP stack), and finally the entity god-class structural refactoring (safe only after 400+ tests exist). Each phase builds confidence in a specific layer and unblocks testing of the layers above it.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Test Infrastructure** - Install dependencies, build factories, fake UoW, hypothesis strategies, and N+1 detection tooling
- [ ] **Phase 2: Value Objects & Entity Foundations** - Unit tests for all entity factory/update methods and all value objects
- [ ] **Phase 3: Product Aggregate Behavior** - Unit tests for FSM, variant hash, soft-delete cascade, attribute governance, and domain events
- [ ] **Phase 4: Brand, Category & Attribute Command Handlers** - Unit tests for all supporting entity command handlers
- [ ] **Phase 5: Product & Variant Command Handlers** - Unit tests for product lifecycle and variant management handlers
- [ ] **Phase 6: SKU, Media & Cross-Cutting Commands** - Unit tests for SKU/media handlers plus event emission, bulk atomicity, and error paths
- [ ] **Phase 7: Repository & Data Integrity** - Integration tests for all catalog repositories against real PostgreSQL with schema constraint audit
- [ ] **Phase 8: API Contract Validation** - Integration tests for all catalog endpoints covering HTTP contracts, authorization, lifecycle, and pagination
- [ ] **Phase 9: Entity God-Class Refactoring** - Split 2,220-line entities.py into separate files with backward-compatible re-exports

## Phase Details

### Phase 1: Test Infrastructure
**Goal**: All test tooling, factories, and utilities are in place so subsequent phases can focus purely on writing test cases
**Depends on**: Nothing (first phase)
**Requirements**: INFRA-01, INFRA-02, INFRA-03, INFRA-04, INFRA-05
**Success Criteria** (what must be TRUE):
  1. Running `pytest` with the new dependencies (hypothesis, schemathesis, respx, dirty-equals, pytest-randomly, pytest-timeout) succeeds without import errors
  2. A test can instantiate any catalog entity (Product, ProductVariant, SKU, Brand, Category, Attribute, AttributeTemplate, AttributeGroup, TemplateAttributeBinding) via a factory/builder with sensible defaults
  3. A test can execute a command handler using FakeUnitOfWork without touching the database and verify repository interactions
  4. Hypothesis can generate valid EAV domain model instances (attribute values, i18n names, slugs) and shrink failures to minimal examples
  5. A test can wrap a database session in the N+1 query detection context manager and assert exact query counts
**Plans:** 3 plans

Plans:
- [ ] 01-01-PLAN.md — Install test dependencies + build fluent entity Builders + ORM factories
- [ ] 01-02-PLAN.md — Build FakeUnitOfWork with dict-based fake catalog repositories
- [ ] 01-03-PLAN.md — Build composable Hypothesis strategies + N+1 query detection utility

### Phase 2: Value Objects & Entity Foundations
**Goal**: Every entity factory method, update method, and value object is proven correct through unit tests with zero infrastructure dependencies
**Depends on**: Phase 1
**Requirements**: DOM-01, DOM-05
**Success Criteria** (what must be TRUE):
  1. Every entity class (Brand, Category, Product, ProductVariant, SKU, Attribute, AttributeTemplate, AttributeGroup, TemplateAttributeBinding) has tests for its factory method (create/constructor) covering valid inputs and validation rejection of invalid inputs
  2. Every entity update method is tested for both successful mutation and rejection of invalid state transitions
  3. All value objects (Money, BehaviorFlags, ProductStatus, slugs, i18n names) are tested for immutability, equality, validation rules, and edge cases (zero money, empty strings, Unicode slugs)
**Plans**: TBD

Plans:
- [ ] 02-01: TBD
- [ ] 02-02: TBD

### Phase 3: Product Aggregate Behavior
**Goal**: The Product aggregate's complex behavioral invariants -- state machine, variant uniqueness, cascade deletes, attribute governance, and event emission -- are proven correct
**Depends on**: Phase 2
**Requirements**: DOM-02, DOM-03, DOM-04, DOM-06, DOM-07
**Success Criteria** (what must be TRUE):
  1. Every valid FSM transition path (draft to active, active to archived, etc.) succeeds and every invalid path (archived to draft, etc.) raises the correct domain exception
  2. Adding two variants with the same attribute-value combination is rejected (hash collision detection works)
  3. Soft-deleting a Product cascades deleted_at through all its Variants and their SKUs, and restoring reverses the cascade
  4. Assigning an attribute to a product that violates the template governance chain (wrong template, wrong level, unbound attribute) is rejected with a clear error
  5. Every domain lifecycle event (ProductCreated, StatusChanged, VariantAdded, SKUGenerated, etc.) is emitted at the correct point with correct payload
**Plans**: TBD

Plans:
- [ ] 03-01: TBD
- [ ] 03-02: TBD

### Phase 4: Brand, Category & Attribute Command Handlers
**Goal**: All command handlers for supporting entities (Brand, Category, Attribute/Template/Group) are proven to orchestrate correctly -- calling the right repositories, enforcing preconditions, and committing through UoW
**Depends on**: Phase 1 (FakeUnitOfWork), Phase 2 (entity correctness)
**Requirements**: CMD-01, CMD-02, CMD-03
**Success Criteria** (what must be TRUE):
  1. All Brand handlers (create, update, delete, bulk_create) pass happy-path tests and reject invalid inputs (duplicate slug, missing brand)
  2. All Category handlers (create, update, delete, reorder, assign_template) pass happy-path tests and reject invalid inputs (circular parent, missing category, template conflict)
  3. All Attribute handlers (create_template, update_template, delete_template, create_group, manage_bindings) pass happy-path tests and reject invalid inputs (duplicate binding, missing template)
  4. Every handler test verifies UoW.commit() is called on success and not called on validation failure
**Plans**: TBD

Plans:
- [ ] 04-01: TBD
- [ ] 04-02: TBD

### Phase 5: Product & Variant Command Handlers
**Goal**: All command handlers for the Product aggregate core (product CRUD, status changes, attribute assignment, variant management) are proven correct
**Depends on**: Phase 1 (FakeUnitOfWork), Phase 3 (aggregate behavior)
**Requirements**: CMD-04, CMD-05
**Success Criteria** (what must be TRUE):
  1. All Product handlers (create, update, delete, change_status, assign_attributes) pass happy-path tests including cross-module supplier validation
  2. All Variant handlers (add_variant, update_variant, remove_variant) pass happy-path tests and correctly reject duplicate variant hash combinations
  3. Every handler test verifies the correct domain entity method is invoked and UoW commits the result
  4. Error paths (product not found, invalid status transition, supplier inactive) return the correct exception types
**Plans**: TBD

Plans:
- [ ] 05-01: TBD
- [ ] 05-02: TBD

### Phase 6: SKU, Media & Cross-Cutting Commands
**Goal**: SKU and media handlers are tested, and cross-cutting concerns (event emission, bulk atomicity, FK/uniqueness errors) are verified across ALL command handlers
**Depends on**: Phase 4, Phase 5
**Requirements**: CMD-06, CMD-07, CMD-08, CMD-09, CMD-10
**Success Criteria** (what must be TRUE):
  1. All SKU handlers (add_sku, update_sku, remove_sku, generate_sku_matrix) pass happy-path tests including matrix generation from variant combinations
  2. All Media handlers (sync_media, reorder_media) pass happy-path tests including image backend HTTP mock interactions
  3. Every command handler that produces domain events is verified to emit the correct event type and payload (systematic audit across all 46 handlers)
  4. Bulk operations (bulk_create_brands, generate_sku_matrix) roll back completely on partial failure -- no partial state persists
  5. FK-not-found and uniqueness conflict error paths are tested across all handlers that reference related entities
**Plans**: TBD

Plans:
- [ ] 06-01: TBD
- [ ] 06-02: TBD

### Phase 7: Repository & Data Integrity
**Goal**: All catalog repository implementations are proven correct against real PostgreSQL -- Data Mapper roundtrips, schema constraints, soft-delete filtering, and ORM mapping fidelity
**Depends on**: Phase 1 (N+1 detection), Phase 3 (domain model understanding)
**Requirements**: REPO-01, REPO-02, REPO-03, REPO-04, REPO-05
**Success Criteria** (what must be TRUE):
  1. A Product with variants and SKUs can be created, read back, updated, and deleted through the repository with all fields surviving the ORM roundtrip (including Money decomposition, JSONB i18n, nested collections)
  2. Brand, Category, and Attribute repositories pass CRUD integration tests with real PostgreSQL including tree operations and slug propagation
  3. All FK, unique, and check constraints in the migration files are verified to reject invalid data at the database level (not just application level)
  4. Every repository method and query handler that reads data correctly filters out soft-deleted records (deleted_at IS NULL) with no leaks
  5. All entity fields survive a full create-read roundtrip through ORM models without data loss or type coercion errors
**Plans**: TBD

Plans:
- [ ] 07-01: TBD
- [ ] 07-02: TBD

### Phase 8: API Contract Validation
**Goal**: All catalog REST endpoints are proven to return correct HTTP status codes, response shapes, authorization enforcement, and pagination behavior through the full HTTP stack
**Depends on**: Phase 7 (repository correctness)
**Requirements**: API-01, API-02, API-03, API-04, API-05
**Success Criteria** (what must be TRUE):
  1. Every catalog admin endpoint returns the correct HTTP method, status code (200/201/204/400/404/409/422), and response shape for both success and error cases
  2. Storefront query endpoints return correct product listings, filtering results, and detail views with only active (non-draft, non-archived, non-deleted) products
  3. Every protected endpoint rejects unauthenticated requests and requests without the required permission (RequirePermission enforcement verified)
  4. A full product lifecycle (create product, add variants, generate SKU matrix, activate, query storefront) works end-to-end through the API layer
  5. Pagination returns correct offset, limit, total count for normal pages, empty results, and boundary conditions (offset beyond total, limit=0)
**Plans**: TBD

Plans:
- [ ] 08-01: TBD
- [ ] 08-02: TBD

### Phase 9: Entity God-Class Refactoring
**Goal**: The 2,220-line entities.py is split into separate, maintainable files with zero breakage in any existing code or tests
**Depends on**: Phase 2, Phase 3 (domain tests as safety net)
**Requirements**: REF-01, REF-02, REF-03
**Success Criteria** (what must be TRUE):
  1. Each entity/aggregate class (Brand, Category, Product, ProductVariant, SKU, Attribute, AttributeTemplate, AttributeGroup, TemplateAttributeBinding) lives in its own file under an entities/ package directory
  2. An `entities/__init__.py` re-exports every public name so that all 50+ existing import sites continue to work with zero changes
  3. The full test suite (all tests from Phases 1-8) passes with zero failures after the split, confirming no import breakage or circular dependency issues
**Plans**: TBD

Plans:
- [ ] 09-01: TBD
- [ ] 09-02: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7 -> 8 -> 9

| Phase | Plans Complete | Status | Completed |
| ----- | -------------- | ------ | --------- |
| 1. Test Infrastructure | 0/3 | Planning complete | - |
| 2. Value Objects & Entity Foundations | 0/0 | Not started | - |
| 3. Product Aggregate Behavior | 0/0 | Not started | - |
| 4. Brand, Category & Attribute Command Handlers | 0/0 | Not started | - |
| 5. Product & Variant Command Handlers | 0/0 | Not started | - |
| 6. SKU, Media & Cross-Cutting Commands | 0/0 | Not started | - |
| 7. Repository & Data Integrity | 0/0 | Not started | - |
| 8. API Contract Validation | 0/0 | Not started | - |
| 9. Entity God-Class Refactoring | 0/0 | Not started | - |
