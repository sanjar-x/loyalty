---
phase: 08-admin-ui-enhancements
plan: 01
subsystem: infra
tags: [bff, proxy, product-detail, completeness, fsm, constants]

requires:
  - phase: 01-backend-schema-fixes
    provides: Backend accepts correct payloads
provides:
  - BFF GET/PATCH product detail proxy route
  - BFF GET completeness proxy route
  - getProduct, getProductCompleteness, updateProduct service functions
  - PRODUCT_STATUS_TRANSITIONS and PRODUCT_STATUS_LABELS constants
affects: []

tech-stack:
  added: []
  patterns: [FSM transition map as static constant]

key-files:
  created:
    - frontend/admin/src/app/api/catalog/products/[productId]/route.js
    - frontend/admin/src/app/api/catalog/products/[productId]/completeness/route.js
  modified:
    - frontend/admin/src/services/products.js
    - frontend/admin/src/lib/constants.js

key-decisions:
  - "PATCH route passes body through as-is — version field flows naturally"
  - "FSM constants mirror backend _ALLOWED_TRANSITIONS exactly (5 statuses, 7 transitions)"

requirements-completed: [UI-01, UI-02, UI-03]

duration: 5min
completed: 2026-03-30
---

# Plan 08-01: BFF Routes, Service Functions, FSM Constants Summary

**BFF product detail/completeness routes + 3 service functions + FSM transition map matching backend exactly**

## Task Commits

1. **Task 1+2: BFF routes, service functions, constants** - `b33df82` (feat)

## Deviations from Plan
None.

---
*Phase: 08-admin-ui-enhancements*
*Completed: 2026-03-30*
