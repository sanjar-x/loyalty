---
phase: 02-value-objects-entity-foundations
plan: 02
subsystem: testing
tags: [pytest, domain-entities, product-aggregate, sku, variant, media-asset, ddd]

# Dependency graph
requires:
  - phase: 01-test-infrastructure
    provides: "ProductBuilder, SKUBuilder, ProductVariantBuilder, MediaAssetBuilder fluent builders"
provides:
  - "94 unit tests for Product aggregate (create, update, guard, soft-delete, variant/SKU management, variant hash)"
  - "Unit tests for ProductVariant standalone (create, update, soft-delete)"
  - "Unit tests for SKU construction validation and update cross-field checks"
  - "Unit tests for MediaAsset create factory with string-to-enum conversion"
affects: [03-product-aggregate-behavior, entity-refactoring]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "_i18n() helper for bilingual test data (en+ru)"
    - "clear_domain_events() before testing subsequent event emission"
    - "SKUBuilder().for_product(p) pattern for SKU construction through aggregate"

key-files:
  created:
    - backend/tests/unit/modules/catalog/domain/test_product.py
    - backend/tests/unit/modules/catalog/domain/test_variant.py
    - backend/tests/unit/modules/catalog/domain/test_sku.py
    - backend/tests/unit/modules/catalog/domain/test_media_asset.py
  modified: []

key-decisions:
  - "Product.update() returns None (not old_slug) -- plan interface was inaccurate, tests adapted to actual implementation"
  - "Pre-existing test_category_effective_family failure left untouched (out-of-scope, tracked for 02-01 plan)"

patterns-established:
  - "clear_domain_events() before each event assertion block to avoid conflation with ProductCreatedEvent"
  - "Use product.add_sku(variant_id, ...) for SKU creation (SKU has no standalone create())"
  - "FSM walk pattern: DRAFT->ENRICHING->READY_FOR_REVIEW->PUBLISHED requires priced active SKU"

requirements-completed: [DOM-01]

# Metrics
duration: 6min
completed: 2026-03-28
---

# Phase 02 Plan 02: Product Aggregate and Entity Tests Summary

**94 unit tests covering Product aggregate root (create, update, guard, soft-delete, variant/SKU lifecycle, variant hash), ProductVariant (create, update, soft-delete), SKU (construction validation, update, soft-delete), and MediaAsset (create factory with enum conversion)**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-28T14:25:17Z
- **Completed:** 2026-03-28T14:31:19Z
- **Tasks:** 2
- **Files created:** 4

## Accomplishments
- 48 Product aggregate tests proving create, update, guard, soft-delete cascading, variant/SKU management, and variant hash computation
- 19 ProductVariant tests covering create factory, update with price/currency interaction, and soft-delete cascading to SKUs
- 16 SKU tests proving construction validation (__attrs_post_init__), update with cross-field price/compare_at revalidation, and soft-delete
- 11 MediaAsset tests covering create factory, string-to-enum conversion, external URL requirement

## Task Commits

Each task was committed atomically:

1. **Task 1: Product aggregate tests** - `045091b` (test)
2. **Task 2: ProductVariant, SKU, and MediaAsset entity tests** - `0cf8a75` (test)

## Files Created/Modified
- `backend/tests/unit/modules/catalog/domain/test_product.py` - Product aggregate root unit tests (48 tests, 7 test classes)
- `backend/tests/unit/modules/catalog/domain/test_variant.py` - ProductVariant entity unit tests (19 tests, 3 test classes)
- `backend/tests/unit/modules/catalog/domain/test_sku.py` - SKU entity unit tests (16 tests, 3 test classes)
- `backend/tests/unit/modules/catalog/domain/test_media_asset.py` - MediaAsset entity unit tests (11 tests, 1 test class)

## Decisions Made
- Product.update() returns None (not old_slug as plan interface stated) -- adapted tests to actual implementation
- Pre-existing failing test in test_category_effective_family.py left untouched (out of scope for this plan)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Worktree missing builder files from Phase 1**
- **Found during:** Task 1 setup
- **Issue:** Worktree branch was behind dev; builder files (ProductBuilder, SKUBuilder, etc.) created in Phase 1 were not present
- **Fix:** Merged dev branch into worktree (fast-forward) to get all Phase 1 artifacts
- **Files affected:** All builder files from tests/factories/
- **Verification:** Builders imported successfully, all tests pass

**2. [Rule 3 - Blocking] Worktree missing .env file for test conftest**
- **Found during:** Task 1 test execution
- **Issue:** conftest.py imports Settings which requires env vars; worktree had no .env
- **Fix:** Copied .env from main repo to worktree backend directory
- **Verification:** pytest runs successfully

---

**Total deviations:** 2 auto-fixed (both blocking infrastructure issues)
**Impact on plan:** Both fixes were necessary worktree setup -- no scope change to actual test content.

## Issues Encountered
- Plan interface documented Product.update() as returning old_slug (str | None) but actual implementation returns None -- adapted test to verify field mutation instead of return value

## Known Stubs
None -- all tests exercise real domain entity behavior.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Product aggregate test coverage established, ready for Phase 3 FSM/behavior tests
- All 94 new tests pass; pre-existing test_category_effective_family failure is tracked for 02-01 plan

---
*Phase: 02-value-objects-entity-foundations*
*Completed: 2026-03-28*

## Self-Check: PASSED
- All 5 files found on disk
- Both task commits (045091b, 0cf8a75) found in git log
