# Phase 1: Test Infrastructure - Context

**Gathered:** 2026-03-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Install new test dependencies, build test data factories for all catalog entities, create a FakeUnitOfWork for command handler isolation, build hypothesis strategies for attrs-based domain models, and implement N+1 query detection utilities. This phase delivers zero test cases — it builds the infrastructure that Phases 2-8 consume.

</domain>

<decisions>
## Implementation Decisions

### Factory Pattern
- **D-01:** Use fluent Builders as the primary factory pattern for all catalog domain entities (ProductBuilder, SKUBuilder, BrandBuilder, etc.). Mothers become thin wrappers calling builders with sensible defaults.
- **D-02:** Expand Polyfactory ORM factories (orm_factories.py) for new catalog ORM models. Builders are for domain entities, Polyfactory for ORM-level seeding.

### FakeUnitOfWork Design
- **D-03:** Build a full in-memory FakeUnitOfWork with real dict-based repository storage. It must track registered aggregates, collect domain events on commit, and allow tests to verify actual state changes (not mock interactions).
- **D-04:** The existing `make_uow()` AsyncMock pattern in identity/user tests remains untouched — FakeUoW is for new catalog tests only.

### Hypothesis Strategy Depth
- **D-05:** Build full aggregate tree strategies — generate complete Product→Variant→SKU hierarchies with attribute values. This catches EAV combinatorial edge cases that targeted tests miss.
- **D-06:** Strategies must compose: leaf strategies (Money, slugs, i18n names) combine into entity strategies, which combine into aggregate trees. Each level usable independently.

### File Organization
- **D-07:** One builder file per entity: `product_builder.py`, `brand_builder.py`, `category_builder.py`, `attribute_builder.py`, `sku_builder.py`, `variant_builder.py`, etc. Placed under `tests/factories/`.
- **D-08:** One hypothesis strategy file per entity domain, co-located with builders: `tests/factories/strategies/` directory.

### N+1 Query Detection
- **D-09:** Build an `assert_query_count(session, expected)` context manager using SQLAlchemy's `after_cursor_execute` event.
- **D-10:** Also build pre-built catalog query count assertions for common patterns (list_products, get_product_detail, storefront queries). These become reference baselines for Phases 7-8.

### Cross-Module Stubs
- **D-11:** Use per-test inline AsyncMock for cross-module dependencies (ISupplierQueryService, IImageBackendClient). Keep stubs simple and local to each test rather than building shared fakes directory.

### Test Naming & Organization
- **D-12:** Use class-per-entity organization: TestBrand, TestProduct, TestSKU classes with descriptive test methods. This matches the existing identity module pattern (TestIdentity, TestCustomer).

### Claude's Discretion
- Exact Builder API design (method names, chaining style)
- Internal structure of FakeUnitOfWork (dict keys, collection types)
- Hypothesis strategy shrinking configuration
- Whether to add pytest fixtures wrapping builders for common test setups

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing test infrastructure
- `backend/tests/conftest.py` — Root conftest with DB/Redis URLs, DI container, db_session fixture
- `backend/tests/integration/conftest.py` — Integration conftest with nested-transaction rollback pattern
- `backend/tests/e2e/conftest.py` — E2E conftest with FastAPI app, httpx AsyncClient, auth fixtures

### Existing factory patterns (models to follow)
- `backend/tests/factories/builders.py` — Fluent Builder pattern (RoleBuilder, SessionBuilder, CategoryBuilder)
- `backend/tests/factories/catalog_mothers.py` — Object Mother pattern for catalog domain
- `backend/tests/factories/identity_mothers.py` — Object Mother pattern for identity domain
- `backend/tests/factories/orm_factories.py` — Polyfactory ORM model factories

### Existing fakes
- `backend/tests/fakes/oidc_provider.py` — Stub OIDC provider (pattern reference for cross-module fakes)

### Domain entities to build factories for
- `backend/src/modules/catalog/domain/entities.py` — All 9+ entity/aggregate classes (2,220 lines)
- `backend/src/modules/catalog/domain/value_objects.py` — Value objects (Money, BehaviorFlags, etc.)
- `backend/src/modules/catalog/domain/interfaces.py` — Repository ABCs (10 interfaces)

### UnitOfWork interface
- `backend/src/shared/interfaces/uow.py` — IUnitOfWork interface (contract FakeUoW must implement)
- `backend/src/infrastructure/database/uow.py` — Real UoW implementation (reference for behavior)

### Test configuration
- `backend/pytest.ini` — pytest config with markers, asyncio mode
- `backend/pyproject.toml` — Project dependencies including test deps

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `tests/factories/builders.py`: Fluent Builder with `.with_*()` methods and `.build()` — extend this pattern for catalog entities
- `tests/factories/orm_factories.py`: Polyfactory `ModelFactory` subclasses — add catalog ORM factories here or in separate files
- `tests/factories/catalog_mothers.py`: Existing catalog mothers — will become thin wrappers around new builders
- `make_uow()` helper: Existing AsyncMock-based UoW — stays for identity/user tests, FakeUoW is new for catalog

### Established Patterns
- All entities use `attrs` `@define` decorator with factory `create()` class methods
- Domain models use `AggregateRoot` mixin with `add_domain_event()` / `clear_domain_events()`
- Repositories follow `ICatalogRepository[T]` generic ABC
- Tests use `asyncio_mode = "auto"` — all async test functions auto-detected

### Integration Points
- New builders go in `tests/factories/` alongside existing files
- New hypothesis strategies go in `tests/factories/strategies/` (new directory)
- FakeUnitOfWork goes in `tests/fakes/` alongside existing oidc_provider.py
- N+1 detection utility goes in `tests/utils/` (new directory) or `tests/conftest.py`
- New deps added to `backend/pyproject.toml` `[dependency-groups]` test group

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. User wants full aggregate tree generation via hypothesis and per-entity file organization for clarity.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 01-test-infrastructure*
*Context gathered: 2026-03-28*
