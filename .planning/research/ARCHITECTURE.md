# Architecture Research: EAV Catalog Testing & Validation Strategy

**Domain:** EAV Catalog Hardening in DDD Hexagonal/CQRS Architecture
**Researched:** 2026-03-28
**Confidence:** HIGH

## System Overview: Testing Layers

```
+-------------------------------------------------------------------+
|                    PRESENTATION LAYER                              |
|  FastAPI Routers / Pydantic Schemas / Auth Dependencies           |
|  Test type: E2E (HTTP) + Schema unit tests                        |
+-------------------------------+-----------------------------------+
                                |
+-------------------------------v-----------------------------------+
|                    APPLICATION LAYER                               |
|  +-------------------+    +---------------------+                 |
|  | Command Handlers  |    | Query Handlers      |                 |
|  | (44 untested!)    |    | (AsyncSession-based) |                |
|  | Uses: UoW + Repos |    | Uses: ORM directly  |                 |
|  +--------+----------+    +---------+-----------+                 |
|           |                         |                             |
|  Test type: Unit (mock             Test type: Integration         |
|  repos + UoW)                      (real DB session)              |
+-------------------------------+-----------------------------------+
                                |
+-------------------------------v-----------------------------------+
|                    DOMAIN LAYER                                    |
|  Entities: Brand, Category, Product(+Variant+SKU), Attribute,     |
|            AttributeValue, AttributeTemplate, etc.                |
|  Value Objects: Money, BehaviorFlags, ProductStatus, enums        |
|  Events: 27 domain events                                         |
|  Test type: Pure unit tests (zero dependencies)                   |
+-------------------------------------------------------------------+
                                |
+-------------------------------v-----------------------------------+
|                    INFRASTRUCTURE LAYER                            |
|  Repository implementations (Data Mapper pattern)                 |
|  ORM Models (SQLAlchemy 2.1)                                      |
|  External clients (ImageBackend HTTP)                             |
|  Test type: Integration (real PostgreSQL via testcontainers)      |
+-------------------------------------------------------------------+
```

### Component Responsibilities

| Component | Responsibility | Test Strategy |
|-----------|---------------|---------------|
| Domain Entities (9+ classes) | Business logic, invariants, FSM, factory methods, validation | Pure unit tests -- no mocks needed, just construct and assert |
| Value Objects (Money, BehaviorFlags, etc.) | Immutable domain concepts with self-validation | Pure unit tests -- constructor validation, equality, edge cases |
| Domain Events (27 events) | Immutable records of state changes with required-field validation | Pure unit tests -- construction, required fields, aggregate_id |
| Command Handlers (46 handlers) | Use-case orchestration: validate preconditions, call domain, persist | Unit tests with mocked repos + UoW (AsyncMock) |
| Query Handlers (18+ handlers) | Direct ORM reads, read models, pagination | Integration tests -- need real DB schema and data |
| Repository Interfaces (10 ABCs) | Abstract contracts for persistence | Not tested directly (ABCs) |
| Repository Implementations | SQLAlchemy Data Mapper: `_to_domain()` / `_to_orm()` + queries | Integration tests with real PostgreSQL session |
| ORM Models | SQLAlchemy declarative models, constraints, relationships | Tested implicitly via repository integration tests |
| Pydantic Schemas | Request/response validation, camelCase aliasing | Unit tests for serialization edge cases |
| API Routers | HTTP handling, auth, DI wiring | E2E tests with real HTTP client (httpx AsyncClient) |

## Testing Strategy Per Layer

### Layer 1: Domain Layer (Test First -- Zero Dependencies)

**Why first:** Domain entities are pure Python with zero infrastructure imports. They depend only on the shared kernel (`AggregateRoot`). Every other layer depends on the domain. Testing here catches business logic bugs without any infrastructure setup.

**What to test:**

**Entity Factory Methods (`create()`):**
- Happy path: `Brand.create(name="Nike", slug="nike")` produces valid entity
- Slug validation: invalid slugs raise `ValueError`
- i18n validation: empty dicts, blank values, missing required locales
- ID generation: generates UUID when not provided, uses provided UUID when given
- Default state: `Product.create()` starts in `DRAFT` status, creates default variant

