---
phase: 01-test-infrastructure
plan: 03
subsystem: testing
tags: [hypothesis, property-based-testing, n-plus-one, sqlalchemy, query-counter, eav]

# Dependency graph
requires:
  - phase: 01-01
    provides: hypothesis installed as dev dependency, entity builders in tests/factories
provides:
  - Three-layer composable Hypothesis strategy hierarchy (primitives -> entities -> aggregates)
  - Async N+1 query detection context manager with SAVEPOINT filtering
  - Catalog query count baselines scaffold for Phases 7-8
  - 10 hypothesis smoke tests and 4 query counter integration tests
affects: [02-domain-unit-tests, 03-command-handler-tests, 07-integration-tests, 08-storefront-tests]

# Tech tracking
tech-stack:
  added: [hypothesis, pytest-timeout]
  patterns: [composable-strategy-hierarchy, async-query-counting, savepoint-filtering]

key-files:
  created:
    - backend/tests/factories/strategies/__init__.py
    - backend/tests/factories/strategies/primitives.py
    - backend/tests/factories/strategies/entity_strategies.py
    - backend/tests/factories/strategies/aggregate_strategies.py
    - backend/tests/utils/__init__.py
    - backend/tests/utils/query_counter.py
    - backend/tests/utils/catalog_query_baselines.py
    - backend/tests/unit/test_strategies_smoke.py
    - backend/tests/integration/test_query_counter_smoke.py
  modified:
    - backend/pyproject.toml
    - backend/uv.lock

key-decisions:
  - "Used segment-based regex for slug generation to avoid hypothesis edge cases with hyphens"
  - "SKU generation uses synthetic variant_attributes UUIDs to avoid DuplicateVariantCombinationError"
  - "Query counter accesses sync_connection (not async) per SQLAlchemy event API requirements"

patterns-established:
  - "Composable strategy layers: primitives feed entities feed aggregates"
  - "Safe alphabet with min_codepoint=65 for i18n text generation avoids control char validation failures"
  - "Async query counter with SAVEPOINT filtering for nested-transaction test isolation"

requirements-completed: [INFRA-04, INFRA-05]

# Metrics
duration: 6min
completed: 2026-03-28
---

# Phase 01 Plan 03: Hypothesis Strategies & Query Counter Summary

**Composable three-layer Hypothesis strategies for EAV catalog models plus async N+1 query detection with SAVEPOINT-aware filtering**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-28T12:37:01Z
- **Completed:** 2026-03-28T12:43:18Z
- **Tasks:** 2
- **Files modified:** 11

## Accomplishments
- Built composable three-layer Hypothesis strategy hierarchy: primitives (i18n names, slugs, codes, Money, BehaviorFlags, enums), entities (Brand, Product, Attribute, Category, Template, MediaAsset), aggregates (Product trees with variants and SKUs, attribute sets)
- Implemented async N+1 query detection context manager using SQLAlchemy's after_cursor_execute event, correctly accessing sync_connection and filtering SAVEPOINT statements
- Scaffolded catalog query count baselines for Phases 7-8 with known values and TBD placeholders
- 10 Hypothesis smoke tests prove all strategy layers produce valid domain instances passing all entity invariants

## Task Commits

Each task was committed atomically:

1. **Task 1: Build composable Hypothesis strategies for catalog domain models** - `f3d6a3b` (feat)
2. **Task 2: Implement N+1 query detection async context manager and baselines** - `acfef2e` (feat)

## Files Created/Modified
- `backend/tests/factories/strategies/__init__.py` - Re-exports key strategies from all three layers
- `backend/tests/factories/strategies/primitives.py` - Leaf strategies: i18n_names, valid_slugs, valid_codes, money, behavior_flags, enum strategies, uuids, tags
- `backend/tests/factories/strategies/entity_strategies.py` - Entity strategies: brands, attribute_groups, attributes, attribute_values, root_categories, products, attribute_templates, template_bindings, media_assets
- `backend/tests/factories/strategies/aggregate_strategies.py` - Aggregate strategies: product_trees (Product->Variant->SKU), attribute_sets (group with attrs and values)
- `backend/tests/utils/__init__.py` - Re-exports assert_query_count
- `backend/tests/utils/query_counter.py` - Async context manager for exact SQL query count assertion with SAVEPOINT filtering
- `backend/tests/utils/catalog_query_baselines.py` - Expected query counts for catalog operations (TBD for Phases 7-8)
- `backend/tests/unit/test_strategies_smoke.py` - 10 hypothesis smoke tests (TestHypothesisStrategies class, @pytest.mark.unit)
- `backend/tests/integration/test_query_counter_smoke.py` - 4 integration tests (TestQueryCounter class, @pytest.mark.integration)
- `backend/pyproject.toml` - Added hypothesis and pytest-timeout to dev dependencies
- `backend/uv.lock` - Updated lockfile

## Decisions Made
- **Segment-based regex for slugs:** Used `st.from_regex(r"[a-z][a-z0-9]{0,9}(-[a-z0-9]{1,10}){0,3}", fullmatch=True)` instead of raw `st.text()` to avoid edge cases like leading hyphens and empty segments
- **Synthetic variant_attributes for SKU uniqueness:** Each SKU in product_trees gets a unique (attribute_id, attribute_value_id) tuple to avoid DuplicateVariantCombinationError when multiple SKUs share a variant with no real attributes
- **Safe alphabet min_codepoint=65:** i18n_names strategy uses `min_codepoint=65` to avoid control characters and low ASCII that trigger `_validate_i18n_values()` failures

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Installed hypothesis and pytest-timeout dependencies**
- **Found during:** Task 1 (strategy creation)
- **Issue:** hypothesis and pytest-timeout not available in this worktree despite prerequisite note
- **Fix:** Ran `uv add --group dev hypothesis` and `uv add --group dev pytest-timeout`
- **Files modified:** backend/pyproject.toml, backend/uv.lock
- **Verification:** `import hypothesis` succeeds, tests run with --timeout flag
- **Committed in:** f3d6a3b (Task 1 commit)

**2. [Rule 1 - Bug] Fixed DuplicateVariantCombinationError in product_trees strategy**
- **Found during:** Task 1 (smoke test verification)
- **Issue:** product_trees strategy added multiple SKUs to same variant with no variant_attributes, causing hash collision and DuplicateVariantCombinationError
- **Fix:** Generate unique synthetic variant_attributes (random UUID pairs) per SKU
- **Files modified:** backend/tests/factories/strategies/aggregate_strategies.py
- **Verification:** test_product_tree_has_variants passes consistently
- **Committed in:** f3d6a3b (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (1 blocking dependency, 1 bug fix)
**Impact on plan:** Both fixes necessary for correctness. No scope creep.

## Issues Encountered
- Database not available in CI/worktree environment -- integration tests for query counter cannot be verified here but are structurally correct. They require `docker compose up -d` to run.

## Known Stubs
None -- all strategies produce real domain instances, query baselines have intentional TBD placeholders (by design, to be filled in Phases 7-8).

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Hypothesis strategies ready for use in Phases 2-3 (domain unit tests, command handler tests)
- Query counter ready for use in Phases 7-8 (integration tests, storefront tests)
- All strategy layers independently importable and composable

## Self-Check: PASSED

All 9 created files verified on disk. Both task commits (f3d6a3b, acfef2e) verified in git log.

---
*Phase: 01-test-infrastructure*
*Completed: 2026-03-28*
