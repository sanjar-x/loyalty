# QA Report -- MT-1: Add ProductStatus and Money value objects

> **QA Engineer:** senior-qa (10/10)
> **Plan:** arch/MT-1-plan.md
> **Review:** review/MT-1-review.md
> **Verdict:** DONE

---

## Test files created/modified

- `tests/unit/modules/catalog/domain/test_value_objects.py` -- 63 tests (1 pre-existing + 62 new)
- `tests/architecture/` -- no new file needed; existing boundary tests already cover domain purity for the catalog module and pass

## Scenarios covered

| Scenario | Test | Result |
|----------|------|--------|
| ProductStatus has exactly 5 members | `TestProductStatus::test_has_exactly_five_members` | PASS |
| All 5 expected members present | `TestProductStatus::test_all_expected_members_present` | PASS |
| Values are lowercase strings (ORM-compatible) | `TestProductStatus::test_values_are_lowercase_strings` | PASS |
| ProductStatus inherits str | `TestProductStatus::test_is_str_enum` | PASS |
| Reconstruct from string value | `TestProductStatus::test_construct_from_string_value` | PASS |
| Each member is a str instance (parametrized x5) | `TestProductStatus::test_each_member_is_a_string` | PASS |
| Happy path: valid amount and currency | `TestMoneyCreation::test_create_with_valid_amount_and_currency` | PASS |
| Edge: zero amount is valid | `TestMoneyCreation::test_zero_amount_is_valid` | PASS |
| Edge: large amount is valid | `TestMoneyCreation::test_large_amount_is_valid` | PASS |
| 3-char currency codes accepted (parametrized x5) | `TestMoneyCreation::test_three_char_currency_codes_accepted` | PASS |
| Negative amount raises ValueError | `TestMoneyValidation::test_negative_amount_raises_value_error` | PASS |
| Large negative amount raises ValueError | `TestMoneyValidation::test_large_negative_amount_raises_value_error` | PASS |
| Currency != 3 chars raises ValueError (parametrized x6) | `TestMoneyValidation::test_currency_not_three_chars_raises_value_error` | PASS |
| Boundary: 2-char currency raises | `TestMoneyValidation::test_two_char_currency_raises` | PASS |
| Boundary: 4-char currency raises | `TestMoneyValidation::test_four_char_currency_raises` | PASS |
| Empty currency raises | `TestMoneyValidation::test_empty_currency_raises` | PASS |
| Frozen: amount mutation raises FrozenInstanceError | `TestMoneyImmutability::test_amount_cannot_be_mutated` | PASS |
| Frozen: currency mutation raises FrozenInstanceError | `TestMoneyImmutability::test_currency_cannot_be_mutated` | PASS |
| Frozen class is hashable | `TestMoneyImmutability::test_money_is_hashable` | PASS |
| Equality: same amount+currency | `TestMoneyEquality::test_equal_same_amount_same_currency` | PASS |
| Inequality: different amount | `TestMoneyEquality::test_not_equal_different_amount` | PASS |
| Inequality: different currency | `TestMoneyEquality::test_not_equal_different_currency` | PASS |
| Inequality: both differ | `TestMoneyEquality::test_not_equal_different_amount_and_currency` | PASS |
| Equality: zero same currency | `TestMoneyEquality::test_zero_same_currency_equal` | PASS |
| Inequality: zero different currency | `TestMoneyEquality::test_zero_different_currency_not_equal` | PASS |
| __lt__ true/false/equal same currency | `TestMoneyOrdering::test_lt_*` (x3) | PASS |
| __le__ true/equal/false same currency | `TestMoneyOrdering::test_le_*` (x3) | PASS |
| __gt__ true/equal/false same currency | `TestMoneyOrdering::test_gt_*` (x3) | PASS |
| __ge__ true/equal/false same currency | `TestMoneyOrdering::test_ge_*` (x3) | PASS |
| __lt__ cross-currency raises ValueError | `TestMoneyCrossCurrencyComparison::test_lt_raises_on_different_currency` | PASS |
| __le__ cross-currency raises ValueError | `TestMoneyCrossCurrencyComparison::test_le_raises_on_different_currency` | PASS |
| __gt__ cross-currency raises ValueError | `TestMoneyCrossCurrencyComparison::test_gt_raises_on_different_currency` | PASS |
| __ge__ cross-currency raises ValueError | `TestMoneyCrossCurrencyComparison::test_ge_raises_on_different_currency` | PASS |
| Error message names both currencies | `TestMoneyCrossCurrencyComparison::test_error_message_includes_both_currencies` | PASS |
| Any currency mismatch raises (parametrized x4) | `TestMoneyCrossCurrencyComparison::test_any_currency_mismatch_raises` | PASS |
| compare_at_price > price detectable | `TestMoneyCompareAtPriceInvariant::test_compare_at_price_greater_than_price_is_detectable` | PASS |
| compare_at_price == price detectable | `TestMoneyCompareAtPriceInvariant::test_compare_at_price_equal_to_price_is_detectable` | PASS |
| compare_at_price < price detectable | `TestMoneyCompareAtPriceInvariant::test_compare_at_price_less_than_price_is_detectable` | PASS |