**Entity Mutation Methods (`update()`, `transition_status()`, etc.):**
- `_UPDATABLE_FIELDS` whitelist: unknown fields raise `TypeError`
- Guarded fields: direct `product.status = X` raises `AttributeError`
- FSM transitions: valid transitions succeed, invalid raise `InvalidStatusTransitionError`
- Readiness checks: cannot publish without active priced SKU
- Soft delete: cascades to variants and SKUs, blocked on PUBLISHED products

**Aggregate Child Management:**
- `Product.add_variant()` / `remove_variant()`: cannot remove last variant
- `Product.add_sku()`: variant_hash uniqueness check across all variants
- `Product.find_variant()` / `find_sku()`: excludes soft-deleted entities

**Value Objects:**
- `Money`: non-negative amount, 3-char currency, cross-currency comparison blocked
- `BehaviorFlags`: search_weight range [1, 10]
- `validate_validation_rules()`: type-specific key whitelist enforcement

**Domain Events:**
- Required field validation in `__post_init__`
- `aggregate_id` auto-populated from `_aggregate_id_field`
- `__init_subclass__` guards: must override `event_type` and `aggregate_type`

**Pattern:**
```python
# Pure unit test -- no mocks, no fixtures, no DB
def test_product_create_emits_created_event():
    product = Product.create(
        slug="test-product",
        title_i18n={"en": "Test", "ru": "Тест"},
        brand_id=uuid.uuid4(),
        primary_category_id=uuid.uuid4(),
    )
    assert product.status == ProductStatus.DRAFT
    assert len(product.variants) == 1  # default variant
    events = product.domain_events
    assert len(events) == 1
    assert isinstance(events[0], ProductCreatedEvent)

def test_product_cannot_transition_draft_to_published():
    product = _make_draft_product()
    with pytest.raises(InvalidStatusTransitionError):
        product.transition_status(ProductStatus.PUBLISHED)
```

**Estimated scope:** ~150-200 test cases across all entities and value objects.

### Layer 2: Command Handler Unit Tests (Mocked Dependencies)

**Why second:** Command handlers orchestrate domain logic with repository calls. With the domain already tested, handler tests focus on orchestration correctness: "does the handler call the right repos in the right order and raise the right exceptions?"

**What to test per handler:**
1. Happy path: command succeeds, entity persisted, event emitted, UoW committed
2. Precondition failures: slug conflict, FK not found, business rule violation
3. Domain delegation: handler passes correct args to entity factory/methods
4. UoW integration: `register_aggregate()` called, `commit()` called

**Mocking strategy:**
- Mock all repository interfaces (`IBrandRepository`, etc.) using `unittest.mock.AsyncMock`
- Mock `IUnitOfWork` as an async context manager with `commit()` and `register_aggregate()` methods
- Mock `ILogger` (or use a no-op stub)
- No database, no ORM, no real I/O

**Pattern:**
```python
async def test_create_brand_slug_conflict():
    brand_repo = AsyncMock(spec=IBrandRepository)
    brand_repo.check_slug_exists.return_value = True
    uow = make_fake_uow()
    logger = AsyncMock(spec=ILogger)
    handler = CreateBrandHandler(brand_repo=brand_repo, uow=uow, logger=logger)

    with pytest.raises(BrandSlugConflictError):
        await handler.handle(CreateBrandCommand(name="Nike", slug="nike"))

    uow.commit.assert_not_awaited()  # should NOT commit on failure
```

**Critical handlers to prioritize (complex orchestration):**
1. `CreateProductHandler` -- validates brand FK, category FK, supplier active check, source URL for cross-border, slug uniqueness, media attachment
2. `ChangeProductStatusHandler` -- FSM validation, readiness checks
3. `GenerateSkuMatrixHandler` -- combinatorial SKU generation
4. `AssignProductAttributeHandler` -- template binding check, level matching, duplicate guard
5. `BulkCreateAttributesHandler` / `BulkCreateCategoriesHandler` -- batch validation logic
6. `CloneAttributeTemplateHandler` -- deep copy with binding replication

**Estimated scope:** ~200-250 test cases (46 handlers x ~4-5 tests each).

### Layer 3: Repository Integration Tests (Real PostgreSQL)

