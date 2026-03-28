---
phase: 01-test-infrastructure
verified: 2026-03-28T13:15:00Z
status: gaps_found
score: 3/5 must-haves verified
re_verification: false
gaps:
  - truth: "Running pytest with new dependencies (hypothesis, schemathesis, respx, dirty-equals, pytest-randomly, pytest-timeout) succeeds without import errors"
    status: failed
    reason: "Only 2 of 6 required dependencies are installed (hypothesis, pytest-timeout). schemathesis, respx, dirty-equals, and pytest-randomly are missing from pyproject.toml and cannot be imported."
    artifacts:
      - path: "backend/pyproject.toml"
        issue: "dev dependency group is missing schemathesis>=4.14.1, respx>=0.22.0, dirty-equals>=0.11, pytest-randomly>=4.0.1"
    missing:
      - "Add schemathesis>=4.14.1 to [dependency-groups] dev"
      - "Add respx>=0.22.0 to [dependency-groups] dev"
      - "Add dirty-equals>=0.11 to [dependency-groups] dev"
      - "Add pytest-randomly>=4.0.1 to [dependency-groups] dev"
      - "Run uv lock to update uv.lock"
  - truth: "A test can execute a command handler using FakeUnitOfWork without touching the database and verify repository interactions"
    status: failed
    reason: "FakeMediaAssetRepository is missing implementations for abstract methods bulk_update_sort_order and check_main_exists from IMediaAssetRepository. This causes FakeUnitOfWork.__init__() to raise TypeError, preventing all 11 FakeUoW smoke tests from running."
    artifacts:
      - path: "backend/tests/fakes/fake_catalog_repos.py"
        issue: "FakeMediaAssetRepository (line 517) does not implement bulk_update_sort_order and check_main_exists required by IMediaAssetRepository"
    missing:
      - "Implement async def bulk_update_sort_order(self, product_id, updates) -> None in FakeMediaAssetRepository (can raise NotImplementedError for now)"
      - "Implement async def check_main_exists(self, product_id, variant_id) -> bool in FakeMediaAssetRepository (can raise NotImplementedError for now)"
human_verification:
  - test: "Run integration test suite for query counter with database available"
    expected: "All 4 tests in test_query_counter_smoke.py pass (counts single query, counts multiple, fails on wrong count, excludes SAVEPOINTs)"
    why_human: "Requires running PostgreSQL via docker compose; cannot verify programmatically without live database"
---

# Phase 01: Test Infrastructure Verification Report

**Phase Goal:** All test tooling, factories, and utilities are in place so subsequent phases can focus purely on writing test cases
**Verified:** 2026-03-28T13:15:00Z
**Status:** gaps_found
**Re-verification:** No -- initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Running pytest with new dependencies (hypothesis, schemathesis, respx, dirty-equals, pytest-randomly, pytest-timeout) succeeds without import errors | FAILED | Only hypothesis and pytest-timeout are installed. schemathesis, respx, dirty-equals, and pytest-randomly are missing from pyproject.toml and fail to import. |
| 2 | A test can instantiate any catalog entity via a factory/builder with sensible defaults | VERIFIED | 8 builder files exist (brand, product, variant, sku, attribute, attribute_template, attribute_group, media_asset). All call entity .create() factory methods. 16 smoke tests pass in 1.16s. |
| 3 | A test can execute a command handler using FakeUnitOfWork without touching the database and verify repository interactions | FAILED | FakeUnitOfWork.__init__() raises TypeError because FakeMediaAssetRepository is missing abstract methods bulk_update_sort_order and check_main_exists. All 11 FakeUoW tests fail. |
| 4 | Hypothesis can generate valid EAV domain model instances and shrink failures to minimal examples | VERIFIED | 3-layer strategy hierarchy (primitives -> entities -> aggregates) exists. 10 smoke tests using @given pass in 4.48s. i18n_names uses safe alphabet (min_codepoint=65), valid_slugs uses segment-based regex. |
| 5 | A test can wrap a database session in the N+1 query detection context manager and assert exact query counts | VERIFIED (structural) | assert_query_count async context manager exists (86 lines), uses event.listen on sync_connection with after_cursor_execute, filters SAVEPOINT statements. Integration tests exist but require live database to verify. |

