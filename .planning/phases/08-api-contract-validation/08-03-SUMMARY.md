---
phase: 08-api-contract-validation
plan: 03
subsystem: testing
tags: [e2e, api, storefront, auth, lifecycle, pagination]

requires:
  - phase: 08-01
    provides: Shared conftest.py with entity creation helpers
  - phase: 08-02
    provides: Product aggregate endpoint patterns

provides:
  - Storefront endpoint tests verifying public access and attribute projection
  - Auth enforcement tests proving 401/403 across all protected routers
  - Full product lifecycle test from brand creation through PUBLISHED status
  - Pagination boundary tests for offset, limit, total, hasNext

affects: []

tech-stack:
  added: []
  patterns: [Public vs protected endpoint testing, FSM lifecycle integration test]

key-files:
  created:
    - backend/tests/e2e/api/v1/catalog/test_storefront.py
    - backend/tests/e2e/api/v1/catalog/test_auth_enforcement.py
    - backend/tests/e2e/api/v1/catalog/test_lifecycle.py
    - backend/tests/e2e/api/v1/catalog/test_pagination.py
  modified: []

key-decisions:
  - "Used async_client (no auth) for public storefront endpoints to verify they are truly public"
  - "Auth enforcement tests use authenticated_client (valid JWT, no perms) for 403 tests"
  - "Lifecycle test exercises the complete product creation flow through all FSM states"

requirements-completed: [API-02, API-03, API-04, API-05]

duration: 5 min
completed: 2026-03-28
---

# Phase 08 Plan 03: Storefront, Auth, Lifecycle, Pagination E2E Tests Summary

4 test files covering 27 tests for cross-cutting API concerns: storefront attribute endpoints (public access), auth enforcement (401/403), full product lifecycle (DRAFT to PUBLISHED), and pagination behavior (offset/limit/total/hasNext boundaries).

## Execution Details

- Duration: ~5 min
- Tasks: 3/3 complete
- Files: 4 created
- Tests: 27 (7 storefront + 9 auth + 1 lifecycle + 10 pagination)

## Deviations from Plan

None - plan executed exactly as written.

## Key Artifacts

- Storefront tests verify 3 public endpoints (no auth) and 1 protected endpoint (form-attributes)
- Auth enforcement tests cover representative endpoints from every catalog router
- Full lifecycle test creates 7 prerequisite entities and transitions product through all FSM states
- Pagination tests cover default params, custom offset/limit, offset beyond total, hasNext logic, max limit boundary

## Self-Check: PASSED

- [x] All 4 files created
- [x] All files parse without syntax errors
- [x] Storefront public access verified (no auth on filter/card/comparison endpoints)
- [x] Auth enforcement covers 401 (unauthenticated) and 403 (unauthorized)
- [x] Full lifecycle transitions through DRAFT -> ENRICHING -> READY_FOR_REVIEW -> PUBLISHED
- [x] Pagination boundary conditions tested (offset beyond total, limit=201 -> 422)
