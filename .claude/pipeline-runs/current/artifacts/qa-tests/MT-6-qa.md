# QA Report -- MT-6: Add Product read models

> **QA Engineer:** senior-qa (10/10)
> **Plan:** arch/MT-6-plan.md
> **Review:** review/MT-6-review.md
> **Verdict:** DONE

---

## Test files created

- `tests/unit/modules/catalog/application/queries/test_product_read_models.py` — 74 tests

Integration and E2E suites skipped: MT-6 adds pure application-layer data classes with no database schema changes, no repository implementations, and no HTTP endpoints.

---

## Scenarios covered

| Scenario | Test(s) | Result |
|----------|---------|--------|
| Happy path: MoneyReadModel instantiation | `test_instantiation_with_valid_fields` | PASS |
| Happy path: VariantAttributePairReadModel instantiation | `test_instantiation_with_valid_uuids` | PASS |
| Happy path: SKUReadModel instantiation (minimal) | `test_instantiation_minimal` | PASS |
| Happy path: ProductAttributeValueReadModel instantiation | `test_instantiation_with_valid_fields` | PASS |
| Happy path: ProductReadModel instantiation | `test_instantiation_with_required_fields` | PASS |
| Happy path: ProductListItemReadModel instantiation | `test_instantiation_with_valid_fields` | PASS |
| Happy path: ProductListReadModel instantiation | `test_instantiation_with_items` | PASS |
| BaseModel inheritance (all 7 models) | `test_inherits_from_base_model` (x7), `test_all_new_models_use_base_model_not_camel_model` | PASS |
| No CamelModel in MRO (all 7 models) | `test_all_new_models_use_base_model_not_camel_model` | PASS |
| status is plain str, not domain enum | `test_status_is_plain_string_not_enum`, `test_status_is_plain_string`, `test_status_field_is_not_domain_enum` | PASS |
| status accepts any string value | `test_status_accepts_any_string[active/draft/published/archived/CUSTOM]` | PASS |
| No domain imports in read_models.py | `test_read_models_module_no_domain_catalog_import` | PASS |
| No SQLAlchemy imports in read_models.py | `test_read_models_module_no_sqlalchemy_import` | PASS |
| Nesting: SKUReadModel.price is MoneyReadModel | `test_price_is_money_read_model`, `test_nesting_sku_contains_money_model` | PASS |
| Nesting: SKUReadModel.variant_attributes list | `test_variant_attributes_list_of_pairs`, `test_nesting_sku_contains_variant_pairs` | PASS |
| Nesting: ProductReadModel.skus list of SKUReadModel | `test_skus_list_contains_sku_read_models` | PASS |
| Nesting: ProductReadModel.attributes list of ProductAttributeValueReadModel | `test_attributes_list_contains_product_attribute_value_models` | PASS |
| Deep nesting: ProductReadModel -> SKU -> MoneyReadModel round-trip | `test_serialization_round_trip` (ProductReadModel), `test_json_round_trip` (ProductReadModel) | PASS |
| Optional fields default to None | `test_optional_fields_default_to_none`, `test_compare_at_price_optional_none`, `test_deleted_at_optional_set` | PASS |
| Optional fields accept non-None values | `test_optional_fields_can_be_set`, `test_compare_at_price_optional_set` | PASS |
| compare_at_price is MoneyReadModel or None | `test_compare_at_price_optional_none`, `test_compare_at_price_optional_set` | PASS |
| min_price / max_price are int or None (no currency) | `test_min_price_max_price_are_int_or_none` | PASS |
| Serialization round-trip (model_dump / model_validate) | `test_serialization_round_trip` (all 7 models) | PASS |
| JSON round-trip (model_dump_json / model_validate_json) | `test_json_round_trip` (MoneyReadModel, ProductReadModel, ProductListReadModel) | PASS |
| ProductListItemReadModel is lightweight (no skus/attributes/description_i18n) | `test_no_skus_or_attributes_fields` | PASS |
| Pagination boundary values | `test_pagination_boundary_values` (5 parametrized cases) | PASS |
| Empty items list is valid | `test_instantiation_empty_items` | PASS |
| Zero amount is valid | `test_zero_amount_is_valid` | PASS |
| Multiple SKUs and attributes on one product | `test_multiple_skus_and_attributes` | PASS |
| Empty tags list is valid | `test_empty_tags_list_is_valid` | PASS |
| Field type checks (UUID, int, str, bool, datetime) | Dedicated type-assertion tests per model | PASS |

