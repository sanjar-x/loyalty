# Project Research Summary

**Project:** Loyality -- EAV Catalog Hardening
**Domain:** Testing, validation, and correctness for a production EAV catalog in a DDD/CQRS e-commerce backend
**Researched:** 2026-03-28
**Confidence:** HIGH

## Executive Summary

This project is a testing and validation milestone for an existing EAV (Entity-Attribute-Value) catalog module inside a Python/FastAPI/SQLAlchemy DDD modular monolith. The catalog already has 46 command handlers, 22 query handlers, 11 router files, and a rich domain model with 9+ entity classes -- but only 1.1% test coverage. 44 of 46 command handlers are completely untested. The goal is not to build new features but to prove the existing code is correct before the order system is built on top of it.

Experts harden EAV systems by testing bottom-up: value objects first, then domain entities (pure unit tests with zero infrastructure), then command handler orchestration (mocked repositories), then repository Data Mapper fidelity (real PostgreSQL), then query handlers and API contracts. This order matters because EAV systems push schema enforcement out of the database and into application code -- a bug in a value object or entity method cascades into every handler that uses it. The existing test infrastructure (pytest, pytest-asyncio, testcontainers, polyfactory, nested transaction fixtures) is solid; the gap is purely coverage. New tooling needed is minimal: hypothesis for property-based EAV invariant testing, schemathesis for API contract fuzzing, respx for HTTP mocking, dirty-equals for readable assertions, and pytest-randomly/pytest-timeout for test reliability.

The key risks are: (1) writing mock-heavy handler tests that pass while real Data Mapper bugs go undetected -- mitigated by requiring domain entity tests and repository integration tests before handler tests; (2) splitting the 2,220-line god-class entity file before tests exist to verify the split -- mitigated by deferring the split until after Phase 1 tests are in place; (3) EAV-specific integrity issues like orphaned attribute values, template drift, and soft-delete leaks in queries -- mitigated by systematic negative testing at every layer. The total estimated scope is 550-700 test cases across 5 phases.

## Key Findings

### Recommended Stack

The production stack (Python 3.14, FastAPI, SQLAlchemy 2.1 async, PostgreSQL 18, Dishka DI) and core test infrastructure (pytest 9.x, pytest-asyncio, testcontainers, polyfactory, pytest-archon) are already in place and should not change. Research identified six new testing dependencies to add and two small custom utilities to build. See `.planning/research/STACK.md` for full details.

**New testing dependencies:**
- **hypothesis (>=6.151.5):** Property-based testing for EAV domain invariants -- combinatorial attribute-value states that example-based tests miss
- **schemathesis (>=4.13.0):** Auto-generates API contract test cases from FastAPI's OpenAPI spec -- covers 44+ endpoints without manual case writing
- **dirty-equals (>=0.11):** Readable assertion helpers for API responses with UUIDs, timestamps, and nested objects
- **respx (>=0.22.0):** Mock httpx requests to the image backend service -- the canonical httpx mocking library
- **pytest-randomly (>=3.16.0):** Randomize test order to detect hidden inter-test dependencies as the suite scales
- **pytest-timeout (>=2.4.0):** 30-second default timeout to catch hanging async tests with real DB connections

**Custom utilities to build (not libraries):**
- Query count assertion context manager using SQLAlchemy `after_cursor_execute` events (replaces unmaintained nplusone)
- Hypothesis strategies for EAV domain types (attribute values, i18n names, slugs)

### Expected Features

This is a hardening milestone, not a feature milestone. "Features" are testing and validation capabilities. See `.planning/research/FEATURES.md` for the full prioritization matrix.

**Must have (P1 -- blocks the order system):**
- Value object unit tests (Money, BehaviorFlags, slug/i18n validation)
- Product aggregate unit tests (FSM, variant/SKU management, soft-delete cascade, variant hash)
- Brand, Category, Attribute entity unit tests
- Test data builders (ProductBuilder, attribute fixtures, FakeUnitOfWork)
- Command handler unit tests for all 46 handlers (~200-300 test cases)
- Product repository integration tests (CRUD, eager loading, soft-delete, variant sync)
- Category repository integration tests (tree operations, recursive CTE template propagation)
- Entity god-class split (prerequisite for maintainable test organization)
- Data integrity validation (schema constraint audit)

**Should have (P2 -- significantly reduces risk):**
- Query handler tests for all 22 handlers
- API contract integration tests for all 11 routers
- Product status FSM full lifecycle integration test
- Completeness checker integration test
- Optimistic locking concurrency tests