**Why third:** Repositories implement the Data Mapper pattern (`_to_domain()` / `_to_orm()`) and complex queries. These must be tested against real PostgreSQL because:
- SQLAlchemy ORM model mapping correctness
- PostgreSQL-specific features (JSONB, recursive CTEs, `FOR UPDATE SKIP LOCKED`)
- Constraint enforcement (unique indexes, FK constraints)
- Soft-delete filtering in queries

**What to test:**
- CRUD round-trip: `add()` -> `get()` -> `update()` -> `delete()` -> `get()` returns None
- Domain<->ORM fidelity: complex fields (JSONB for i18n, nested lists, Money decomposition)
- Uniqueness checks: `check_slug_exists()`, `check_code_exists()`
- Deletion guards: `has_products()`, `has_children()`, `has_bindings_for_attribute()`
- Complex queries: `propagate_effective_template_id()` (recursive CTE), `get_all_ordered()` (tree)
- Eager loading: `get_with_variants()` loads Product + Variants + SKUs in one query
- Pessimistic locking: `get_for_update()` uses `SELECT FOR UPDATE`

**Test infrastructure already in place:**
- `db_session` fixture: nested transaction per test, auto-rollback
- `testcontainers` or local Docker PostgreSQL (based on conftest URLs)
- `SQLAlchemyFactory` (polyfactory) for ORM model seeding

**Repositories to test (priority order):**
1. `ProductRepository` -- most complex: eager loading, soft-delete filtering, variant_hash checks
2. `CategoryRepository` -- recursive CTE for template propagation, tree ordering
3. `AttributeValueRepository` -- bulk operations, parent-scoped uniqueness
4. `TemplateAttributeBindingRepository` -- batch loading, sort order bulk update
5. `BrandRepository` -- simpler but foundational (tests exist partially)
6. `MediaAssetRepository` -- sort order bulk update, main-media check

**Estimated scope:** ~100-120 test cases.

### Layer 4: Query Handler Integration Tests (Real PostgreSQL)

**Why fourth:** Query handlers bypass the domain layer and read directly from ORM via `AsyncSession`. They must be tested with real data to verify:
- Correct SQL generation (joins, filters, ordering)
- Read model mapping (ORM row -> dataclass/Pydantic)
- Pagination behavior
- N+1 query detection (verify expected query counts)

**What to test:**
- List queries: pagination, filtering, ordering
- Detail queries: all fields populated correctly
- Tree queries: `GetCategoryTreeHandler` returns correct nesting
- Computed queries: `GetProductCompletenessHandler` correctly checks template bindings
- Storefront queries: correct product status filtering (only PUBLISHED)

**Pattern:**
```python
async def test_list_brands_paginated(db_session: AsyncSession):
    # Seed 25 brands via ORM factories
    for i in range(25):
        db_session.add(BrandModel(id=uuid.uuid4(), name=f"Brand-{i}", slug=f"brand-{i}"))
    await db_session.flush()

    handler = ListBrandsHandler(session=db_session, logger=stub_logger())
    result = await handler.handle(ListBrandsQuery(page=1, page_size=10))

    assert result.total == 25
    assert len(result.items) == 10
```

**Estimated scope:** ~60-80 test cases.

### Layer 5: E2E / API Integration Tests

**Why last:** E2E tests exercise the full stack (HTTP -> Router -> Handler -> Domain -> DB -> Response). They are the most expensive to run and slowest. Write them for critical user flows after unit/integration coverage is solid.

**What to test:**
- Request validation: Pydantic schema rejects malformed input (422)
- Authorization: endpoints require correct permissions (401/403)
- Response contract: correct HTTP status codes, JSON structure, camelCase aliasing
- Error mapping: domain exceptions map to correct error envelopes

**Priority flows:**
1. Product CRUD lifecycle (create draft -> enrich -> publish -> archive)
2. Category tree management (create root -> add children -> move -> delete)
3. Attribute + template binding flow (create group -> create attribute -> create template -> bind)
4. SKU matrix generation (create product -> add variants -> generate matrix)

**Estimated scope:** ~30-40 test cases covering critical paths.

## Aggregate Boundary Validation

### Aggregate Identification

The catalog module contains these aggregates and child entities:

