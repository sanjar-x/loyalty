---
phase: 04-bff-upload-route
plan: 01
subsystem: infra
tags: [bff, proxy, upload, media, image-backend]

requires:
  - phase: 03-bff-media-proxy-infrastructure
    provides: imageBackendFetch() utility
provides:
  - POST /api/media/upload BFF proxy route
affects: [06-frontend-media-field-alignment]

tech-stack:
  added: []
  patterns: [BFF proxy route with field stripping]

key-files:
  created:
    - frontend/admin/src/app/api/media/upload/route.js
  modified: []

key-decisions:
  - "Strip mediaType, role, sortOrder — only forward contentType + filename to image_backend"
  - "Leave existing broken route at /api/catalog/products/[productId]/media/upload for Phase 6 cleanup"

patterns-established:
  - "Media BFF proxy pattern: auth check → strip fields → imageBackendFetch → passthrough response"

requirements-completed: [BFF-02]

duration: 3min
completed: 2026-03-30
---

# Plan 04-01: BFF Upload Proxy Route Summary

**POST /api/media/upload route strips product-specific fields and forwards {contentType, filename} to image_backend**

## Performance

- **Duration:** 3 min
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Created upload proxy route using imageBackendFetch with X-API-Key auth
- Route strips mediaType, role, sortOrder — only forwards contentType + filename
- Returns storageObjectId, presignedUrl, expiresIn from image_backend
- Admin build shows route registered at /api/media/upload

## Task Commits

1. **Task 1: Create upload proxy route** - `73e3816` (feat)

## Deviations from Plan
None.

## Issues Encountered
None.

---
*Phase: 04-bff-upload-route*
*Completed: 2026-03-30*