## Acceptance criteria verification

From MT-1 definition in pm-spec.md:

- [x] ProductStatus enum has values: DRAFT, ENRICHING, READY_FOR_REVIEW, PUBLISHED, ARCHIVED -- tested by `test_all_expected_members_present`, `test_values_are_lowercase_strings`
- [x] Money is a frozen attrs dataclass with `amount: int` and `currency: str` -- tested by `test_create_with_valid_amount_and_currency`, `test_amount_cannot_be_mutated`
- [x] Money validates amount >= 0 and currency is exactly 3 characters -- tested by `TestMoneyValidation` class (10 tests)
- [x] Money has comparison methods (__lt__, __le__, __gt__, __ge__) for price validation -- tested by `TestMoneyOrdering` (12 tests) and `TestMoneyCrossCurrencyComparison` (9 tests)
- [x] All existing tests pass after this change -- full unit+architecture suite: 504 passed
- [x] Linter/type-checker passes -- verified by reviewer (APPROVED)

From arch/MT-1-plan.md acceptance checklist:

- [x] ProductStatus enum has exactly 5 values -- `test_has_exactly_five_members`
- [x] ProductStatus values match ORM enum strings exactly -- `test_values_are_lowercase_strings`
- [x] Money(-1, "RUB") raises ValueError -- `test_negative_amount_raises_value_error`
- [x] Money(100, "RU") raises ValueError -- `test_two_char_currency_raises`
- [x] Money(100, "RUBB") raises ValueError -- `test_four_char_currency_raises`
- [x] Money(100, "RUB") < Money(200, "RUB") returns True -- `test_lt_returns_true_when_less`
- [x] Money(100, "RUB") < Money(100, "USD") raises ValueError -- `test_lt_raises_on_different_currency`
- [x] Money(100, "RUB") == Money(100, "RUB") returns True -- `test_equal_same_amount_same_currency`
- [x] Money(100, "RUB") == Money(100, "USD") returns False -- `test_not_equal_different_currency`
- [x] Money(0, "RUB") is valid -- `test_zero_amount_is_valid`
- [x] Mutating Money fields raises FrozenInstanceError -- `test_amount_cannot_be_mutated`, `test_currency_cannot_be_mutated`
- [x] Domain layer has zero framework imports -- existing `test_domain_has_zero_framework_imports` architecture test passes

## Architecture tests

The existing `tests/architecture/test_boundaries.py` suite covers the domain purity rule for the catalog module. All architecture tests pass as part of the 504-test run. No new architecture test file was needed -- the existing parametrized rule `test_domain_has_zero_framework_imports[catalog]` already enforces the domain purity constraint that `value_objects.py` must not import sqlalchemy, fastapi, dishka, redis, taskiq, pydantic, or alembic.

## Test results

| Suite | Passed | Failed | Skipped |
|-------|--------|--------|---------|
| unit (test_value_objects.py only) | 63 | 0 | 0 |
| unit (full suite) | 490 | 0 | 0 |
| architecture | 14 | 0 | 0 |
| integration | skipped -- no infra changes in MT-1 | | |
| e2e | skipped -- no new endpoints in MT-1 | | |
| **TOTAL** | **504** | **0** | **0** |

## Coverage

`src/modules/catalog/domain/value_objects.py` coverage in the targeted test run: 64% (101 statements, 36 missed -- the uncovered lines are the pre-existing `validate_validation_rules` and `_validate_string_rules`/`_validate_numeric_rules` helpers which belong to the AttributeDataType feature, not MT-1). All ProductStatus and Money code paths are fully exercised.

## Verdict

**DONE** -- all 63 new tests pass, full unit+architecture suite (504 tests) passes, all MT-1 acceptance criteria verified, domain purity architecture constraint confirmed.