| Aggregate Root | Child Entities | Boundary Notes |
|---------------|----------------|----------------|
| **Brand** | (none) | Simple aggregate. Deletion guard: `has_products`. Slug guarded. |
| **Category** | (none) | Tree structure. Deletion guards: `has_children`, `has_products`. Template inheritance via `effective_template_id`. |
| **AttributeGroup** | (none) | Deletion guard: `has_attributes`. Code guarded. |
| **Attribute** | AttributeValue (via separate repo) | Dictionary attributes own values. Code and slug guarded. |
| **AttributeTemplate** | TemplateAttributeBinding (via separate repo) | Template owns bindings. Deletion guard: `has_category_references`. |
| **Product** | ProductVariant -> SKU | Most complex aggregate. FSM status. Variant hash uniqueness. Optimistic locking (`version`). Soft-delete cascade. |
| **MediaAsset** | (none) | Independent entity (not AggregateRoot). Scoped to product+variant. |
| **ProductAttributeValue** | (none) | EAV pivot entity. Not aggregate root. Managed via dedicated repo. |

### Boundary Validation Tests

**Product aggregate boundary is the most critical to validate:**

1. **Invariant: Status FSM**
   - Test all 7 valid transitions succeed
   - Test all invalid transitions are rejected (e.g., DRAFT -> PUBLISHED)
   - Test guard: cannot publish without active priced SKU
   - Test guard: cannot publish without any active SKU

2. **Invariant: Variant hash uniqueness**
   - Test: two SKUs with same variant attributes on same variant -> `DuplicateVariantCombinationError`
   - Test: same attributes on different variants -> different hashes (variant_id included)
   - Test: empty attributes on two different variants -> both succeed (variant_id disambiguates)

3. **Invariant: Cannot remove last variant**
   - Test: product with 1 variant, `remove_variant()` -> `LastVariantRemovalError`
   - Test: product with 2 variants, `remove_variant()` -> succeeds

4. **Invariant: Cannot delete published product**
   - Test: `soft_delete()` on PUBLISHED product -> `CannotDeletePublishedProductError`
   - Test: `soft_delete()` on DRAFT/ARCHIVED -> succeeds with cascade

5. **Invariant: Guarded field protection**
   - Test: `product.status = ProductStatus.PUBLISHED` -> `AttributeError`
   - Test: `brand.slug = "new-slug"` -> `AttributeError`
   - Test: `category.slug = "new"` -> `AttributeError`

6. **Cross-aggregate consistency (validated in command handlers):**
   - Product requires existing Brand (FK check in `CreateProductHandler`)
   - Product requires existing Category (FK check in `CreateProductHandler`)
   - Attribute assignment checks template binding (`AssignProductAttributeHandler`)
   - Attribute assignment checks level match (`AttributeLevelMismatchError`)
   - Attribute deletion blocked by template bindings (`AttributeHasTemplateBindingsError`)
   - Brand deletion blocked by products (`BrandHasProductsError`)

### Domain Event Consistency Tests

Every aggregate mutation that should emit events must be verified:

| Operation | Expected Event | Test Scope |
|-----------|---------------|------------|
| `Product.create()` | `ProductCreatedEvent` | Domain unit test |
| `Product.transition_status()` | `ProductStatusChangedEvent` | Domain unit test |
| `Product.update()` | `ProductUpdatedEvent` | Domain unit test |
| `Product.soft_delete()` | `ProductDeletedEvent` | Domain unit test |
| `Product.add_variant()` | `VariantAddedEvent` | Domain unit test |
| `Product.remove_variant()` | `VariantDeletedEvent` | Domain unit test |
| `Product.add_sku()` | `SKUAddedEvent` | Domain unit test |
| `Product.remove_sku()` | `SKUDeletedEvent` | Domain unit test |
| Brand/Category events | Emitted in command handlers, not entity | Handler unit test |

## Data Flow: Testing Each Path

### Command (Write) Path Testing

```
HTTP Request
    |
    v (NOT tested in unit tests -- tested in E2E)
[Router] -- validates Pydantic schema, constructs Command
    |
    v (Unit test boundary starts here)
[Command Handler]
    |-- opens UoW context      (mock: async context manager)
    |-- repo.check_*()         (mock: return True/False for preconditions)
    |-- Entity.create/update   (real: tested in domain layer)
    |-- repo.add/update()      (mock: return entity)
    |-- uow.register_aggregate (mock: verify called)
    |-- uow.commit()           (mock: verify called)
    |
    v (Unit test boundary ends here)
[Result dataclass returned]
```

