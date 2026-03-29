---
phase: 03-bff-media-proxy-infrastructure
plan: 01
subsystem: infra
tags: [bff, proxy, fetch, image-backend, api-client]

requires: []
provides:
  - imageBackendFetch() utility for BFF media proxy routes
  - IMAGE_BACKEND_URL and IMAGE_BACKEND_API_KEY env var documentation
affects: [04-bff-upload-route, 05-bff-confirm-external-routes]

tech-stack:
  added: []
  patterns: [service-to-service X-API-Key auth via BFF fetch wrapper]

key-files:
  created:
    - frontend/admin/src/lib/image-api-client.js
  modified:
    - frontend/admin/.env.local.example

key-decisions:
  - "Mirrored backendFetch() pattern exactly — same signature, same return shape, different target and auth"
  - "Used catch block returning structured 502 instead of letting network errors propagate"
  - "console.warn guards for missing env vars — non-blocking, visible in dev server logs"

patterns-established:
  - "BFF service client pattern: one file per upstream service (api-client.js for backend, image-api-client.js for image_backend)"

requirements-completed: [BFF-01]

duration: 5min
completed: 2026-03-30
---

# Plan 03-01: imageBackendFetch() Utility Summary

**Server-side fetch wrapper for image_backend with X-API-Key auth and structured 502 error handling**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-30T01:30:00Z
- **Completed:** 2026-03-30T01:35:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Created `imageBackendFetch(path, options)` mirroring `backendFetch()` pattern with X-API-Key auth
- Added try/catch returning structured 502 error when image_backend is unreachable
- Documented IMAGE_BACKEND_URL and IMAGE_BACKEND_API_KEY in `.env.local.example`
- Admin frontend builds clean — no import or syntax errors

## Task Commits

1. **Task 1: Create imageBackendFetch() utility** - `4b22c7f` (feat)
2. **Task 2: Add image_backend env vars** - `81d917c` (feat)

## Files Created/Modified
- `frontend/admin/src/lib/image-api-client.js` - New: imageBackendFetch() with X-API-Key auth + 502 error handling
- `frontend/admin/.env.local.example` - Added IMAGE_BACKEND_URL and IMAGE_BACKEND_API_KEY

## Decisions Made
- Mirrored backendFetch() exactly — callers (Phase 4/5) use identical API
- Used `en || ru` style catch (bare catch, no error var) matching project's ES2017+ convention

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - `.env.local.example` updated with defaults. Dev mode doesn't require valid API key.

## Next Phase Readiness
- Phase 4 can `import { imageBackendFetch } from '@/lib/image-api-client'` for upload proxy route
- Phase 5 can use same import for confirm and external routes
- Return shape `{ ok, status, data }` matches existing `backendFetch()` so route handlers need minimal changes

---
*Phase: 03-bff-media-proxy-infrastructure*
*Completed: 2026-03-30*
