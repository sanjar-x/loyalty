---
phase: 01-test-infrastructure
verified: 2026-03-28T18:45:00Z
status: human_needed
score: 5/5 must-haves verified
re_verification:
  previous_status: gaps_found
  previous_score: 3/5
  gaps_closed:
    - "Running pytest with new dependencies (hypothesis, schemathesis, respx, dirty-equals, pytest-randomly, pytest-timeout) succeeds without import errors"
    - "A test can execute a command handler using FakeUnitOfWork without touching the database and verify repository interactions"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Run integration test suite for query counter with database available"
    expected: "All 4 tests in test_query_counter_smoke.py pass (counts single query, counts multiple, fails on wrong count, excludes SAVEPOINTs)"
    why_human: "Requires running PostgreSQL via docker compose; cannot verify programmatically without live database"
---

# Phase 01: Test Infrastructure Verification Report

**Phase Goal:** All test tooling, factories, and utilities are in place so subsequent phases can focus purely on writing test cases
**Verified:** 2026-03-28T18:45:00Z
**Status:** human_needed
**Re-verification:** Yes -- after gap closure (previous status: gaps_found, score: 3/5)

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Running pytest with new dependencies (hypothesis, schemathesis, respx, dirty-equals, pytest-randomly, pytest-timeout) succeeds without import errors | VERIFIED | All 6 deps present in pyproject.toml (lines 39-53). All 6 import successfully via `uv run python -c "import ..."`. pytest plugin list shows all 6 loaded. |
| 2 | A test can instantiate any catalog entity via a factory/builder with sensible defaults | VERIFIED | 8 builder files exist. 16 smoke tests pass in 0.58s (regression OK). |
| 3 | A test can execute a command handler using FakeUnitOfWork without touching the database and verify repository interactions | VERIFIED | FakeMediaAssetRepository now implements bulk_update_sort_order (line 580) and check_main_exists (line 589). FakeUnitOfWork instantiation succeeds. All 11 FakeUoW smoke tests pass in 0.50s. |
| 4 | Hypothesis can generate valid EAV domain model instances and shrink failures to minimal examples | VERIFIED | 3-layer strategy hierarchy exists. 10 smoke tests using @given pass in 2.17s (regression OK). |
| 5 | A test can wrap a database session in the N+1 query detection context manager and assert exact query counts | VERIFIED (structural) | assert_query_count async context manager importable and exists (86 lines). Integration tests exist (47 lines, 4 tests) but require live database for runtime verification. |

