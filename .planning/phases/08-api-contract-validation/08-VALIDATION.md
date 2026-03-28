---
phase: 8
slug: api-contract-validation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-28
---

# Phase 8 -- Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property               | Value                                                |
| ---------------------- | ---------------------------------------------------- |
| **Framework**          | pytest 9.x + pytest-asyncio (auto mode)              |
| **Config file**        | `backend/pyproject.toml`                             |
| **Quick run command**  | `cd backend && python -m pytest tests/e2e/api/v1/catalog/ -x -q --timeout=30` |
| **Full suite command** | `cd backend && python -m pytest tests/e2e/ -q --timeout=60` |
| **Estimated runtime**  | ~45 seconds                                          |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && python -m pytest tests/e2e/api/v1/catalog/ -x -q --timeout=30`
- **After every plan wave:** Run `cd backend && python -m pytest tests/e2e/ -q --timeout=60`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 45 seconds

---

## Per-Task Verification Map

| Task ID   | Plan | Wave | Requirement | Test Type   | Automated Command | File Exists | Status     |
| --------- | ---- | ---- | ----------- | ----------- | ----------------- | ----------- | ---------- |
| 08-01-01  | 01   | 1    | API-01      | integration | `pytest tests/e2e/api/v1/catalog/test_brands.py -x -q` | TBD W1 | pending |
| 08-01-02  | 01   | 1    | API-01      | integration | `pytest tests/e2e/api/v1/catalog/test_categories.py -x -q` | TBD W1 | pending |
| 08-01-03  | 01   | 1    | API-01      | integration | `pytest tests/e2e/api/v1/catalog/test_attributes.py -x -q` | TBD W1 | pending |
| 08-01-04  | 01   | 1    | API-01      | integration | `pytest tests/e2e/api/v1/catalog/test_attribute_values.py -x -q` | TBD W1 | pending |
| 08-02-01  | 02   | 1    | API-01      | integration | `pytest tests/e2e/api/v1/catalog/test_attribute_templates.py -x -q` | TBD W1 | pending |
| 08-02-02  | 02   | 1    | API-01      | integration | `pytest tests/e2e/api/v1/catalog/test_products.py -x -q` | TBD W1 | pending |
| 08-02-03  | 02   | 1    | API-01      | integration | `pytest tests/e2e/api/v1/catalog/test_variants.py -x -q` | TBD W1 | pending |
| 08-02-04  | 02   | 1    | API-01      | integration | `pytest tests/e2e/api/v1/catalog/test_skus.py -x -q` | TBD W1 | pending |
| 08-02-05  | 02   | 1    | API-01      | integration | `pytest tests/e2e/api/v1/catalog/test_product_attributes.py -x -q` | TBD W1 | pending |
| 08-02-06  | 02   | 1    | API-01      | integration | `pytest tests/e2e/api/v1/catalog/test_media.py -x -q` | TBD W1 | pending |
| 08-03-01  | 03   | 2    | API-02      | integration | `pytest tests/e2e/api/v1/catalog/test_storefront.py -x -q` | TBD W2 | pending |
| 08-03-02  | 03   | 2    | API-03      | integration | `pytest tests/e2e/api/v1/catalog/test_auth_enforcement.py -x -q` | TBD W2 | pending |
| 08-03-03  | 03   | 2    | API-04      | integration | `pytest tests/e2e/api/v1/catalog/test_lifecycle.py -x -q` | TBD W2 | pending |
| 08-03-04  | 03   | 2    | API-05      | integration | `pytest tests/e2e/api/v1/catalog/test_pagination.py -x -q` | TBD W2 | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/e2e/api/v1/catalog/__init__.py` -- empty marker for pytest discovery
- [ ] `backend/tests/e2e/api/v1/catalog/conftest.py` -- shared helper fixtures (create_brand, create_category, etc.)

*Existing infrastructure (conftest.py with admin_client, db_session, Redis isolation) covers base requirements.*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have automated verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 45s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