### Query (Read) Path Testing

```
HTTP Request
    |
    v (NOT tested in integration -- tested in E2E)
[Router] -- validates params, constructs Query
    |
    v (Integration test boundary starts here)
[Query Handler]
    |-- session.execute(select(...)) (real: needs DB + seeded data)
    |-- paginate() helper            (real: tests pagination math)
    |-- mapper function              (real: tests ORM -> read model)
    |
    v (Integration test boundary ends here)
[ReadModel returned]
```

## Build Order Implications

The testing phases should be executed in this order because of dependency and risk:

### Phase 1: Domain Entity Tests + Entity God-Class Split
**Rationale:** The 2,220-line `entities.py` must be split before writing tests, otherwise test files will have confusing imports and the entity file is too unwieldy to review. Split first, then test each entity file.

**Split plan:**
```
domain/entities.py (2,220 lines)
  -> domain/brand.py         (~90 lines)
  -> domain/category.py      (~200 lines)
  -> domain/attribute.py     (~250 lines)
  -> domain/attribute_value.py (~120 lines)
  -> domain/attribute_group.py (~80 lines)
  -> domain/attribute_template.py (~60 lines)
  -> domain/template_binding.py   (~40 lines)
  -> domain/product.py       (~500 lines: Product + ProductVariant + SKU)
  -> domain/media_asset.py   (~100 lines)
  -> domain/product_attribute_value.py (~60 lines)
  -> domain/entities.py      (re-exports for backward compat)
```

**Dependencies:** None. Pure refactoring.

### Phase 2: Command Handler Unit Tests
**Rationale:** 44 of 46 command handlers are untested. This is the highest-risk gap. With domain entities tested, command handler tests can focus on orchestration logic.

**Dependencies:** Domain entity tests must pass (Phase 1).

### Phase 3: Repository Integration Tests
**Rationale:** Validates the Data Mapper pattern and complex PostgreSQL queries. Must run after domain tests confirm entity behavior is correct, so any repo test failure is clearly a mapping/query bug.

**Dependencies:** Phase 1 (domain entities), Docker PostgreSQL running.

### Phase 4: Query Handler Integration Tests + API E2E
**Rationale:** Validates read paths and full HTTP stack. Lower risk because query handlers are simpler (no business logic, just SQL). E2E tests catch integration gaps between all layers.

**Dependencies:** Phases 1-3, Docker PostgreSQL running.

### Phase 5: Performance Validation
**Rationale:** After correctness is proven, measure query performance. Use `pytest-benchmark` or manual profiling. Check for N+1 patterns in storefront queries, pagination efficiency.

**Dependencies:** All prior phases.

## Anti-Patterns

### Anti-Pattern 1: Testing Command Handlers with Real DB

**What people do:** Write integration tests for command handlers using real PostgreSQL, seeding data via ORM factories.
**Why it is wrong:** Command handlers contain orchestration logic, not query logic. Testing them with a real DB makes tests slow (5-10x), brittle (schema changes break tests), and conflates two concerns (is the business logic right? vs. does the ORM mapping work?).
**Do this instead:** Mock repository interfaces and UoW. Test the handler's decision-making in isolation. Test ORM mapping correctness in dedicated repository integration tests.

### Anti-Pattern 2: Skipping Domain Entity Tests

**What people do:** Jump straight to handler or E2E tests, assuming entity logic "is simple enough."
**Why it is wrong:** In this codebase, entities contain significant logic: FSM transitions with readiness checks, variant hash computation, guarded field protection, soft-delete cascades, i18n validation. Bugs here propagate to every handler that uses them.
**Do this instead:** Test entities first. They are the fastest tests to write and run (no async, no mocks, no DB). Cover every `create()`, `update()`, `transition_status()`, and guard.

### Anti-Pattern 3: Testing Domain Events in Handler Tests Only

**What people do:** Verify event emission only in command handler integration tests.
**Why it is wrong:** Some events are emitted by domain entities directly (Product creates/status/update/delete/variant/SKU events), not by handlers. Handler tests with mocked repos will not exercise entity event emission.
**Do this instead:** Test event emission at the domain layer for entities that emit events directly. Test event emission at the handler layer only for events the handler explicitly constructs.