**Defer (P3/v2+):**
- Property-based testing for variant hash collisions
- N+1 query detection instrumentation
- API response snapshot tests
- Storefront query caching correctness
- Migration integrity audit

**Anti-features (deliberately excluded):**
- Refactoring away from EAV pattern
- Search/Elasticsearch integration
- Frontend test coverage
- Performance optimization before correctness
- 100% code coverage target
- Automated load testing

### Architecture Approach

The testing architecture follows the existing hexagonal/CQRS layer boundaries. The domain layer (pure Python entities, value objects, events) gets pure unit tests with zero dependencies. Command handlers get unit tests with mocked repository interfaces and UoW. Repositories get integration tests against real PostgreSQL via testcontainers. Query handlers get integration tests with seeded data. API routers get E2E tests with httpx AsyncClient. This layering mirrors the production architecture and ensures each layer's correctness is verified independently before higher layers are tested. See `.planning/research/ARCHITECTURE.md` for component-level test strategies.

**Major components and their test strategies:**
1. **Domain Layer (9+ entities, value objects, 27 events)** -- Pure unit tests, ~150-200 cases. No mocks, no DB, fastest to write and run.
2. **Command Handlers (46 handlers)** -- Unit tests with AsyncMock repos/UoW, ~200-250 cases. Test orchestration logic only.
3. **Repository Implementations (6 priority repos)** -- Integration tests with real PostgreSQL, ~100-120 cases. Validate Data Mapper fidelity.
4. **Query Handlers (22 handlers)** -- Integration tests with seeded data, ~60-80 cases. Verify SQL generation and read model mapping.
5. **API Routers (11 files)** -- E2E tests via httpx AsyncClient, ~30-40 cases. Verify HTTP contracts and error mapping.

### Critical Pitfalls

Top 5 pitfalls from `.planning/research/PITFALLS.md`, ordered by risk:

1. **Mock-heavy handler tests hiding real bugs** -- The most dangerous pattern. Writing 44 handler tests with mocked repos feels productive but tests zero Data Mapper logic. Prevent by writing domain entity tests and repository integration tests BEFORE handler tests. If all 44 handler tests are written in under 2 days, mapping logic was not tested.

2. **God-class split breaking import compatibility** -- Splitting `entities.py` (2,220 lines) seems simple but risks `ImportError` and `NameError` at runtime due to circular imports, shared private helpers, and module initialization order. Prevent by doing the split AFTER tests exist, moving one entity at a time (simplest first), and maintaining a re-export `__init__.py` permanently.

3. **Optimistic locking silently not working** -- Product has a `version` field but it may not be properly configured with SQLAlchemy's `version_id_col`. Child entity changes (add SKU) may not bump the parent version. Prevent with a dedicated concurrent-session integration test.

4. **EAV attribute integrity gaps** -- Orphaned attribute values after template unbinding, template drift when parent category templates change, level mismatches between product-level and variant-level attributes. Prevent with systematic negative tests for the full attribute governance chain.

5. **Async SQLAlchemy lazy-load landmines** -- `MissingGreenlet` errors when test code accesses relationships not eagerly loaded. Prevent by establishing the "re-fetch for assertions" pattern (`session.get()` after handler execution) in the earliest integration tests.

## Implications for Roadmap

Based on research, the work should be structured in 5 phases with strict ordering. The ordering is driven by three principles: (a) test the layers with zero dependencies first, (b) verify each layer before testing layers that depend on it, (c) defer structural refactoring until tests exist to verify it.

### Phase 1: Foundation -- Domain Model Tests + Test Infrastructure

**Rationale:** Domain entities are pure Python with zero infrastructure dependencies. They are the fastest tests to write, the fastest to run, and they establish a trusted foundation. Every higher layer depends on domain correctness. Test infrastructure (builders, fake UoW, attribute fixtures) must be built here to enable Phase 2 efficiency.

**Delivers:**
- Value object unit tests (Money, BehaviorFlags, ProductStatus, slug/i18n validation)
- Product aggregate unit tests (~40-60 cases: create, FSM, add/remove variant, add/remove SKU, soft-delete cascade, variant hash, domain events)
- Brand, Category, Attribute, AttributeValue, AttributeTemplate entity unit tests
- ProductBuilder, attribute fixtures, FakeUnitOfWork, catalog-specific conftest
- Hypothesis strategies for EAV domain types

**Features from FEATURES.md:** P1 value object tests, P1 entity tests, P1 test data builders, domain event emission verification
**Avoids pitfall:** #1 (mock tests hiding real bugs -- domain tests verify real business logic), #7 (domain event accumulation -- verify event counts here)

