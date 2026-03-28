# Requirements: EAV Catalog Hardening

**Defined:** 2026-03-28
**Core Value:** The EAV Catalog module must be provably correct and thoroughly tested — it is the foundation for cart, checkout, and order management.

## v1 Requirements

Requirements for this milestone. Each maps to roadmap phases.

### Test Infrastructure

- [ ] **INFRA-01**: Install and configure new test dependencies (hypothesis, schemathesis, respx, dirty-equals, pytest-randomly, pytest-timeout)
- [ ] **INFRA-02**: Create test data builders/factories for all catalog entities (Product, ProductVariant, SKU, Attribute, AttributeTemplate, TemplateAttributeBinding, AttributeGroup, Brand, Category)
- [ ] **INFRA-03**: Build FakeUnitOfWork for command handler unit test isolation
- [ ] **INFRA-04**: Build hypothesis strategies for attrs-based domain models
- [ ] **INFRA-05**: Implement N+1 query detection via SQLAlchemy `after_cursor_execute` event context manager

### Domain Model Validation

- [ ] **DOM-01**: Unit tests for all entity factory methods and update methods across all 9+ entity/aggregate classes
- [ ] **DOM-02**: Unit tests for Product FSM transitions — all valid paths (draft→active, active→archived, etc.) and all invalid paths
- [ ] **DOM-03**: Unit tests for variant hash uniqueness enforcement and collision detection
- [ ] **DOM-04**: Unit tests for soft-delete cascade behavior across Product→Variant→SKU hierarchy
- [ ] **DOM-05**: Unit tests for all value objects — immutability, validation rules, edge cases
- [ ] **DOM-06**: Unit tests for attribute template governance chain (Category → effective template → bindings → attribute assignment validation)
- [ ] **DOM-07**: Unit tests for domain event emission — correct events emitted at correct lifecycle points

### Command Handler Testing

- [ ] **CMD-01**: Unit tests for all Brand command handlers (create, update, delete, bulk_create)
- [ ] **CMD-02**: Unit tests for all Category command handlers (create, update, delete, reorder, assign_template)
- [ ] **CMD-03**: Unit tests for all Attribute command handlers (create_template, update_template, delete_template, create_group, manage_bindings)
- [ ] **CMD-04**: Unit tests for all Product command handlers (create, update, delete, change_status, assign_attributes)
- [ ] **CMD-05**: Unit tests for all Variant command handlers (add_variant, update_variant, remove_variant)
- [ ] **CMD-06**: Unit tests for all SKU command handlers (add_sku, update_sku, remove_sku, generate_sku_matrix)
- [ ] **CMD-07**: Unit tests for all Media command handlers (sync_media, reorder_media)
- [ ] **CMD-08**: Verify domain event emission in all command handlers that produce events
- [ ] **CMD-09**: Test bulk operation atomicity — bulk_create_brands and generate_sku_matrix rollback on partial failure
- [ ] **CMD-10**: Test FK-not-found and uniqueness conflict error paths across all handlers

### Repository & Data Integrity

- [ ] **REPO-01**: Integration tests for Product repository — full 3-level variant/SKU Data Mapper roundtrip (create, read, update, delete)
- [ ] **REPO-02**: Integration tests for Brand, Category, Attribute repositories — CRUD operations with real PostgreSQL
- [ ] **REPO-03**: Schema constraint audit — verify all FK, unique, and check constraints are correctly defined in migrations
- [ ] **REPO-04**: Soft-delete filter audit — verify `deleted_at IS NULL` filtering in every repository method and query handler
- [ ] **REPO-05**: ORM-to-domain mapping fidelity — verify all entity fields survive roundtrip through ORM models

### API Contract Validation

- [ ] **API-01**: Integration tests for all catalog admin REST endpoints — correct HTTP methods, status codes, response shapes
- [ ] **API-02**: Integration tests for storefront query endpoints — product listing, filtering, detail views
- [ ] **API-03**: Authorization enforcement tests — verify RequirePermission on all protected endpoints
- [ ] **API-04**: Full lifecycle integration tests — create product → add variants → generate SKU matrix → activate → query storefront
- [ ] **API-05**: Pagination behavior tests — offset, limit, total count, empty results, boundary conditions

### Entity Refactoring

- [ ] **REF-01**: Split `backend/src/modules/catalog/domain/entities.py` (2,220 lines) into separate files per entity/aggregate
- [ ] **REF-02**: Create `entities/__init__.py` with backward-compatible re-exports preserving all 50+ existing import sites
- [ ] **REF-03**: Verify all existing tests pass after the split with zero import changes in consuming code

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Performance Validation

- **PERF-01**: N+1 query detection across all catalog query handlers
- **PERF-02**: Pagination efficiency audit — evaluate cursor-based pagination for high-volume endpoints
- **PERF-03**: Load testing with Locust for catalog endpoints under concurrent access

### Advanced Testing

- **ADV-01**: Schemathesis API fuzzing from OpenAPI spec
- **ADV-02**: Concurrent session tests for optimistic locking on Product aggregate
- **ADV-03**: Property-based testing for EAV attribute combinatorial state
- **ADV-04**: Orphaned attribute value detection and cleanup

### Documentation

- **DOC-01**: API contract documentation for all catalog endpoints
- **DOC-02**: Domain model documentation — entity relationships, invariants, FSM diagrams

## Out of Scope

| Feature | Reason |
|---------|--------|
| Order module / cart / checkout | Future milestone — depends on this hardening work |
| Payment integration | Future milestone |
| Frontend changes or tests | This milestone is backend catalog only |
| Other module testing (identity, user, geo) | Separate effort, different milestone |
| Refactoring away from EAV pattern | EAV is a deliberate architectural choice |
| Search/filtering backend for storefront | Future milestone |
| Admin frontend fixes (mock data, TypeScript) | Separate effort |
| 100% test coverage target | Diminishing returns — aim for meaningful coverage of business logic |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| INFRA-01 | — | Pending |
| INFRA-02 | — | Pending |
| INFRA-03 | — | Pending |
| INFRA-04 | — | Pending |
| INFRA-05 | — | Pending |
| DOM-01 | — | Pending |
| DOM-02 | — | Pending |
| DOM-03 | — | Pending |
| DOM-04 | — | Pending |
| DOM-05 | — | Pending |
| DOM-06 | — | Pending |
| DOM-07 | — | Pending |
| CMD-01 | — | Pending |
| CMD-02 | — | Pending |
| CMD-03 | — | Pending |
| CMD-04 | — | Pending |
| CMD-05 | — | Pending |
| CMD-06 | — | Pending |
| CMD-07 | — | Pending |
| CMD-08 | — | Pending |
| CMD-09 | — | Pending |
| CMD-10 | — | Pending |
| REPO-01 | — | Pending |
| REPO-02 | — | Pending |
| REPO-03 | — | Pending |
| REPO-04 | — | Pending |
| REPO-05 | — | Pending |
| API-01 | — | Pending |
| API-02 | — | Pending |
| API-03 | — | Pending |
| API-04 | — | Pending |
| API-05 | — | Pending |
| REF-01 | — | Pending |
| REF-02 | — | Pending |
| REF-03 | — | Pending |

**Coverage:**
- v1 requirements: 35 total
- Mapped to phases: 0
- Unmapped: 35 ⚠️

---
*Requirements defined: 2026-03-28*
*Last updated: 2026-03-28 after initial definition*
