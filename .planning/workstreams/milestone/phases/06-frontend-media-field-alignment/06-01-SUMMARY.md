---
phase: 06-frontend-media-field-alignment
plan: 01
subsystem: ui
tags: [frontend, media, field-names, api-client, hooks]

requires:
  - phase: 04-bff-upload-route
    provides: POST /api/media/upload BFF route
  - phase: 05-bff-confirm-external-routes
    provides: POST /api/media/{id}/confirm and /api/media/external BFF routes
provides:
  - Working media upload pipeline (frontend → BFF → image_backend)
  - Correct field name mapping for presignedUrl, storageObjectId
affects: [07-frontend-media-status-polling]

tech-stack:
  added: []
  patterns: []

key-files:
  created: []
  modified:
    - frontend/admin/src/services/products.js
    - frontend/admin/src/hooks/useSubmitProduct.js

key-decisions:
  - "Kept role and sortOrder in uploadTasks array for future Phase 7/8 attach-to-product step"
  - "Deleted 3 old broken route files under /api/catalog/products/[productId]/media/"

patterns-established:
  - "Media service functions are product-agnostic — no productId in signature"

requirements-completed: [MEDIA-01, MEDIA-02]

duration: 5min
completed: 2026-03-30
---

# Plan 06-01: Frontend Media Field Alignment Summary

**Fixed all media field names (presignedUrl, storageObjectId, filename, url) and rewired to new BFF routes**

## Performance

- **Duration:** 5 min
- **Tasks:** 2
- **Files modified:** 2 modified, 3 deleted

## Accomplishments
- Rewrote 3 media service functions to use new /api/media/* BFF routes (no productId)
- Fixed 4 callsites in useSubmitProduct.js: presignedUrl, storageObjectId, {contentType, filename}, {url}
- Deleted 3 old broken route files under /api/catalog/products/[productId]/media/
- Admin build passes clean

## Task Commits

1. **Task 1: Rewrite media service functions** - `033de95` (fix)
2. **Task 2: Fix media callsites in useSubmitProduct** - `780f009` (fix)

## Deviations from Plan
None.

## Issues Encountered
None.

---
*Phase: 06-frontend-media-field-alignment*
*Completed: 2026-03-30*
