---
phase: 04-brand-category-attribute-command-handlers
plan: 02
subsystem: testing
tags: [pytest, category, command-handlers, fake-uow, ellipsis-sentinel, slug-cascade, template-propagation]

# Dependency graph
requires:
  - phase: 04-01
    provides: FakeCategoryRepository with update_descendants_full_slug, propagate_effective_template_id, cross-repo wiring
provides:
  - 28 unit tests for all 4 Category command handlers (CMD-02)
  - TestCreateCategory (7 tests), TestUpdateCategory (8 tests), TestDeleteCategory (5 tests), TestBulkCreateCategories (8 tests)
affects: [04-03, phase-05, phase-06]

# Tech tracking
tech-stack:
  added: []
  patterns: [Ellipsis sentinel for template_id keep-current, _provided_fields pattern for partial updates, intra-batch parent_ref resolution, error_code assertion via exc_info.value.error_code]

key-files:
  created:
    - backend/tests/unit/modules/catalog/application/commands/test_category_handlers.py
  modified: []

key-decisions:
  - "Used exc_info.value.error_code instead of pytest.raises(match=) for ValidationError assertions because error_code is in the exception's details, not its str() representation"

patterns-established:
  - "Ellipsis sentinel test pattern: omit template_id (defaults to ...) for keep-current, explicit None for clear, explicit UUID for set"
  - "_provided_fields is mandatory on UpdateCategoryCommand -- without it the handler does nothing"
  - "error_code assertion pattern: pytest.raises(ValidationError) as exc_info + assert exc_info.value.error_code == 'CODE'"

requirements-completed: [CMD-02]

# Metrics
duration: 3min
completed: 2026-03-28
---

# Phase 04 Plan 02: Category Command Handler Tests Summary

**28 unit tests covering all 4 Category command handlers: create (root + child + template), update (slug cascade + template propagation + Ellipsis sentinel), delete (children/products guards), and bulk create (intra-batch parent_ref tree resolution)**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-28T15:31:29Z
- **Completed:** 2026-03-28T15:34:45Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- All 4 Category command handlers fully tested with 28 passing tests
- Ellipsis sentinel semantics for template_id thoroughly verified (keep-current vs clear vs set)
- Slug cascade to descendants verified via FakeCategoryRepository.update_descendants_full_slug
- Template propagation to inheriting children verified via FakeCategoryRepository.propagate_effective_template_id
- Intra-batch parent_ref resolution tested (creating entire category trees in one bulk call)
- All rejection paths verify uow.committed is False; all happy paths verify uow.committed is True

## Task Commits

Each task was committed atomically:

1. **Task 1: Write Category command handler unit tests (CMD-02)** - `75368ff` (test)

**Plan metadata:** pending (docs: complete plan)

## Files Created/Modified
- `backend/tests/unit/modules/catalog/application/commands/test_category_handlers.py` - 28 unit tests across 4 test classes for Category command handlers

## Decisions Made
- Used `exc_info.value.error_code` instead of `pytest.raises(match=...)` for ValidationError assertions because the error_code is stored in the exception's `error_code` attribute, not in its string representation (which contains the message text)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed ValidationError match patterns**
- **Found during:** Task 1 (test execution)
- **Issue:** Plan specified `pytest.raises(ValidationError, match="BULK_LIMIT_EXCEEDED")` but the `match` parameter matches against `str(exception)` which contains the message, not the error_code
- **Fix:** Changed to `pytest.raises(ValidationError) as exc_info` followed by `assert exc_info.value.error_code == "BULK_LIMIT_EXCEEDED"`
- **Files modified:** test_category_handlers.py
- **Verification:** All 28 tests pass
- **Committed in:** 75368ff (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Minor assertion style fix. No scope change.

## Issues Encountered
- Pre-existing failure in `tests/unit/modules/catalog/infrastructure/test_image_backend_client.py::test_delete_sends_correct_request` (X-API-Key header assertion) -- not related to this plan's changes, out of scope

## User Setup Required
None - no external service configuration required.

## Known Stubs
None - all tests use real domain entity factory methods and FakeUoW repos.

## Next Phase Readiness
- Category handler tests complete, 04-03 (Attribute template + binding handlers) can proceed
- FakeUoW and FakeCategoryRepository patterns established and proven reliable

## Self-Check: PASSED

- FOUND: backend/tests/unit/modules/catalog/application/commands/test_category_handlers.py
- FOUND: commit 75368ff

---
*Phase: 04-brand-category-attribute-command-handlers*
*Completed: 2026-03-28*
