# QA Report -- MT-15: Add Product query handlers

> **QA Engineer:** senior-qa (10/10)
> **Verdict:** DONE

---

## Test files created

- `tests/unit/modules/catalog/application/queries/test_get_product.py` -- 18 tests
- `tests/unit/modules/catalog/application/queries/test_list_products.py` -- 10 tests
- `tests/unit/modules/catalog/application/queries/test_list_skus.py` -- 11 tests
- `tests/unit/modules/catalog/application/queries/test_list_product_attributes.py` -- 7 tests
- Integration tests: skipped -- no infra changes
- E2E tests: skipped -- no new endpoints in this MT
- Architecture tests: skipped -- query handlers are application layer, no new modules

## Scenarios covered

| Scenario                        | Test                                             | Result |
| ------------------------------- | ------------------------------------------------ | ------ |
| Happy path (get product)        | `test_returns_product_read_model`                | PASS   |
| Not found (get product)         | `test_raises_product_not_found_error`            | PASS   |
| SKU mapping (price)             | `test_sku_price_is_money_read_model`             | PASS   |
| SKU mapping (compare_at_price)  | `test_sku_compare_at_price_set`                  | PASS   |
| SKU mapping (variant attrs)     | `test_sku_variant_attributes_mapped`             | PASS   |
| Price aggregation (min/max)     | `test_min_max_price_computed`                    | PASS   |
| Price aggregation (inactive)    | `test_inactive_skus_excluded_from_prices`        | PASS   |
| Price aggregation (deleted)     | `test_deleted_skus_excluded_from_prices`         | PASS   |
| Price aggregation (none)        | `test_no_skus_gives_none_prices`                 | PASS   |
| Edge case (empty tags)          | `test_empty_tags_returns_empty_list`             | PASS   |
| Edge case (all inactive)        | `test_all_skus_inactive_gives_none_prices`       | PASS   |
| Status is plain string          | `test_status_is_plain_string`                    | PASS   |
| Attributes empty until MT-16    | `test_attributes_list_empty_until_mt16`          | PASS   |
| Happy path (list products)      | `test_returns_product_list_read_model`           | PASS   |
| Pagination propagated           | `test_pagination_fields_propagated`              | PASS   |
| Empty result (list products)    | `test_empty_items_with_zero_total`               | PASS   |
| Mapping (list products)         | `test_fields_mapped_correctly`                   | PASS   |
| Query defaults                  | `test_defaults`                                  | PASS   |
| Query immutability              | `test_frozen_immutable`                          | PASS   |
| Happy path (list SKUs)          | `test_returns_list_of_sku_read_models`           | PASS   |
| Empty result (list SKUs)        | `test_empty_list_returned`                       | PASS   |
| SKU fields preserved            | `test_sku_fields_preserved`                      | PASS   |
| Stub returns empty (attrs)      | `test_returns_empty_list`                        | PASS   |
| Stub session not queried        | `test_session_not_queried`                       | PASS   |

## Test results

| Suite        | Passed | Failed | Skipped |
| ------------ | ------ | ------ | ------- |
| unit         | 46     | 0      | 0       |
| architecture | --     | --     | --      |
| integration  | --     | --     | --      |
| e2e          | --     | --     | --      |

## Verdict

**DONE** -- all 46 tests pass in 3.27s, micro-task is complete.
