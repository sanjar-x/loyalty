---
phase: 7
slug: repository-data-integrity
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-28
---

# Phase 7 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property               | Value                                                                  |
| ---------------------- | ---------------------------------------------------------------------- |
| **Framework**          | pytest 9.x + pytest-asyncio + testcontainers (PostgreSQL)              |
| **Config file**        | `backend/pyproject.toml` ([tool.pytest.ini_options])                   |
| **Quick run command**  | `cd backend && python -m pytest tests/integration/modules/catalog/infrastructure/repositories/ -x -q --timeout=60` |
| **Full suite command** | `cd backend && python -m pytest tests/integration/ -x -q --timeout=120` |
| **Estimated runtime**  | ~30 seconds (requires running PostgreSQL container)                    |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && python -m pytest tests/integration/modules/catalog/infrastructure/repositories/ -x -q --timeout=60`
- **After every plan wave:** Run `cd backend && python -m pytest tests/integration/ -x -q --timeout=120`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID   | Plan | Wave | Requirement | Test Type   | Automated Command | File Exists | Status    |
| --------- | ---- | ---- | ----------- | ----------- | ----------------- | ----------- | --------- |
| 07-01-01  | 01   | 1    | REPO-01     | integration | `pytest tests/integration/.../test_product.py -v` | ❌ W0 | ⬜ pending |
| 07-01-02  | 01   | 1    | REPO-05     | integration | `pytest tests/integration/.../test_product.py -v` | ❌ W0 | ⬜ pending |
| 07-02-01  | 02   | 1    | REPO-02     | integration | `pytest tests/integration/.../test_attribute.py -v` | ❌ W0 | ⬜ pending |
| 07-02-02  | 02   | 1    | REPO-02     | integration | `pytest tests/integration/.../test_attribute_template.py -v` | ❌ W0 | ⬜ pending |
| 07-03-01  | 03   | 2    | REPO-03     | integration | `pytest tests/integration/.../test_schema_constraints.py -v` | ❌ W0 | ⬜ pending |
| 07-03-02  | 03   | 2    | REPO-04     | integration | `pytest tests/integration/.../test_soft_delete.py -v` | ❌ W0 | ⬜ pending |

---

## Wave 0 Requirements

- [ ] `backend/tests/integration/modules/catalog/infrastructure/repositories/test_product.py` -- stubs for REPO-01, REPO-05
- [ ] `backend/tests/integration/modules/catalog/infrastructure/repositories/test_attribute.py` -- stubs for REPO-02
- [ ] `backend/tests/integration/modules/catalog/infrastructure/repositories/test_schema_constraints.py` -- stubs for REPO-03
- [ ] `backend/tests/integration/modules/catalog/infrastructure/repositories/test_soft_delete.py` -- stubs for REPO-04
- [ ] Currency seed fixture ("RUB" in currencies table) -- required for Product/SKU tests

*Existing infrastructure covers: db_session fixture with nested-transaction rollback, ORM factories, query counter utility.*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
