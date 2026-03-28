---
phase: 01-test-infrastructure
plan: 04
subsystem: testing
tags: [schemathesis, respx, dirty-equals, pytest-randomly, fake-repos, gap-closure]

# Dependency graph
requires:
  - phase: 01-01
    provides: "Initial test dependency installation and builder infrastructure"
  - phase: 01-02
    provides: "FakeUnitOfWork and fake catalog repository implementations"
provides:
  - All 6 required test dependencies importable without errors
  - FakeMediaAssetRepository with complete abstract method coverage
  - FakeUnitOfWork instantiation without TypeError
affects: [02-domain-entity-tests, 03-command-handler-tests, 05-product-command-handlers, 06-media-tests]

# Tech tracking
tech-stack:
  added: []
  patterns: [NotImplementedError-stubs-for-future-phases]

key-files:
  created: []
  modified:
    - backend/pyproject.toml
    - backend/uv.lock
    - backend/tests/fakes/fake_catalog_repos.py

key-decisions:
  - "Used NotImplementedError stubs for bulk_update_sort_order and check_main_exists since full implementations are deferred to Phase 6"

patterns-established:
  - "Gap closure pattern: verification gaps become targeted plans with minimal scope"

requirements-completed: [INFRA-01, INFRA-03]

# Metrics
duration: 3min
completed: 2026-03-28
---

# Phase 01 Plan 04: Gap Closure -- Missing Dependencies and FakeMediaAssetRepository Stubs

**Installed 4 missing test dependencies and added 2 abstract method stubs to FakeMediaAssetRepository, closing INFRA-01 and INFRA-03 verification gaps**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-28T12:45:00Z
- **Completed:** 2026-03-28T12:48:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- All 6 required test dependencies (hypothesis, schemathesis, respx, dirty-equals, pytest-randomly, pytest-timeout) are installed and importable
- FakeMediaAssetRepository now implements all abstract methods from IMediaAssetRepository (bulk_update_sort_order, check_main_exists added as NotImplementedError stubs)
- FakeUnitOfWork instantiates without TypeError -- all 11 smoke tests pass
- No regressions in any Phase 01 tests (37/37 pass)

## Task Commits

Each task was committed atomically:

1. **Task 1: Install 4 missing test dependencies** - `96efa9f` (fix)
2. **Task 2: Add missing abstract method stubs to FakeMediaAssetRepository** - `eed5ea6` (fix)

## Files Created/Modified
- `backend/pyproject.toml` - Added schemathesis, respx, dirty-equals, pytest-randomly to dev dependency group
- `backend/uv.lock` - Updated lockfile with resolved versions for new dependencies
- `backend/tests/fakes/fake_catalog_repos.py` - Added bulk_update_sort_order and check_main_exists stubs to FakeMediaAssetRepository

## Decisions Made
- Used `NotImplementedError` stubs (not full implementations) for the two new FakeMediaAssetRepository methods since they are only needed in Phase 6 (media management tests)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 01 test infrastructure is now complete with all gaps closed
- All 37 Phase 01 tests pass (16 builder + 11 FakeUoW + 10 hypothesis strategy smoke tests)
- All 6 test dependencies are available for subsequent phases
- FakeUnitOfWork is fully functional for command handler testing in Phases 04-05

## Self-Check: PASSED

All 3 modified files verified on disk. Both task commits verified (96efa9f, eed5ea6). All 37 Phase 01 tests pass. All 6 dependencies import successfully.

---
*Phase: 01-test-infrastructure*
*Completed: 2026-03-28*