**Score:** 5/5 truths verified (1 needs human verification for full runtime confirmation)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/pyproject.toml` | New test dependency group entries | VERIFIED | All 6 deps present: hypothesis>=6.151.9, schemathesis>=4.14.1, respx>=0.22.0, dirty-equals>=0.11, pytest-randomly>=4.0.1, pytest-timeout>=2.4.0 |
| `backend/pytest.ini` | timeout=30, timeout_method=thread | VERIFIED | Lines 39-40: timeout=30, timeout_method=thread |
| `backend/tests/factories/brand_builder.py` | BrandBuilder fluent builder | VERIFIED | class BrandBuilder, calls Brand.create() |
| `backend/tests/factories/product_builder.py` | ProductBuilder fluent builder | VERIFIED | class ProductBuilder, calls Product.create() |
| `backend/tests/factories/variant_builder.py` | ProductVariantBuilder | VERIFIED | class ProductVariantBuilder, calls ProductVariant.create() |
| `backend/tests/factories/sku_builder.py` | SKUBuilder via Product.add_sku() | VERIFIED | class SKUBuilder, calls product.add_sku() |
| `backend/tests/factories/attribute_builder.py` | AttributeBuilder, AttributeValueBuilder, ProductAttributeValueBuilder | VERIFIED | All 3 classes present |
| `backend/tests/factories/attribute_template_builder.py` | AttributeTemplateBuilder, TemplateAttributeBindingBuilder | VERIFIED | Both classes present |
| `backend/tests/factories/attribute_group_builder.py` | AttributeGroupBuilder | VERIFIED | Class present |
| `backend/tests/factories/media_asset_builder.py` | MediaAssetBuilder | VERIFIED | Class present with as_external() method |
| `backend/tests/factories/orm_factories.py` | Polyfactory ORM factories for all catalog models | VERIFIED | 11 new catalog model factories |
| `backend/tests/fakes/fake_uow.py` | FakeUnitOfWork implementing IUnitOfWork | VERIFIED | Instantiation succeeds, 11 smoke tests pass |
| `backend/tests/fakes/fake_catalog_repos.py` | 10 fake catalog repositories | VERIFIED | All 10 classes exist, all abstract methods satisfied, FakeMediaAssetRepository now has bulk_update_sort_order and check_main_exists |
| `backend/tests/factories/strategies/primitives.py` | Leaf Hypothesis strategies | VERIFIED | i18n_names/valid_slugs/money/behavior_flags present |
| `backend/tests/factories/strategies/entity_strategies.py` | Entity-level strategies | VERIFIED | brands/products/attributes/attribute_groups/root_categories present |
| `backend/tests/factories/strategies/aggregate_strategies.py` | Aggregate tree strategies | VERIFIED | product_trees/attribute_sets present |
| `backend/tests/utils/query_counter.py` | N+1 query detection context manager | VERIFIED | 86 lines, async context manager with SAVEPOINT filtering |
| `backend/tests/utils/catalog_query_baselines.py` | Query count baselines | VERIFIED | EXPECTED_COUNTS dict (9 keys) and get_expected_count helper |
| `backend/tests/unit/test_builders_smoke.py` | Builder smoke tests | VERIFIED | 16 tests, all pass |
| `backend/tests/unit/test_fake_uow_smoke.py` | FakeUoW smoke tests | VERIFIED | 11 tests, all pass (previously all 11 failed) |
| `backend/tests/unit/test_strategies_smoke.py` | Hypothesis strategy smoke tests | VERIFIED | 10 tests using @given, all pass |
| `backend/tests/integration/test_query_counter_smoke.py` | Query counter integration tests | UNVERIFIED | 47 lines, 4 tests, requires database |
| `backend/tests/factories/strategies/__init__.py` | Re-exports from all layers | VERIFIED | Exports primitives, entities, aggregates |
| `backend/tests/utils/__init__.py` | Re-exports assert_query_count | VERIFIED | Importable |
| `backend/tests/fakes/__init__.py` | Re-exports FakeUnitOfWork | VERIFIED | Importable |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| brand_builder.py | entities.py | Brand.create() | WIRED | Brand.create(...) call present |
| product_builder.py | entities.py | Product.create() | WIRED | Product.create(...) call present |
| sku_builder.py | entities.py | product.add_sku() | WIRED | product.add_sku(...) call present |
| test_builders_smoke.py | *_builder.py | import and .build() | WIRED | 16 tests import and call .build() |
| entity_strategies.py | primitives.py | imports leaf strategies | WIRED | from tests.factories.strategies.primitives import |
| aggregate_strategies.py | entity_strategies.py | imports entity strategies | WIRED | from tests.factories.strategies.entity_strategies import |
| query_counter.py | sqlalchemy.event | after_cursor_execute listener | WIRED | event.listen(raw_conn, "after_cursor_execute", ...) |
| fake_uow.py | IUnitOfWork | implements interface | WIRED | class FakeUnitOfWork(IUnitOfWork) |
| fake_catalog_repos.py | interfaces.py | implements I*Repository | WIRED | All 10 repos now implement all required abstract methods |

### Data-Flow Trace (Level 4)

Not applicable -- this phase produces test utilities, not components that render dynamic data.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Builder smoke tests pass | pytest tests/unit/test_builders_smoke.py | 16 passed in 0.58s | PASS |
| FakeUoW smoke tests pass | pytest tests/unit/test_fake_uow_smoke.py | 11 passed in 0.50s | PASS |
| Hypothesis strategy tests pass | pytest tests/unit/test_strategies_smoke.py | 10 passed in 2.17s | PASS |
| hypothesis importable | uv run python -c "import hypothesis" | OK | PASS |
| schemathesis importable | uv run python -c "import schemathesis" | OK | PASS |
| respx importable | uv run python -c "import respx" | OK | PASS |
| dirty_equals importable | uv run python -c "import dirty_equals" | OK | PASS |
| pytest_randomly importable | uv run python -c "import pytest_randomly" | OK | PASS |
| pytest_timeout importable | uv run python -c "import pytest_timeout" | OK | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| INFRA-01 | 01-01-PLAN | Install and configure new test dependencies (hypothesis, schemathesis, respx, dirty-equals, pytest-randomly, pytest-timeout) | SATISFIED | All 6 deps in pyproject.toml with correct version constraints. All 6 importable. pytest-timeout configured at 30s with thread method. |
| INFRA-02 | 01-01-PLAN | Create test data builders/factories for all catalog entities | SATISFIED | 8 builder files covering all entities, 11 ORM factories, 16 smoke tests pass |
| INFRA-03 | 01-02-PLAN | Build FakeUnitOfWork for command handler unit test isolation | SATISFIED | FakeUoW instantiates successfully, 11 smoke tests pass including event collection, aggregate deduplication, cross-repo wiring |
| INFRA-04 | 01-03-PLAN | Build hypothesis strategies for attrs-based domain models | SATISFIED | 3-layer composable strategy hierarchy, 10 smoke tests pass |
| INFRA-05 | 01-03-PLAN | Implement N+1 query detection via SQLAlchemy after_cursor_execute event context manager | SATISFIED | async context manager with SAVEPOINT filtering. Structural verification passes; integration tests require DB for runtime verification. |

No orphaned requirements found -- all 5 INFRA requirements are claimed by plans and accounted for. All 5 are now SATISFIED.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| backend/tests/fakes/fake_catalog_repos.py | 185, 192, 244, 585, 595, 641, 697, 704, 718 | NotImplementedError stubs for less-common methods | Info | Intentional per plan -- to be filled when phases 4-6 need them. Not blockers. All abstract methods are satisfied. |
| backend/tests/utils/catalog_query_baselines.py | 9-24 | EXPECTED_COUNTS has None values (TBD) | Info | Intentional -- to be filled in Phases 7-8. get_expected_count raises ValueError for None values. |

No blocker anti-patterns found.

### Human Verification Required

### 1. Query Counter Integration Tests

**Test:** Run `cd backend && uv run pytest tests/integration/test_query_counter_smoke.py -x -v --no-cov --timeout=30` with PostgreSQL available (docker compose up -d)
**Expected:** All 4 tests pass: single query counted, multiple queries counted, wrong count assertion raised, SAVEPOINT statements excluded
**Why human:** Requires running PostgreSQL database via docker compose; cannot verify programmatically in this environment

### Gap Closure Summary

Both gaps from the initial verification have been resolved:

**Gap 1 (CLOSED): Missing test dependencies (INFRA-01)**
Previously, only hypothesis and pytest-timeout were installed. Now all 6 dependencies (hypothesis, schemathesis, respx, dirty-equals, pytest-randomly, pytest-timeout) are present in pyproject.toml with correct version constraints and all import successfully via `uv run`.

**Gap 2 (CLOSED): FakeMediaAssetRepository missing abstract methods (INFRA-03)**
FakeMediaAssetRepository now implements `bulk_update_sort_order` (line 580) and `check_main_exists` (line 589) as NotImplementedError stubs. FakeUnitOfWork instantiates without errors. All 11 FakeUoW smoke tests now pass (previously all 11 failed with TypeError).

**Regression check:** All 3 previously-passing test suites continue to pass (16 builder tests, 10 hypothesis tests, all module re-exports functional). No regressions detected.

---

_Verified: 2026-03-28T18:45:00Z_
_Verifier: Claude (gsd-verifier)_
