---
plan: 06-01
status: complete
started: 2026-03-28T22:10:00.000Z
completed: 2026-03-28T22:14:00.000Z
---

## Summary

Implemented 2 missing FakeMediaAssetRepository methods (bulk_update_sort_order, check_main_exists) and wrote 23 unit tests covering all 4 SKU command handlers.

## What was built

- Replaced `bulk_update_sort_order` NotImplementedError stub with dict-scanning implementation
- Replaced `check_main_exists` NotImplementedError stub with MediaRole.MAIN check implementation
- TestAddSKU (6 tests): happy path, price, product not found, SKU code conflict, duplicate variant combination, SKUAddedEvent emission
- TestUpdateSKU (6 tests): update sku_code, update price, product not found, SKU not found, version mismatch (ConcurrencyError), SKU code conflict on update
- TestDeleteSKU (4 tests): soft-delete happy path, product not found, SKU not found, SKUDeletedEvent emission
- TestGenerateSKUMatrix (7 tests): single attribute cartesian, two-attribute cartesian (4 combos), duplicate skip, product not found, attribute not found, wrong level, value not found

## Key files

### Created
- `backend/tests/unit/modules/catalog/application/commands/test_sku_handlers.py` (560 lines)

### Modified
- `backend/tests/fakes/fake_catalog_repos.py` (2 stubs replaced)

## Self-Check: PASSED

All 23 tests pass. Zero NotImplementedError stubs remain in FakeMediaAssetRepository.