### Phase 2: Command Handler Unit Tests

**Rationale:** 44 of 46 handlers untested -- this is the single largest coverage gap and the highest-risk area. With domain entities proven correct in Phase 1, handler tests focus purely on orchestration: does the handler call the right repos, enforce the right preconditions, and raise the right exceptions? Mock repos/UoW for speed.

**Delivers:**
- Unit tests for all 46 command handlers (~200-250 cases: happy path, FK-not-found, slug/code conflict, UoW commit verification, domain event emission)
- Priority handlers first: CreateProduct, ChangeProductStatus, GenerateSkuMatrix, AssignProductAttribute, bulk operations

**Features from FEATURES.md:** P1 command handler unit tests
**Avoids pitfall:** #1 (by testing orchestration only -- not pretending to test mapping), #7 (event emission assertions in every handler test)

### Phase 3: Repository + Integration Tests

**Rationale:** Repositories implement the Data Mapper pattern with complex mapping logic (`_sync_variants`, `_sku_to_orm`, Money VO decomposition, JSONB i18n). These must be tested against real PostgreSQL because SQLite misses PostgreSQL-specific behaviors (JSONB, recursive CTEs, FOR UPDATE). This phase catches the bugs that mocked handler tests cannot.

**Delivers:**
- Product repository integration tests (CRUD roundtrip, eager loading, variant/SKU sync, soft-delete filtering, optimistic locking)
- Category repository integration tests (tree operations, slug propagation, recursive CTE template inheritance)
- Brand, Attribute, AttributeValue, TemplateBinding repository tests
- N+1 query detection utility (assert_query_count context manager)
- Optimistic locking concurrency test
- Data integrity validation (schema constraint audit)

**Features from FEATURES.md:** P1 Product/Category repo tests, P2 optimistic locking, P1 data integrity validation
**Avoids pitfall:** #1 (Data Mapper bugs caught here), #3 (optimistic locking verified), #4 (EAV integrity tested with real DB), #5 (async lazy-load patterns established), #6 (soft-delete filtering verified)

### Phase 4: Query Handlers + API Contract Tests

**Rationale:** Query handlers bypass the domain layer and read directly from ORM. They need real data and real PostgreSQL to verify SQL generation, pagination, and read model mapping. API contract tests exercise the full HTTP stack. Both depend on Phases 1-3 for correctness at lower layers.

**Delivers:**
- Query handler integration tests for all 22 handlers (~60-80 cases: pagination, filtering, tree queries, completeness checker)
- API contract integration tests for all 11 routers (~30-40 cases: request validation, HTTP status codes, response schema, RBAC enforcement)
- Schemathesis fuzz testing against OpenAPI spec
- Product status FSM full lifecycle integration test
- Completeness checker integration test
- Storefront query soft-delete and caching correctness

**Features from FEATURES.md:** P2 query handler tests, P2 API contract tests, P2 FSM lifecycle test, P2 completeness checker
**Avoids pitfall:** #6 (soft-delete leaks in every query verified), #5 (async patterns already established in Phase 3)

### Phase 5: Entity God-Class Split + Cleanup

**Rationale:** The 2,220-line `entities.py` must be split for long-term maintainability, but ONLY after comprehensive tests exist to verify the refactoring. With 400+ tests in place from Phases 1-4, the split can be done safely with immediate feedback on any import breakage.

**Delivers:**
- Split `entities.py` into `entities/` package (brand.py, category.py, product.py, attribute.py, etc.)
- Shared helpers extracted to `entities/_helpers.py`
- Backward-compatible `entities/__init__.py` with re-exports
- Full test suite green after split

**Features from FEATURES.md:** P1 entity god-class split (sequenced last for safety)
**Avoids pitfall:** #2 (split AFTER tests exist, move one entity at a time, verify after each move)

### Phase Ordering Rationale

- **Phases 1-2 before 3-4:** Domain and handler tests are fast (no DB) and catch business logic bugs. They establish a safety net before touching infrastructure.
- **Phase 3 before 4:** Repository mapping correctness must be proven before API tests, which implicitly depend on repositories. A broken repository causes confusing failures in API tests.
- **Phase 5 last:** Refactoring without tests is dangerous. 400+ tests from Phases 1-4 provide the safety net for a safe structural change.
- **Value objects before entities, entities before handlers, handlers before repos:** Each layer validates the one below it. A Money bug caught in Phase 1 prevents cascading failures in Phases 2-4.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 1:** LOW risk -- domain entities are pure Python, well-documented patterns. May need research on hypothesis strategy design for the specific EAV attribute type system.
- **Phase 3:** MEDIUM risk -- the Product repository `_sync_variants()` and `_sync_skus_for_variant()` methods are complex 3-level reconciliation. Need to understand the exact mapping logic to write effective integration tests. The optimistic locking behavior with `version_id_col` on child entities needs investigation.
- **Phase 4:** LOW risk -- API contract testing with httpx AsyncClient is well-established. Schemathesis integration with FastAPI is documented.

