---
phase: 04-brand-category-attribute-command-handlers
plan: 03
subsystem: testing
tags: [pytest, fake-uow, command-handlers, attribute-template, attribute, binding, asyncmock]

# Dependency graph
requires:
  - phase: 04-brand-category-attribute-command-handlers (plan 01)
    provides: "Fake repo methods (get_bindings_for_templates, bulk_update_sort_order, get_template_ids_for_attribute, get_category_ids_by_template_ids, has_category_references), cross-repo _category_store wiring, test directory setup"
provides:
  - "55 unit tests for 12 attribute/template/binding command handlers"
  - "Complete CMD-03 requirement coverage"
affects: [05-product-command-handlers, 07-integration-tests]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "ICacheService mocked with AsyncMock for cache-invalidating handlers"
    - "_provided_fields frozenset required on all Update commands"
    - "TemplateAttributeBindingBuilder for binding pre-seeding"

key-files:
  created:
    - "backend/tests/unit/modules/catalog/application/commands/test_attribute_handlers.py"
  modified: []

key-decisions:
  - "Used _store instead of items property for repository assertions (concrete fake repos extend interface ABCs directly, not FakeRepository base)"
  - "Monkeypatched has_product_attribute_values for product-usage guard test since fake always returns False"

patterns-established:
  - "ICacheService mock pattern: make_cache() helper returning AsyncMock for handlers with cache invalidation"
  - "_make_bulk_item() helper for BulkAttributeItem construction with required fields"

requirements-completed: [CMD-03]

# Metrics
duration: 5min
completed: 2026-03-28
---

# Phase 04 Plan 03: Attribute/Template/Binding Handler Tests Summary

**55 unit tests covering 12 attribute/template/binding command handlers with FakeUoW, validating template CRUD+clone, attribute CRUD+bulk_create, and binding bind/unbind/update/reorder**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-28T15:30:51Z
- **Completed:** 2026-03-28T15:36:29Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- 12 test classes covering every attribute-domain command handler (CMD-03)
- Happy path, rejection path, and event emission tests for all handlers
- Bulk operations tested: batch limit, duplicate codes/slugs, skip_existing mode, group validation
- Template clone verified to copy all bindings (not just template)
- Binding reorder verified with ownership validation and sort_order update
- Delete guards tested: template bindings check, product attribute values check, category references check

## Task Commits

Each task was committed atomically:

1. **Task 1: Write all 12 Attribute/Template/Binding handler tests** - `3cba703` (test)

## Files Created/Modified
- `backend/tests/unit/modules/catalog/application/commands/test_attribute_handlers.py` - 55 tests across 12 classes for CMD-03

## Decisions Made
- Used `_store` instead of `items` property for fake repo assertions -- concrete fake repos (FakeAttributeRepository, etc.) extend interface ABCs directly, not the FakeRepository base class that has the `items` property
- Monkeypatched `has_product_attribute_values` to return True for the product-usage guard test, since the fake implementation always returns False (no cross-repo wiring for product attribute values yet)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed _store vs items property mismatch**
- **Found during:** Task 1 (test execution)
- **Issue:** Plan specified `uow.attributes.items` but concrete fake repos use `_store` directly (they extend interface ABCs, not FakeRepository base)
- **Fix:** Changed all `.items` references to `._store` across the test file
- **Files modified:** test_attribute_handlers.py
- **Verification:** All 55 tests pass
- **Committed in:** 3cba703

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Minor property name correction. No scope creep.

## Issues Encountered
- Pre-existing test failure in `test_image_backend_client.py` (KeyError on headers) -- unrelated to this plan, not addressed

## Known Stubs
None - all tests wire real data through FakeUoW, no stubs.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- CMD-03 requirement fully covered with 55 passing tests
- All 3 plans in Phase 04 complete (brand, category, attribute handler tests)
- Ready for Phase 05 (product command handlers)

## Self-Check: PASSED

- test_attribute_handlers.py: FOUND
- Commit 3cba703: FOUND

---
*Phase: 04-brand-category-attribute-command-handlers*
*Completed: 2026-03-28*