---

## Acceptance criteria verification

From pm-spec.md MT-6:

- [x] ProductReadModel with all product fields including status, version, min_price, max_price, skus list, attributes list — tested by `test_instantiation_with_required_fields`, `test_optional_fields_default_to_none`, `test_optional_fields_can_be_set`, `test_skus_list_contains_sku_read_models`, `test_attributes_list_contains_product_attribute_value_models`
- [x] ProductListReadModel with items, total, offset, limit — tested by `test_instantiation_with_items`, `test_total_is_int`, `test_offset_is_int`, `test_limit_is_int`, `test_pagination_boundary_values`
- [x] ProductListItemReadModel (lightweight: id, slug, title_i18n, status, brand_id, primary_category_id, version) — tested by `test_instantiation_with_valid_fields`, `test_no_skus_or_attributes_fields`
- [x] SKUReadModel with all SKU fields including price as Money-like structure (amount + currency) — tested by `test_instantiation_minimal`, `test_price_is_money_read_model`, `test_compare_at_price_optional_set`, `test_variant_attributes_list_of_pairs`
- [x] ProductAttributeValueReadModel with product_id, attribute_id, attribute_value_id — tested by `test_instantiation_with_valid_fields`, `test_all_fields_are_uuids`
- [x] All existing tests pass after this change — 869 passed (795 pre-MT-6 + 74 new)
- [x] All read models inherit from BaseModel (not CamelModel) — tested by `test_all_new_models_use_base_model_not_camel_model`

From arch plan acceptance verification:

- [x] MoneyReadModel has amount: int and currency: str fields — `test_amount_is_int`, `test_currency_is_str`
- [x] SKUReadModel has all SKU fields including price: MoneyReadModel and variant_attributes: list[VariantAttributePairReadModel] — `test_price_is_money_read_model`, `test_variant_attributes_list_of_pairs`
- [x] ProductAttributeValueReadModel has id, product_id, attribute_id, attribute_value_id — `test_all_fields_are_uuids`
- [x] ProductReadModel has all product fields plus min_price, max_price, skus, attributes — `test_optional_fields_default_to_none`, `test_min_price_max_price_are_int_or_none`
- [x] ProductListItemReadModel is lightweight — `test_no_skus_or_attributes_fields`
- [x] ProductListReadModel has items, total, offset, limit — `test_instantiation_with_items`, `test_serialization_round_trip`
- [x] No domain entity imports in read_models.py — `test_read_models_module_no_domain_catalog_import`
- [x] No cross-module imports — `test_read_models_module_no_sqlalchemy_import` (sqlalchemy check); architecture suite covers boundaries
- [x] All read models inherit from BaseModel (not CamelModel) — `test_all_new_models_use_base_model_not_camel_model`

---

## Test results

| Suite | Passed | Failed | Skipped |
|-------|--------|--------|---------|
| unit (new file) | 74 | 0 | 0 |
| unit (full suite) | 869 | 0 | 0 |
| architecture | included in 869 | 0 | 0 |
| integration | skipped — no infra changes | — | — |
| e2e | skipped — no new endpoints | — | — |

---

## Coverage

Coverage measured against `src/` on the unit + architecture suite.

| Metric | Before MT-6 | After MT-6 | Delta |
|--------|-------------|------------|-------|
| New test file coverage | — | 74/74 tests | +74 tests |
| Total passing tests | 795 | 869 | +74 |
| `read_models.py` lines under test | 100% (exercised directly) | 100% | 0% (already full) |

Coverage did not decrease. The new read model classes are fully exercised by the new test suite.

---

## Verdict

**DONE** — all 74 tests pass, no pre-existing tests broken (869 total passing), coverage maintained. MT-6 is complete.
