---
phase: 4
slug: brand-category-attribute-command-handlers
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-28
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property               | Value                                               |
| ---------------------- | --------------------------------------------------- |
| **Framework**          | pytest 9.0.2 + pytest-asyncio (auto mode)           |
| **Config file**        | `backend/pytest.ini`                                |
| **Quick run command**  | `cd backend && uv run pytest tests/unit/modules/catalog/application/commands/ -x --no-cov -q` |
| **Full suite command** | `cd backend && uv run pytest tests/unit/ -x --no-cov -q` |
| **Estimated runtime**  | ~10 seconds                                         |

---

## Sampling Rate

- **After every task commit:** Run quick command
- **After every plan wave:** Run full suite command
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status    |
| ------- | ---- | ---- | ----------- | --------- | ----------------- | ----------- | --------- |
| CMD-01 | 01 | 1 | CMD-01 | unit | `cd backend && uv run pytest tests/unit/modules/catalog/application/commands/test_brand_handlers.py -x --no-cov -q` | ❌ W0 | ⬜ pending |
| CMD-02 | 02 | 1 | CMD-02 | unit | `cd backend && uv run pytest tests/unit/modules/catalog/application/commands/test_category_handlers.py -x --no-cov -q` | ❌ W0 | ⬜ pending |
| CMD-03 | 03 | 1 | CMD-03 | unit | `cd backend && uv run pytest tests/unit/modules/catalog/application/commands/test_attribute_handlers.py -x --no-cov -q` | ❌ W0 | ⬜ pending |

---

## Wave 0 Requirements

- [ ] `tests/unit/modules/catalog/application/commands/test_brand_handlers.py`
- [ ] `tests/unit/modules/catalog/application/commands/test_category_handlers.py`
- [ ] `tests/unit/modules/catalog/application/commands/test_attribute_handlers.py`
- [ ] Implement 7 NotImplementedError methods in fake_catalog_repos.py

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