### Anti-Pattern 4: Mock Object Mother Drift

**What people do:** Create complex mock fixtures that duplicate domain entity construction logic.
**Why it is wrong:** When entity `create()` signature changes, the mock mothers silently produce invalid test data.
**Do this instead:** Use the real `Entity.create()` factory methods in test fixtures. Only mock repository return values, not entity construction. The existing `CategoryBuilder` pattern is correct -- it delegates to real `create_root()` / `create_child()`.

## Integration Points

### Internal Boundaries

| Boundary | Communication | Test Considerations |
|----------|--------------|---------------------|
| Catalog -> Identity (auth) | `RequirePermission` dependency | E2E tests need auth fixtures (admin JWT); unit tests skip auth entirely |
| Catalog -> Supplier (FK check) | `ISupplierQueryService.assert_supplier_active()` | Mock in command handler tests; integration tests need supplier data seeded |
| Catalog -> ImageBackend (media) | `IImageBackendClient.delete()` | Mock in all tests; never call real image backend in test suite |
| Catalog domain events -> Outbox | `uow.register_aggregate()` + `uow.commit()` | Verify in handler unit tests that `register_aggregate` is called; verify in UoW integration tests that outbox rows are created |

### External Services

| Service | Integration Pattern | Test Strategy |
|---------|-------------------|---------------|
| PostgreSQL | SQLAlchemy 2.1 async, Data Mapper, nested transactions | Real DB in integration tests, mock repos in unit tests |
| Redis | Cache-aside for permissions | `_flush_redis` fixture, not directly tested in catalog tests |
| RabbitMQ | TaskIQ worker for outbox relay | Not tested in catalog tests (outbox relay is infrastructure) |
| ImageBackend | HTTP client (`IImageBackendClient`) | Always mocked via `AsyncMock(spec=IImageBackendClient)` |

## Test Infrastructure Gaps

### Existing (usable now)
- `pytest` + `pytest-asyncio` configured
- `db_session` fixture with nested transaction rollback
- `app_container` with Dishka DI and `TestOverridesProvider`
- `polyfactory` ORM factories for `Brand`, `Category`, `Identity`, etc.
- `CategoryBuilder` fluent builder
- E2E test pattern with `admin_client` fixture

### Missing (must be built in Phase 1-2)
- **Product domain fixtures:** No builder or mothers for `Product`, `ProductVariant`, `SKU` entities. Need a `ProductBuilder` that creates products in various states (draft, with variants, with SKUs, with prices, published, etc.)
- **Fake UoW:** A reusable `FakeUnitOfWork` that acts as async context manager, tracks `register_aggregate()` calls, and has inspectable `committed` / `rolled_back` flags
- **Attribute fixtures:** No builders for `Attribute`, `AttributeValue`, `AttributeGroup`, `AttributeTemplate`, `TemplateAttributeBinding`
- **ORM factories expansion:** `polyfactory` factories exist only for `Brand` and `Category` ORM models. Need factories for `Product`, `SKU`, `Variant`, `Attribute`, `AttributeValue`, `TemplateAttributeBinding`, `ProductAttributeValue` ORM models
- **Catalog-specific conftest:** No `conftest.py` in `tests/unit/modules/catalog/` -- needs fixtures for common test data

## Sources

- Codebase analysis: `backend/src/modules/catalog/domain/entities.py` (2,220 lines, 9+ entity classes)
- Codebase analysis: `backend/src/modules/catalog/domain/interfaces.py` (10 repository ABCs)
- Codebase analysis: `backend/src/modules/catalog/application/commands/` (46 command handlers)
- Codebase analysis: `backend/tests/conftest.py` (test infrastructure setup)
- Codebase analysis: `backend/tests/factories/` (existing builders and ORM factories)
- Codebase analysis: `backend/tests/integration/modules/catalog/` (existing repository tests)
- Project requirements: `.planning/PROJECT.md` (44 of 46 handlers untested, 1.1% test coverage)
- Architecture documentation: `.planning/codebase/ARCHITECTURE.md` (hexagonal CQRS patterns)
- Conventions documentation: `.planning/codebase/CONVENTIONS.md` (naming, testing patterns)

---
*Architecture research for: EAV Catalog Testing & Validation Strategy*
*Researched: 2026-03-28*
