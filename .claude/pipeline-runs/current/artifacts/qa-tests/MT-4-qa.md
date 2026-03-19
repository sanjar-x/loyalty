# QA Report -- MT-4: Add Product domain exceptions

> **QA Engineer:** senior-qa (10/10)
> **Plan:** arch/MT-4-plan.md
> **Review:** review/MT-4-review.md
> **Verdict:** DONE

---

## Test files created

- `tests/unit/modules/catalog/domain/test_product_exceptions.py` -- 89 tests

Integration and e2e tests: skipped (no infrastructure changes, no new endpoints).
Architecture tests: covered by the existing `tests/architecture/test_boundaries.py`
(domain purity rules already enforce the no-framework-imports constraint on all domain files).

---

## Scenarios covered

| Scenario | Test(s) | Result |
|----------|---------|--------|
| Happy path: InvalidStatusTransitionError inheritance, status_code, error_code | `TestInvalidStatusTransitionError::test_inherits_*`, `test_status_code_is_422`, `test_error_code` | PASS |
| Message formatting with injected enum values | `test_message_contains_current_and_target_status`, `test_message_format` | PASS |
| Details dict: current/target serialized as .value strings, not enum instances | `test_details_current_status`, `test_details_target_status`, `test_details_allowed_transitions_serialized_as_strings` | PASS |
| Edge case: empty allowed_transitions list | `test_details_allowed_transitions_empty_list` | PASS |
| Complete details key set | `test_details_keys_complete` (all 8 exception classes) | PASS |
| ProductSlugConflictError: inheritance, status_code=409, error_code, message, details | `TestProductSlugConflictError` (8 tests) | PASS |
| Parametrized slug values (1-char, normal, max-length) | `test_various_slug_values` | PASS |
| SKUNotFoundError: inheritance, status_code=404, error_code, message, details | `TestSKUNotFoundError` (8 tests) | PASS |
| SKUNotFoundError: accepts both UUID and plain string sku_id | `test_accepts_string_sku_id` | PASS |
| SKUCodeConflictError: inheritance, status_code=409, error_code, message, details | `TestSKUCodeConflictError` (7 tests) | PASS |
| DuplicateVariantCombinationError: static message, correct details | `TestDuplicateVariantCombinationError` (7 tests) | PASS |
| DuplicateProductAttributeError: static message, both UUIDs serialized | `TestDuplicateProductAttributeError` (7 tests) | PASS |
| ProductAttributeValueNotFoundError: static message, accepts string ids | `TestProductAttributeValueNotFoundError` (9 tests) | PASS |
| ConcurrencyError: inheritance, status_code=409, error_code, message with entity_id | `TestConcurrencyError` (12 tests) | PASS |
| ConcurrencyError: generic for multiple entity types | `test_generic_entity_types` (parametrized: Product, SKU, Order, Warehouse) | PASS |
| Integration: Product.transition_status raises InvalidStatusTransitionError on forbidden move | `test_transition_status_raises_on_forbidden_transition` | PASS |
| Integration: details in raised InvalidStatusTransitionError reflect actual FSM state | `test_transition_status_allowed_transitions_in_details` | PASS |
| Integration: valid transition does not raise | `test_transition_status_valid_transition_does_not_raise` | PASS |
| Integration: parametrized forbidden FSM transitions (6 cases) | `test_forbidden_transitions_all_raise` | PASS |
| Integration: Product.add_sku raises DuplicateVariantCombinationError on hash collision | `test_add_sku_raises_on_duplicate_variant_combination` | PASS |
| Integration: SHA-256 hash is 64-char hex digest in details | `test_add_sku_raises_on_duplicate_variant_combination` | PASS |
| Integration: soft-deleted duplicate does not block re-add | `test_add_sku_no_raise_on_soft_deleted_duplicate` | PASS |
| Integration: Product.remove_sku raises SKUNotFoundError for unknown id | `test_remove_sku_raises_sku_not_found_for_unknown_id` | PASS |
| Integration: Product.remove_sku raises SKUNotFoundError for already-deleted SKU (regression guard) | `test_remove_sku_raises_sku_not_found_for_already_deleted_sku` | PASS |
| Integration: remove_sku succeeds on active SKU (sanity) | `test_remove_sku_succeeds_for_valid_active_sku` | PASS |

---

## Acceptance criteria verification

From pm-spec.md MT-4 / reviewer's sign-off:

- [x] `InvalidStatusTransitionError (UnprocessableEntityError)` with `current_status`, `target_status`, `allowed_transitions` in details -- tested by `TestInvalidStatusTransitionError` (11 tests)
- [x] `ProductSlugConflictError (ConflictError)` -- tested by `TestProductSlugConflictError` (8 tests)
- [x] `SKUNotFoundError (NotFoundError)` -- tested by `TestSKUNotFoundError` (8 tests)
- [x] `SKUCodeConflictError (ConflictError)` -- tested by `TestSKUCodeConflictError` (7 tests)
- [x] `DuplicateVariantCombinationError (ConflictError)` with `product_id`, `variant_hash` in details -- tested by `TestDuplicateVariantCombinationError` (7 tests)
- [x] `DuplicateProductAttributeError (ConflictError)` with `product_id`, `attribute_id` in details -- tested by `TestDuplicateProductAttributeError` (7 tests)
- [x] `ProductAttributeValueNotFoundError (NotFoundError)` -- tested by `TestProductAttributeValueNotFoundError` (9 tests)
- [x] `ConcurrencyError (ConflictError)` with `entity_type`, `entity_id`, `expected_version`, `actual_version` -- tested by `TestConcurrencyError` (12 tests)
- [x] Constructor kwargs match `Product.change_status()` / `transition_status()` usage -- tested by `TestProductEntityRaisesCorrectExceptions`
- [x] Constructor kwargs match `Product.add_sku()` usage -- tested by `test_add_sku_raises_on_duplicate_variant_combination`
- [x] Constructor kwargs match `Product.remove_sku()` usage -- tested by `test_remove_sku_raises_sku_not_found_*`
- [x] All existing tests pass after this change -- verified (748 passed total)

---

## Test results

| Suite | Passed | Failed | Skipped |
|-------|--------|--------|---------|
| unit (new file) | 89 | 0 | 0 |
| unit (full suite) | 748 | 0 | 0 |
| architecture | included in 748 above | 0 | 0 |
| integration | skipped (no infra changes) | -- | -- |
| e2e | skipped (no new endpoints) | -- | -- |

---

## Coverage

The new 89 tests bring `src/modules/catalog/domain/exceptions.py` to near-complete
coverage for the 8 exception classes added in MT-4. Full suite total: 748 passed in
6.96 s. Coverage delta is positive (previously 634 tests, now 748 tests covering the
same source with additional exception-path assertions).

---

## Verdict

**DONE** -- all 89 tests pass, full unit+architecture suite (748 tests) passes, micro-task is complete.
