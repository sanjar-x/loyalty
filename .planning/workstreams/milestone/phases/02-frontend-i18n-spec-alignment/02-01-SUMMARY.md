---
phase: 02-frontend-i18n-spec-alignment
plan: 01
subsystem: ui
tags: [react, i18n, admin, frontend]

requires:
  - phase: 01-backend-schema-fixes
    provides: Backend accepts optional descriptionI18N
provides:
  - buildI18nPayload(ru, en) write-side i18n helper in lib/utils.js
  - Category CRUD with nameI18N dict payloads
  - Category tree display using i18n() read helper
affects: [06-frontend-media-field-alignment, 08-admin-ui-enhancements]

tech-stack:
  added: []
  patterns: [buildI18nPayload for all i18n write paths, i18n() for all read paths]

key-files:
  created: []
  modified:
    - frontend/admin/src/lib/utils.js
    - frontend/admin/src/hooks/useProductForm.js
    - frontend/admin/src/components/admin/settings/categories/CategoryModal.jsx
    - frontend/admin/src/components/admin/settings/categories/CategoryNode.jsx
    - frontend/admin/src/app/admin/settings/categories/page.jsx

key-decisions:
  - "buildI18nPayload uses en || ru (falsy-coalescing) — empty string triggers fallback, matching backend requirement for both locales"
  - "CategoryModal passes empty string for en locale — single-language input duplicates ru into en"

patterns-established:
  - "i18n write pattern: always use buildI18nPayload(ru, en) for payload construction"
  - "i18n read pattern: always use i18n(obj) for extracting display string from I18N dict"

requirements-completed: [I18N-01]

duration: 8min
completed: 2026-03-30
---

# Plan 02-01: Fix Admin i18n Payloads Summary

**buildI18nPayload helper + product form and category CRUD i18n fixes — backend never receives incomplete locale dicts**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-30T01:10:00Z
- **Completed:** 2026-03-30T01:18:00Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Added `buildI18nPayload(ru, en)` write-side helper to `lib/utils.js` — symmetric pair with existing `i18n()` read helper
- Fixed `useProductForm.js` to always send both ru/en locales for titleI18N and descriptionI18N
- Fixed `CategoryModal.jsx` to send `nameI18N` dict instead of plain `name` string for create and edit
- Fixed `CategoryNode.jsx` to display `i18n(node.nameI18N)` instead of bare `node.name`
- Fixed `CategoriesPage.jsx` to extract ru string from `category.nameI18N` for edit modal

## Task Commits

Each task was committed atomically:

1. **Task 1: Add buildI18nPayload helper and fix useProductForm.js** - `f2eb3f8` (fix)
2. **Task 2: Fix CategoryModal, CategoryNode, and CategoriesPage** - `e1445d4` (fix)

## Files Created/Modified
- `frontend/admin/src/lib/utils.js` - Added buildI18nPayload(ru, en) write helper with JSDoc
- `frontend/admin/src/hooks/useProductForm.js` - Uses buildI18nPayload for titleI18N and descriptionI18N
- `frontend/admin/src/components/admin/settings/categories/CategoryModal.jsx` - Sends nameI18N dict for create/edit
- `frontend/admin/src/components/admin/settings/categories/CategoryNode.jsx` - Displays i18n(node.nameI18N)
- `frontend/admin/src/app/admin/settings/categories/page.jsx` - Extracts name via i18n(category.nameI18N) for edit

## Decisions Made
- Used `en || ru` (falsy-coalescing) rather than `en ?? ru` (nullish) — empty string should trigger ru fallback
- CategoryModal passes `buildI18nPayload(name, '')` — single-language modal always copies ru to en

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All admin write-path forms now send valid i18n payloads with both ru and en locales
- Category display correctly reads nameI18N dict
- Ready for Phase 6 (media field alignment) and Phase 8 (UI enhancements)

---
*Phase: 02-frontend-i18n-spec-alignment*
*Completed: 2026-03-30*
