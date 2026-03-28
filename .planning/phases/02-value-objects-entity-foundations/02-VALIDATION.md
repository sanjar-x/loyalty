---
phase: 2
slug: value-objects-entity-foundations
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-28
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property               | Value                                               |
| ---------------------- | --------------------------------------------------- |
| **Framework**          | pytest 9.0.2                                        |
| **Config file**        | `backend/pytest.ini`                                |
| **Quick run command**  | `cd backend && uv run pytest tests/unit/modules/catalog/domain/ -x -q --no-cov` |
| **Full suite command** | `cd backend && uv run pytest tests/unit/ -x -q --no-cov` |
| **Estimated runtime**  | ~10 seconds                                         |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && uv run pytest tests/unit/modules/catalog/domain/ -x -q --no-cov`
- **After every plan wave:** Run `cd backend && uv run pytest tests/unit/ -x -q --no-cov`
- **Before `/gsd:verify-work`:** Full unit suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status    |
| ------- | ---- | ---- | ----------- | --------- | ----------------- | ----------- | --------- |
| DOM-01-brand | 01 | 1 | DOM-01 | unit | `cd backend && uv run pytest tests/unit/modules/catalog/domain/test_brand.py -x --no-cov` | ❌ W0 | ⬜ pending |
| DOM-01-category | 01 | 1 | DOM-01 | unit | `cd backend && uv run pytest tests/unit/modules/catalog/domain/test_category.py -x --no-cov` | ❌ W0 | ⬜ pending |
| DOM-01-product | 02 | 1 | DOM-01 | unit | `cd backend && uv run pytest tests/unit/modules/catalog/domain/test_product.py -x --no-cov` | ❌ W0 | ⬜ pending |
| DOM-01-variant | 02 | 1 | DOM-01 | unit | `cd backend && uv run pytest tests/unit/modules/catalog/domain/test_variant.py -x --no-cov` | ❌ W0 | ⬜ pending |
| DOM-01-sku | 02 | 1 | DOM-01 | unit | `cd backend && uv run pytest tests/unit/modules/catalog/domain/test_sku.py -x --no-cov` | ❌ W0 | ⬜ pending |
| DOM-01-attr | 03 | 2 | DOM-01 | unit | `cd backend && uv run pytest tests/unit/modules/catalog/domain/test_attribute.py -x --no-cov` | ❌ W0 | ⬜ pending |
| DOM-01-template | 03 | 2 | DOM-01 | unit | `cd backend && uv run pytest tests/unit/modules/catalog/domain/test_attribute_template.py -x --no-cov` | ❌ W0 | ⬜ pending |
| DOM-01-group | 03 | 2 | DOM-01 | unit | `cd backend && uv run pytest tests/unit/modules/catalog/domain/test_attribute_group.py -x --no-cov` | ❌ W0 | ⬜ pending |
| DOM-05-vo | 01 | 1 | DOM-05 | unit | `cd backend && uv run pytest tests/unit/modules/catalog/domain/test_value_objects.py -x --no-cov` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/modules/catalog/domain/test_brand.py`
- [ ] `tests/unit/modules/catalog/domain/test_category.py`
- [ ] `tests/unit/modules/catalog/domain/test_product.py`
- [ ] `tests/unit/modules/catalog/domain/test_variant.py`
- [ ] `tests/unit/modules/catalog/domain/test_sku.py`
- [ ] `tests/unit/modules/catalog/domain/test_attribute.py`
- [ ] `tests/unit/modules/catalog/domain/test_attribute_template.py`
- [ ] `tests/unit/modules/catalog/domain/test_attribute_group.py`
- [ ] `tests/unit/modules/catalog/domain/test_value_objects.py`

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
