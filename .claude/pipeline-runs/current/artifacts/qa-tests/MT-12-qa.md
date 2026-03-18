# QA Report -- MT-12: Add UpdateSKU command handler

> **QA Engineer:** senior-qa (10/10)
> **Verdict:** DONE

---

## Test files created

- `tests/unit/modules/catalog/application/commands/test_update_sku.py` -- 38 tests

## Scenarios covered

| Scenario                            | Test                                                          | Result |
| ----------------------------------- | ------------------------------------------------------------- | ------ |
| Happy path                          | `test_returns_result_with_sku_id`                             | PASS   |
| Repo + UoW interaction              | `test_calls_repo_update_and_uow_commit`                      | PASS   |
| Get with SKUs                       | `test_calls_repo_get_with_skus`                               | PASS   |
| SKU update delegation               | `test_calls_sku_update_with_sku_code`                         | PASS   |
| is_active update                    | `test_calls_sku_update_with_is_active`                        | PASS   |
| UoW context manager                 | `test_uow_used_as_context_manager`                            | PASS   |
| No fields = empty kwargs            | `test_no_fields_provided_calls_update_with_empty_kwargs`       | PASS   |
| Product not found                   | `test_raises_product_not_found_error`                         | PASS   |
| No commit on product not found      | `test_no_commit_on_product_not_found`                         | PASS   |
| No repo update on product not found | `test_no_repo_update_on_product_not_found`                    | PASS   |
| SKU not found                       | `test_raises_sku_not_found_error`                             | PASS   |
| No commit on SKU not found          | `test_no_commit_on_sku_not_found`                             | PASS   |
| Soft-deleted SKU = not found        | `test_soft_deleted_sku_treated_as_not_found`                  | PASS   |
| Version mismatch                    | `test_version_mismatch_raises_concurrency_error`              | PASS   |
| No commit on version mismatch       | `test_no_commit_on_version_mismatch`                          | PASS   |
| Matching version proceeds           | `test_matching_version_proceeds`                              | PASS   |
| None version skips check            | `test_none_version_skips_check`                               | PASS   |
| Variant hash recomputation          | `test_variant_attributes_recomputes_hash`                     | PASS   |
| Duplicate variant hash              | `test_duplicate_variant_hash_raises_error`                    | PASS   |
| Deleted SKU hash ignored            | `test_deleted_sku_hash_collision_ignored`                     | PASS   |
| Same SKU hash ignored               | `test_same_sku_hash_collision_ignored`                        | PASS   |
| No variant = no hash                | `test_no_variant_attributes_skips_hash_computation`           | PASS   |
| Price amount only                   | `test_price_amount_only_uses_existing_currency`               | PASS   |
| Price currency only                 | `test_price_currency_only_uses_existing_amount`               | PASS   |
| Both price fields                   | `test_both_price_fields_creates_new_money`                    | PASS   |
| No price fields                     | `test_no_price_fields_omits_price_from_kwargs`                | PASS   |
| Sentinel omits compare_at_price     | `test_sentinel_default_omits_compare_at_price`                | PASS   |
| None clears compare_at_price        | `test_explicit_none_clears_compare_at_price`                  | PASS   |
| Int sets compare_at_price Money     | `test_explicit_amount_sets_money_with_effective_currency`      | PASS   |
| New currency for compare_at_price   | `test_compare_at_price_uses_new_currency_when_price_currency_changes` | PASS |
| compare_at_price <= price           | `test_compare_at_price_lte_price_raises_value_error`          | PASS   |
| Command fields stored               | `test_required_fields_stored`                                 | PASS   |
| Command defaults                    | `test_optional_fields_default_to_none_or_sentinel`            | PASS   |
| Command frozen                      | `test_command_is_frozen`                                      | PASS   |
| Command accepts values              | `test_all_optional_fields_accept_values`                      | PASS   |
| Sentinel vs None                    | `test_compare_at_price_amount_none_vs_sentinel`               | PASS   |
| Result stores id                    | `test_stores_sku_id`                                          | PASS   |
| Result frozen                       | `test_result_is_frozen`                                       | PASS   |

## Test results

| Suite | Passed | Failed | Skipped |
| ----- | ------ | ------ | ------- |
| unit  | 38     | 0      | 0       |

## Verdict

**DONE** -- all 38 tests pass. MT-12 test coverage is complete.
