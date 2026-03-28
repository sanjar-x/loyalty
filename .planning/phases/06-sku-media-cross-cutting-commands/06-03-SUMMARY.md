---
plan: 06-03
status: complete
started: 2026-03-28T22:16:00.000Z
completed: 2026-03-28T22:18:00.000Z
---

## Summary

Wrote 16 cross-cutting concern tests covering event audit gaps, bulk atomicity, and FK/uniqueness error paths (CMD-08, CMD-09, CMD-10).

## What was built

- TestEventAuditGaps (5 tests): AddSKU emits SKUAddedEvent, DeleteSKU emits SKUDeletedEvent, GenerateSKUMatrix emits N SKUAddedEvents, BulkCreateBrands emits N BrandCreatedEvents, no events on validation failure
- TestBulkAtomicity (3 tests): strict mode rollback on slug conflict (committed=False), matrix validation rollback (zero SKUs), skip mode partial success (committed=True)
- TestFKUniquenessErrors (8 tests): AddSKU product/variant not found, AddMedia product/variant not found, GenerateMatrix attribute not found, AddSKU code conflict, AddMedia MAIN duplicate, UpdateSKU duplicate variant hash

## Key files

### Created
- `backend/tests/unit/modules/catalog/application/commands/test_cross_cutting.py` (430 lines)

## Self-Check: PASSED

All 16 tests pass. Every test verifies uow.committed state. Event tests verify via uow.collected_events.
