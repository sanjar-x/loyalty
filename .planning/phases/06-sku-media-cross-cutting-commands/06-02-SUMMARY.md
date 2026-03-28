---
plan: 06-02
status: complete
started: 2026-03-28T22:14:00.000Z
completed: 2026-03-28T22:16:00.000Z
---

## Summary

Wrote 20 unit tests covering all 4 Media command handlers (CMD-07).

## What was built

- TestAddProductMedia (6 tests): gallery image, variant binding, product not found, variant not found, MAIN duplicate, MAIN different variant OK
- TestUpdateProductMedia (6 tests): update sort_order, update role to MAIN, media not found, ownership mismatch, MAIN conflict, variant not found on change
- TestDeleteProductMedia (5 tests): delete with cleanup, no cleanup when no storage_object, media not found, ownership mismatch, cleanup-after-commit ordering
- TestReorderProductMedia (3 tests): happy path reorder, partial match error, empty items

## Key files

### Created
- `backend/tests/unit/modules/catalog/application/commands/test_media_handlers.py` (430 lines)

## Self-Check: PASSED

All 20 tests pass. Image backend cleanup verified to occur after commit, not before.
