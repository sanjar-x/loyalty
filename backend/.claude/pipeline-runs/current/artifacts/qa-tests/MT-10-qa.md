# QA Report -- MT-10: Add ChangeProductStatus command handler

> **QA Engineer:** senior-qa (10/10)
> **Verdict:** DONE

---

## Test files created

- `tests/unit/modules/catalog/application/commands/test_change_product_status.py` -- 39 tests

## Scenarios covered

| Scenario                     | Test                                                  | Result |
| ---------------------------- | ----------------------------------------------------- | ------ |
| Happy path                   | `test_product_status_is_updated`                      | PASS   |
| Happy path                   | `test_calls_repo_get_with_product_id`                 | PASS   |
| Happy path                   | `test_calls_repo_update_with_product`                 | PASS   |
| Happy path                   | `test_calls_uow_commit_once`                          | PASS   |
| Happy path                   | `test_uow_used_as_context_manager`                    | PASS   |
| Happy path                   | `test_returns_none`                                   | PASS   |
| Not found                    | `test_raises_product_not_found_error`                 | PASS   |
| Not found                    | `test_error_contains_product_id`                      | PASS   |
| Not found                    | `test_repo_update_not_called`                         | PASS   |
| Not found                    | `test_commit_not_called`                              | PASS   |
| Invalid transition           | `test_draft_to_published_raises_error`                | PASS   |
| Invalid transition           | `test_draft_to_archived_raises_error`                 | PASS   |
| Invalid transition           | `test_published_to_draft_raises_error`                | PASS   |
| Invalid transition           | `test_invalid_transition_does_not_commit`             | PASS   |
| Invalid transition           | `test_invalid_transition_does_not_update`             | PASS   |
| Edge case (self-loop)        | `test_same_status_raises_error`                       | PASS   |
| Command DTO                  | `test_fields_stored_correctly`                        | PASS   |
| Command DTO                  | `test_command_is_frozen`                              | PASS   |
| All valid FSM transitions    | 7 parametrized cases                                  | PASS   |
| All invalid FSM transitions  | 14 parametrized cases                                 | PASS   |

## Test results

| Suite | Passed | Failed | Skipped |
| ----- | ------ | ------ | ------- |
| unit  | 39     | 0      | 0       |

## Verdict

**DONE** -- all 39 tests pass in 2.97s.