**Score:** 3/5 truths verified (2 failed, 1 needs human verification for full confirmation)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/pyproject.toml` | New test dependency group entries | PARTIAL | Only hypothesis and pytest-timeout added. Missing 4 dependencies. |
| `backend/pytest.ini` | timeout=30, timeout_method=thread | VERIFIED | Lines 39-40: timeout=30, timeout_method=thread |
| `backend/tests/factories/brand_builder.py` | BrandBuilder fluent builder | VERIFIED | 50 lines, class BrandBuilder, calls Brand.create() |
| `backend/tests/factories/product_builder.py` | ProductBuilder fluent builder | VERIFIED | 104 lines, class ProductBuilder, calls Product.create() |
| `backend/tests/factories/variant_builder.py` | ProductVariantBuilder | VERIFIED | 70 lines, class ProductVariantBuilder, calls ProductVariant.create() |
| `backend/tests/factories/sku_builder.py` | SKUBuilder via Product.add_sku() | VERIFIED | 93 lines, class SKUBuilder, calls product.add_sku() |
| `backend/tests/factories/attribute_builder.py` | AttributeBuilder, AttributeValueBuilder, ProductAttributeValueBuilder | VERIFIED | 250 lines, all 3 classes present |
| `backend/tests/factories/attribute_template_builder.py` | AttributeTemplateBuilder, TemplateAttributeBindingBuilder | VERIFIED | 132 lines, both classes present |
| `backend/tests/factories/attribute_group_builder.py` | AttributeGroupBuilder | VERIFIED | 51 lines, class present |
| `backend/tests/factories/media_asset_builder.py` | MediaAssetBuilder | VERIFIED | 89 lines, class present with as_external() method |
| `backend/tests/factories/orm_factories.py` | Polyfactory ORM factories for all catalog models | VERIFIED | 11 new catalog model factories (AttributeTemplate through ProductAttributeValue) |
| `backend/tests/fakes/fake_uow.py` | FakeUnitOfWork implementing IUnitOfWork | BROKEN | 185 lines, class exists, but fails to instantiate due to FakeMediaAssetRepository missing abstract methods |
| `backend/tests/fakes/fake_catalog_repos.py` | 10 fake catalog repositories | BROKEN | 701 lines, all 10 classes exist, but FakeMediaAssetRepository missing bulk_update_sort_order and check_main_exists |
| `backend/tests/factories/strategies/primitives.py` | Leaf Hypothesis strategies | VERIFIED | 208 lines, i18n_names/valid_slugs/money/behavior_flags present |
| `backend/tests/factories/strategies/entity_strategies.py` | Entity-level strategies | VERIFIED | 229 lines, brands/products/attributes/attribute_groups/root_categories present |
| `backend/tests/factories/strategies/aggregate_strategies.py` | Aggregate tree strategies | VERIFIED | 160 lines, product_trees/attribute_sets present |
| `backend/tests/utils/query_counter.py` | N+1 query detection context manager | VERIFIED | 86 lines, async context manager with SAVEPOINT filtering, uses sync_connection |
| `backend/tests/utils/catalog_query_baselines.py` | Query count baselines | VERIFIED | 45 lines, EXPECTED_COUNTS dict and get_expected_count helper |
| `backend/tests/unit/test_builders_smoke.py` | Builder smoke tests | VERIFIED | 253 lines, 16 tests, all pass |
| `backend/tests/unit/test_fake_uow_smoke.py` | FakeUoW smoke tests | BROKEN | 200 lines, 11 tests, ALL FAIL due to FakeUoW instantiation TypeError |
| `backend/tests/unit/test_strategies_smoke.py` | Hypothesis strategy smoke tests | VERIFIED | 114 lines, 10 tests using @given, all pass |
| `backend/tests/integration/test_query_counter_smoke.py` | Query counter integration tests | UNVERIFIED | 47 lines, 4 tests, requires database |
| `backend/tests/factories/strategies/__init__.py` | Re-exports from all layers | VERIFIED | 60 lines, exports primitives, entities, aggregates |
| `backend/tests/utils/__init__.py` | Re-exports assert_query_count | VERIFIED | 8 lines |
| `backend/tests/fakes/__init__.py` | Re-exports FakeUnitOfWork | VERIFIED | 4 lines |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| brand_builder.py | entities.py | Brand.create() | WIRED | Line 45: Brand.create(...) |
| product_builder.py | entities.py | Product.create() | WIRED | Line 94: Product.create(...) |
| sku_builder.py | entities.py | product.add_sku() | WIRED | Line 86: product.add_sku(...) |
| test_builders_smoke.py | *_builder.py | import and .build() | WIRED | 16 tests import and call .build() |
| entity_strategies.py | primitives.py | imports leaf strategies | WIRED | Line 26: from tests.factories.strategies.primitives import |
| aggregate_strategies.py | entity_strategies.py | imports entity strategies | WIRED | Line 23: from tests.factories.strategies.entity_strategies import |
| query_counter.py | sqlalchemy.event | after_cursor_execute listener | WIRED | Line 77: event.listen(raw_conn, "after_cursor_execute", ...) |
| fake_uow.py | IUnitOfWork | implements interface | WIRED | Line 74: class FakeUnitOfWork(IUnitOfWork) |
| fake_catalog_repos.py | interfaces.py | implements I*Repository | PARTIALLY BROKEN | 9/10 repos implement correctly; FakeMediaAssetRepository missing 2 abstract methods |

### Data-Flow Trace (Level 4)

Not applicable -- this phase produces test utilities, not components that render dynamic data.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Builder smoke tests pass | pytest tests/unit/test_builders_smoke.py | 16 passed in 1.16s | PASS |
| FakeUoW smoke tests pass | pytest tests/unit/test_fake_uow_smoke.py | 1 failed (TypeError on FakeMediaAssetRepository) | FAIL |
| Hypothesis strategy tests pass | pytest tests/unit/test_strategies_smoke.py | 10 passed in 4.48s | PASS |
| hypothesis importable | python -c "import hypothesis" | OK | PASS |
| schemathesis importable | python -c "import schemathesis" | No module named 'schemathesis' | FAIL |
| respx importable | python -c "import respx" | No module named 'respx' | FAIL |
| dirty_equals importable | python -c "import dirty_equals" | No module named 'dirty_equals' | FAIL |
| pytest_randomly importable | python -c "import pytest_randomly" | No module named 'pytest_randomly' | FAIL |
| pytest_timeout importable | python -c "import pytest_timeout" | OK | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| INFRA-01 | 01-01-PLAN | Install and configure new test dependencies (hypothesis, schemathesis, respx, dirty-equals, pytest-randomly, pytest-timeout) | PARTIAL | Only hypothesis and pytest-timeout installed. 4 of 6 dependencies missing. |
| INFRA-02 | 01-01-PLAN | Create test data builders/factories for all catalog entities | SATISFIED | 8 builder files covering all entities, 11 ORM factories, 16 smoke tests pass |
| INFRA-03 | 01-02-PLAN | Build FakeUnitOfWork for command handler unit test isolation | BLOCKED | FakeUoW exists but cannot instantiate due to FakeMediaAssetRepository missing abstract methods |
| INFRA-04 | 01-03-PLAN | Build hypothesis strategies for attrs-based domain models | SATISFIED | 3-layer composable strategy hierarchy, 10 smoke tests pass |
| INFRA-05 | 01-03-PLAN | Implement N+1 query detection via SQLAlchemy after_cursor_execute event context manager | SATISFIED | async context manager with SAVEPOINT filtering. Structural verification passes; requires DB for runtime verification. |

No orphaned requirements found -- all 5 INFRA requirements are claimed by plans and accounted for.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| backend/tests/fakes/fake_catalog_repos.py | 185, 192, 244, 622, 678, 685, 699 | NotImplementedError stubs for less-common methods | Info | Intentional per plan -- to be filled when phases 4-6 need them. Not blockers. |
| backend/tests/fakes/fake_catalog_repos.py | 517 | FakeMediaAssetRepository missing abstract methods | Blocker | Prevents FakeUoW instantiation entirely. TypeError on any attempt to create FakeUnitOfWork. |
| backend/tests/utils/catalog_query_baselines.py | 9-24 | EXPECTED_COUNTS has None values (TBD) | Info | Intentional -- to be filled in Phases 7-8. get_expected_count raises ValueError for None values. |

### Human Verification Required

### 1. Query Counter Integration Tests

**Test:** Run `cd backend && uv run pytest tests/integration/test_query_counter_smoke.py -x -v --no-cov --timeout=30` with PostgreSQL available (docker compose up -d)
**Expected:** All 4 tests pass: single query counted, multiple queries counted, wrong count assertion raised, SAVEPOINT statements excluded
**Why human:** Requires running PostgreSQL database via docker compose; cannot verify programmatically in this environment

### Gaps Summary

Two gaps block full phase goal achievement:

**Gap 1: Missing test dependencies (INFRA-01 partial failure)**
Four of six required test dependencies were never installed: schemathesis, respx, dirty-equals, and pytest-randomly. These are listed in pyproject.toml's PLAN but were not added to the actual dev dependency group. The SUMMARY for Plan 01 claimed all six were installed, but the codebase evidence contradicts this. While these four packages are not consumed by any Phase 1 artifacts directly (they are used in later phases), the Success Criterion explicitly requires all six to be importable.

**Gap 2: FakeMediaAssetRepository missing abstract methods (INFRA-03 failure)**
The `IMediaAssetRepository` interface defines `bulk_update_sort_order` and `check_main_exists` as abstract methods. `FakeMediaAssetRepository` does not implement either. This causes `FakeUnitOfWork.__init__()` to raise `TypeError: Can't instantiate abstract class FakeMediaAssetRepository without an implementation for abstract methods 'bulk_update_sort_order', 'check_main_exists'`. All 11 FakeUoW smoke tests fail. This is likely caused by the interface being updated (methods added) after Plan 02 was executed, or the Plan 02 executor working against a different version of the interface. The fix is straightforward: add NotImplementedError stubs for both methods.

**Root cause relationship:** These two gaps are independent -- different plans, different artifacts, different causes.

---

_Verified: 2026-03-28T13:15:00Z_
_Verifier: Claude (gsd-verifier)_
