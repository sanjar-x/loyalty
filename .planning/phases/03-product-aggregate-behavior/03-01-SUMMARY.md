---
phase: 03-product-aggregate-behavior
plan: 01
subsystem: testing
tags: [pytest, product-fsm, variant-hash, soft-delete, domain-testing, attrs]

# Dependency graph
requires:
  - phase: 01-entity-value-object-tests
    provides: fluent builders (ProductBuilder, SKUBuilder, VariantBuilder)
provides:
  - 37 unit tests proving Product aggregate FSM, variant hash, and soft-delete correctness
  - TestProductFSMValid, TestProductFSMInvalid, TestProductFSMReadiness test classes
  - TestVariantHashUniqueness and TestSoftDeleteCascade test classes
  - Helper functions (_advance_to, _product_with_priced_sku) reusable by future tests
affects: [03-02, 04-command-handler-tests, 05-query-handler-tests]

# Tech tracking
tech-stack:
  added: []
  patterns: [parametrized-invalid-fsm-transitions, fsm-path-walker-helper, priced-sku-helper]

key-files:
  created:
    - backend/tests/unit/modules/catalog/domain/__init__.py
    - backend/tests/unit/modules/catalog/domain/test_product_aggregate.py
  modified: []

key-decisions:
  - "Used parametrized tests for 13 invalid FSM transitions instead of individual methods"
  - "Created reusable _advance_to() helper with pre-computed FSM paths for DRY test setup"
  - "Cherry-picked builder files from Phase 01 parallel agent (not yet on dev branch)"

patterns-established:
  - "FSM path walker: _advance_to(product, target_status) walks any product to target state"
  - "Priced SKU helper: _ensure_priced_sku() adds price-bearing SKU when readiness checks require it"
  - "Parametrized invalid transitions: compute INVALID_TRANSITIONS from VALID_TRANSITIONS complement"

requirements-completed: [DOM-02, DOM-03, DOM-04]

# Metrics
duration: 5min
completed: 2026-03-28
---

# Phase 03 Plan 01: Product Aggregate Behavior Tests Summary

**37 unit tests proving Product FSM transitions (7 valid, 13 invalid, 4 readiness), variant hash uniqueness (5 tests), and soft-delete cascade (6 tests) with all passing**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-28T14:24:26Z
- **Completed:** 2026-03-28T14:29:09Z
- **Tasks:** 1
- **Files modified:** 2 created

## Accomplishments
- All 7 valid FSM transitions verified (DRAFT->ENRICHING, ENRICHING->DRAFT, ENRICHING->READY_FOR_REVIEW, READY_FOR_REVIEW->ENRICHING, READY_FOR_REVIEW->PUBLISHED, PUBLISHED->ARCHIVED, ARCHIVED->DRAFT)
- All 13 invalid FSM transitions parametrized and verified to raise InvalidStatusTransitionError
- Readiness checks proven: active SKU required for READY_FOR_REVIEW, priced SKU required for PUBLISHED
- published_at set only on first PUBLISHED transition and retained through ARCHIVED->DRAFT->...->PUBLISHED cycle
- __setattr__ guard prevents direct product.status assignment (raises AttributeError)
- Variant hash deterministic regardless of attribute order; different variant_ids produce different hashes
- Duplicate variant combinations rejected; soft-deleted SKUs excluded from uniqueness checks
- Soft-delete cascades through Product->Variant->SKU hierarchy; idempotent; published products cannot be deleted

## Task Commits

Each task was committed atomically:

1. **Task 1: Create test file with FSM, variant hash, and soft-delete cascade tests** - `1717c74` (test)

## Files Created/Modified
- `backend/tests/unit/modules/catalog/domain/__init__.py` - pytest discovery marker (empty)
- `backend/tests/unit/modules/catalog/domain/test_product_aggregate.py` - 37 tests across 5 classes covering FSM, hash, and cascade behaviors
- `backend/tests/factories/product_builder.py` - Fluent builder for Product aggregate (dependency from Phase 01)
- `backend/tests/factories/sku_builder.py` - Fluent builder for SKU via Product.add_sku() (dependency from Phase 01)
- `backend/tests/factories/variant_builder.py` - Fluent builder for ProductVariant (dependency from Phase 01)

## Decisions Made
- Used parametrized tests for 13 invalid FSM transitions instead of individual test methods -- reduces duplication and auto-covers new transitions if FSM changes
- Created _advance_to() helper with pre-computed path dictionaries for DRY test setup -- avoids repeating multi-step transition sequences
- Included builder files (product_builder.py, sku_builder.py, variant_builder.py) from Phase 01 parallel agent as they were not yet merged to dev branch

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Builder files missing from worktree**
- **Found during:** Task 1 (test execution)
- **Issue:** product_builder.py, sku_builder.py, variant_builder.py not present in worktree (created by Phase 01 parallel agent, not yet on dev branch)
- **Fix:** Cherry-picked commit 4d6e650 from Phase 01 agent to bring builder files into worktree
- **Files modified:** backend/tests/factories/product_builder.py, sku_builder.py, variant_builder.py
- **Verification:** Tests import successfully, all 37 pass
- **Committed in:** 1717c74 (part of task commit)

**2. [Rule 3 - Blocking] .env file missing in worktree**
- **Found during:** Task 1 (test execution)
- **Issue:** conftest.py imports Settings which requires environment variables; .env file not present in worktree
- **Fix:** Copied .env from main backend directory to worktree
- **Files modified:** backend/.env (copied, not committed -- gitignored)
- **Verification:** pytest runs successfully after .env copy

---

**Total deviations:** 2 auto-fixed (2 blocking)
**Impact on plan:** Both fixes necessary for test execution in parallel worktree environment. No scope creep.

## Issues Encountered
None beyond the blocking issues documented as deviations above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Product aggregate behavioral invariants are proven correct
- Helper functions (_advance_to, _product_with_priced_sku) ready for reuse in Plan 03-02 (domain event emission tests)
- Foundation established for command handler tests in Phases 4-6

## Known Stubs
None - all test assertions are wired to real domain logic.

## Self-Check: PASSED

- FOUND: backend/tests/unit/modules/catalog/domain/__init__.py
- FOUND: backend/tests/unit/modules/catalog/domain/test_product_aggregate.py
- FOUND: commit 1717c74

---
*Phase: 03-product-aggregate-behavior*
*Completed: 2026-03-28*
