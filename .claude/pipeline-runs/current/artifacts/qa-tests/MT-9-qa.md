# QA Report -- MT-9: Add DeleteProduct command handler

> **QA Engineer:** senior-qa (10/10)
> **Verdict:** DONE

---

## Test files created

- `tests/unit/modules/catalog/application/commands/test_delete_product.py` -- 14 tests

## Scenarios covered

| Scenario                    | Test                                    | Result |
| --------------------------- | --------------------------------------- | ------ |
| Happy path                  | `test_calls_repo_get_with_correct_id`   | PASS   |
| Soft delete invoked         | `test_calls_soft_delete_on_product`     | PASS   |
| Repo update called          | `test_calls_repo_update_with_product`   | PASS   |
| UoW commit called           | `test_calls_uow_commit_once`           | PASS   |
| Returns None                | `test_returns_none`                     | PASS   |
| Context manager usage       | `test_uow_used_as_context_manager`     | PASS   |
| Ordering: delete before update | `test_soft_delete_called_before_update` | PASS |
| Ordering: update before commit | `test_update_called_before_commit`     | PASS   |
| Not found                   | `test_raises_product_not_found_error`  | PASS   |
| Error contains product_id   | `test_error_contains_product_id`       | PASS   |
| No update on not found      | `test_repo_update_not_called`          | PASS   |
| No commit on not found      | `test_commit_not_called`               | PASS   |
| Command stores product_id   | `test_stores_product_id`               | PASS   |
| Command is frozen            | `test_command_is_frozen`               | PASS   |

## Test results

| Suite | Passed | Failed | Skipped |
| ----- | ------ | ------ | ------- |
| unit  | 14     | 0      | 0       |

## Verdict

**DONE** -- all 14 tests pass in 2.96s.
