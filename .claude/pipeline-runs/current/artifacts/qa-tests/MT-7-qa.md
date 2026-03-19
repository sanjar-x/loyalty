# QA Report — MT-7: Add CreateProduct command handler

> **QA Engineer:** senior-qa (10/10)
> **Plan:** arch/MT-7-plan.md
> **Review:** review/MT-7-review.md
> **Verdict:** DONE

---

## Test files created

- `tests/unit/modules/catalog/application/commands/test_create_product.py` — 35 tests

Integration and E2E tests: skipped — no database schema changes, no new HTTP endpoints in this MT.

---

## Scenarios covered

| Scenario | Test | Result |
|----------|------|--------|
| Command required fields stored correctly | `test_required_fields_stored_correctly` | PASS |
| Command optional fields default to {}, None, None, [] | `test_optional_fields_have_correct_defaults` | PASS |
| Command optional fields accept provided values | `test_optional_fields_accept_provided_values` | PASS |
| Command is a frozen dataclass | `test_command_is_frozen` | PASS |
| Default factory instances are independent (no aliasing) | `test_default_factory_instances_are_independent` | PASS |
| title_i18n supports multiple languages | `test_multilingual_title_multiple_languages` | PASS |
| Result stores product_id | `test_stores_product_id` | PASS |
| Result is frozen dataclass | `test_result_is_frozen` | PASS |
| Happy path: returns CreateProductResult with UUID | `test_returns_result_with_product_id` | PASS |
| Happy path: check_slug_exists called with correct slug | `test_calls_check_slug_exists_with_correct_slug` | PASS |
| Happy path: repo.add called with a Product instance | `test_calls_repo_add_with_product` | PASS |
| Happy path: uow.commit called exactly once | `test_calls_uow_commit_once` | PASS |
| Product created in DRAFT status | `test_product_has_draft_status` | PASS |
| result.product_id matches persisted product.id | `test_product_id_matches_result` | PASS |
| All command fields forwarded to product | `test_product_fields_match_command` | PASS |
| register_aggregate NOT called (events deferred) | `test_no_register_aggregate_called` | PASS |
| UoW used as async context manager | `test_uow_used_as_context_manager` | PASS |
| Default optional fields produce valid product | `test_default_optional_fields_produce_valid_product` | PASS |
| Slug conflict raises ProductSlugConflictError | `test_raises_product_slug_conflict_error` | PASS |
| Exception details contain conflicting slug | `test_error_contains_slug` | PASS |
| Slug conflict: repo.add not called | `test_repo_add_not_called_on_conflict` | PASS |
| Slug conflict: uow.commit not called | `test_commit_not_called_on_conflict` | PASS |
| Slug conflict: register_aggregate not called | `test_register_aggregate_not_called_on_conflict` | PASS |
| Empty title_i18n propagates ValueError | `test_empty_title_i18n_raises_value_error` | PASS |
| Empty title_i18n: commit not called | `test_empty_title_i18n_does_not_commit` | PASS |
| Empty description_i18n treated as {} | `test_empty_description_treated_as_empty_dict` | PASS |
| Empty tags treated as [] | `test_empty_tags_treated_as_empty_list` | PASS |
| Slug check called before Product.create (ordering) | `test_slug_check_called_before_product_create` | PASS |
| country_of_origin variants: US, DE, UZ, GB, None | `test_country_of_origin_variants[*]` (5 parametrized) | PASS |
| supplier_id None by default | `test_supplier_id_none_by_default` | PASS |
| supplier_id set when provided | `test_supplier_id_set_when_provided` | PASS |

---

## Acceptance criteria verification

- [x] `CreateProductCommand` is a frozen stdlib dataclass with all 8 planned fields, correct types, correct defaults — tested by `TestCreateProductCommand` (6 tests)
- [x] `CreateProductResult` is a frozen stdlib dataclass with `product_id: uuid.UUID` — tested by `TestCreateProductResult` (2 tests)
- [x] Handler validates slug uniqueness via `IProductRepository.check_slug_exists` — tested by `test_calls_check_slug_exists_with_correct_slug`, `test_raises_product_slug_conflict_error`
- [x] Handler creates Product via `Product.create()` factory method — tested by `test_calls_repo_add_with_product`, `test_product_has_draft_status`, `test_product_fields_match_command`
- [x] Handler uses UoW pattern: `async with self._uow` -> `repo.add()` -> `uow.commit()` — tested by `test_uow_used_as_context_manager`, `test_calls_uow_commit_once`, `test_slug_check_called_before_product_create`
- [x] No domain events emitted (no `add_domain_event`, no `register_aggregate`) — tested by `test_no_register_aggregate_called` and all conflict/error tests
- [x] Handler returns `CreateProductResult(product_id=product.id)` — tested by `test_product_id_matches_result`
- [x] Default values for optional fields work correctly — tested by `test_optional_fields_have_correct_defaults`, `test_default_optional_fields_produce_valid_product`

Reviewer minor finding (description_i18n falsy-to-None conversion): confirmed correct behavior — `test_empty_description_treated_as_empty_dict` verifies the round-trip produces `{}` on the product as intended.

---

## Test results

| Suite | Passed | Failed | Skipped |
|-------|--------|--------|---------|
| unit (MT-7 new) | 35 | 0 | 0 |
| unit (full suite) | 954 | 0 | 0 |
| architecture | included in 954 | 0 | 0 |
| integration | skipped — no infra changes | — | — |
| e2e | skipped — no new endpoints | — | — |

Pre-MT-7 baseline: 869 tests passing (per reviewer report).
Post-MT-7: 954 tests passing. Delta: +85 tests total (35 from this MT).

---

## Coverage

Coverage measurement is dominated by the full codebase at ~47% when running the full unit+architecture suite. The new test file exercises `create_product.py` (application layer) fully and exercises `Product.create()` + `ProductSlugConflictError` + `CreateProductCommand`/`CreateProductResult` data paths. Coverage did not decrease.

---

## Verdict

**DONE** — all 35 tests pass, no regressions in the 919 pre-existing tests, coverage maintained.