Phases with standard patterns (skip research-phase):
- **Phase 2:** Command handler unit tests follow a mechanical pattern (mock repos, call handler, assert result/exception). The 46 handlers share the same DI structure.
- **Phase 5:** Entity file split is a standard Python module refactoring. The only complexity is circular imports, which is manageable with deferred imports.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All recommended tools verified on PyPI with 2025/2026 releases. Versions cross-checked against project's pyproject.toml. No speculative recommendations. |
| Features | HIGH | Feature list derived directly from codebase analysis (line counts, handler counts, entity inspection). Priority ordering based on dependency analysis, not guesswork. |
| Architecture | HIGH | Testing strategy mirrors the existing hexagonal/CQRS architecture. Layer boundaries and component responsibilities verified against codebase conventions. |
| Pitfalls | HIGH | Pitfalls identified from codebase-specific analysis (the _sync_variants mapping, the version field, the 2,220-line god-class) and validated against domain literature (EAV anti-patterns, async SQLAlchemy gotchas, DDD testing strategies). |

**Overall confidence:** HIGH

### Gaps to Address

- **Optimistic locking configuration:** The `version_id_col` configuration on the Product ORM model needs to be inspected during Phase 3 planning. If it is not configured, this is a bug to fix, not just a test to write.
- **Template drift behavior:** The research identified that `effective_template_id` is computed at category creation time but may not update when parent templates change. The actual behavior of `propagate_effective_template_id()` needs verification during Phase 3 implementation.
- **Supplier module dependency:** `CreateProductHandler` depends on `ISupplierQueryService.assert_supplier_active()`. A shared test stub for this cross-module dependency needs to be designed during Phase 2 planning.
- **Event clearing mechanism:** The exact lifecycle of `clear_domain_events()` in the UoW commit path needs verification. If events are cleared before Outbox persistence, they are lost silently.
- **Brand/Attribute repo test overlap:** Some repository tests already exist (partially for Brand). Phase 3 planning should audit existing coverage to avoid duplication.

## Sources

### Primary (HIGH confidence)
- Codebase analysis: `backend/src/modules/catalog/domain/entities.py` (2,220 lines, 9+ entity classes)
- Codebase analysis: `backend/src/modules/catalog/application/commands/` (46 command handlers, 44 untested)
- Codebase analysis: `backend/src/modules/catalog/application/queries/` (22 query handlers)
- Codebase analysis: `backend/tests/` (796 LOC existing catalog tests, 1.1% test-to-source ratio)
- Codebase analysis: `backend/src/modules/catalog/infrastructure/repositories/product.py` (Data Mapper implementation)
- PyPI package verification: hypothesis 6.151.5, schemathesis 4.13.0, dirty-equals 0.11, respx 0.22.0, pytest-randomly 3.16.0, pytest-timeout 2.4.0
- SQLAlchemy 2.1 event documentation: `after_cursor_execute` for query counting

### Secondary (MEDIUM confidence)
- [DDD Testing Strategy](http://www.taimila.com/blog/ddd-and-testing-strategy/) -- aggregate as unit of testing
- [Testing Strategies in DDD](https://dev.to/ruben_alapont/testing-strategies-in-domain-driven-design-ddd-2d93) -- unit/integration/E2E layering
- [Schemathesis + FastAPI guide](https://testdriven.io/blog/fastapi-hypothesis/) -- integration pattern
- [CQRS Testing Strategies](https://reintech.io/blog/testing-strategies-cqrs-applications) -- command/query test separation
- [Optimistic locking in SQLAlchemy](https://oneuptime.com/blog/post/2026-01-25-optimistic-locking-sqlalchemy/view) -- version_id_col behavior

### Tertiary (LOW confidence)
- EAV anti-pattern analysis (general domain literature, not codebase-specific): constraint enforcement limitations, orphan data risks
- Child entity version bumping discussion (GitHub issue, not official SQLAlchemy docs): version bump behavior for nested collection changes

---
*Research completed: 2026-03-28*
*Ready for roadmap: yes*
