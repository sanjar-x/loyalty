# QA Report -- MT-19: Add Product Pydantic schemas

> **QA Engineer:** senior-qa (10/10)
> **Verdict:** DONE

---

## Test files created/modified

- `tests/unit/modules/catalog/presentation/test_product_schemas.py` -- 92 tests
- `tests/architecture/` -- skipped (no new modules, presentation schemas only)
- `tests/integration/` -- skipped (no infra changes)
- `tests/e2e/` -- skipped (no new endpoints in this MT)

## Schemas tested

| Schema | Tests |
|--------|-------|
| MoneySchema | 14 (valid, zero, negative, currency patterns, camelCase) |
| VariantAttributePairSchema | 4 (valid, aliases, missing fields) |
| ProductCreateRequest | 14 (valid, all fields, missing required, slug patterns, max lengths, camelCase) |
| ProductCreateResponse | 1 |
| ProductUpdateRequest | 12 (empty rejected, sentinel nulls, partial updates, slug validation, camelCase) |
| ProductStatusChangeRequest | 2 (valid, missing) |
| SKUCreateRequest | 10 (valid, price validation, currency, sku_code, compare_at_price, variant attrs, camelCase) |
| SKUCreateResponse | 1 |
| SKUUpdateRequest | 10 (partial update, sentinel pattern, validation, variant attrs, version, camelCase) |
| SKUResponse | 3 (valid, compare_at_price, camelCase) |
| ProductAttributeAssignRequest | 2 (valid, camelCase) |
| ProductAttributeAssignResponse | 1 |
| ProductAttributeResponse | 2 (valid, camelCase) |
| ProductResponse | 3 (full response, nested SKUs/attrs, camelCase) |
| ProductListItemResponse | 2 (valid, camelCase) |
| ProductListResponse | 2 (empty, with items) |
| CamelCaseAliasing (cross-schema) | 3 (populate_by_alias for create, update, SKU) |

## Scenarios covered

| Scenario | Test | Result |
|----------|------|--------|
| Happy path | test_valid_creation, test_valid_sku, test_valid_money | PASS |
| Validation (required fields) | test_missing_title_rejected, test_missing_brand_id_rejected | PASS |
| Validation (pattern) | test_slug_invalid_patterns_rejected (5 cases) | PASS |
| Validation (min/max length) | test_slug_max_length_255, test_sku_code_max_length_100 | PASS |
| Validation (range) | test_negative_amount_rejected, test_negative_price_rejected | PASS |
| Edge cases (zero) | test_zero_amount_accepted, test_zero_price_accepted | PASS |
| Edge cases (currency) | test_invalid_currency_rejected (5 cases), test_lowercase_currency_rejected | PASS |
| PATCH semantics (at_least_one_field) | test_empty_update_rejected, test_sentinel_null_alone_passes_validator | PASS |
| Sentinel pattern | test_compare_at_price_omitted_is_required, test_compare_at_price_null_accepted | PASS |
| CamelCase serialization | test_camel_case_serialization (per schema) | PASS |
| CamelCase deserialization | test_populate_by_alias, test_sku_create_populate_by_alias | PASS |
| Nested schemas | test_with_nested_skus_and_attributes, test_with_variant_attributes | PASS |

## Key findings

1. **CamelCase alias behavior**: `to_camel("title_i18n")` produces `titleI18N` (capital N), not `titleI18n`. This affects both serialization keys and validation error field names when using `model_validate`.
2. **Sentinel pattern (`= ...`)**: Pydantic treats fields with `= ...` as required. In `ProductUpdateRequest`, `supplier_id` and `country_of_origin` must always be explicitly provided in JSON (even as `null`). The `at_least_one_field` validator is effectively unreachable for the "no sentinel provided" path since Pydantic's required-field check fires first.
3. **Constructor vs model_validate**: Constructor-based validation errors use snake_case field names; model_validate errors use camelCase aliases.

## Test results

| Suite | Passed | Failed | Skipped |
|-------|--------|--------|---------|
| unit | 92 | 0 | 0 |
| architecture | -- | -- | skipped |
| integration | -- | -- | skipped |
| e2e | -- | -- | skipped |

## Full suite regression

| Suite | Passed | Failed |
|-------|--------|--------|
| All unit + architecture | 1318 | 0 |

## Verdict

**DONE** -- all 92 tests pass, no regressions in the full suite (1318 passed).
