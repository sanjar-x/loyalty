---
phase: 3
slug: product-aggregate-behavior
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-03-28
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property               | Value                                               |
| ---------------------- | --------------------------------------------------- |
| **Framework**          | pytest 9.0.2                                        |
| **Config file**        | `backend/pyproject.toml` [tool.pytest.ini_options]  |
| **Quick run command**  | `cd backend && uv run pytest tests/unit/modules/catalog/domain/test_product_aggregate.py -v --tb=short` |
| **Full suite command** | `cd backend && uv run pytest tests/unit/ -v --tb=short` |
| **Estimated runtime**  | ~2 seconds                                          |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && uv run pytest tests/unit/modules/catalog/domain/test_product_aggregate.py -v --tb=short`
- **After every plan wave:** Run `cd backend && uv run pytest tests/unit/ -v --tb=short`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
| ------- | ---- | ---- | ----------- | --------- | ----------------- | ----------- | ------ |
| 03-01-FSM-valid | 01 | 1 | DOM-02 | unit | `uv run pytest tests/unit/modules/catalog/domain/test_product_aggregate.py::TestProductFSMValid -x` | ❌ W0 | ⬜ pending |
| 03-01-FSM-invalid | 01 | 1 | DOM-02 | unit | `uv run pytest tests/unit/modules/catalog/domain/test_product_aggregate.py::TestProductFSMInvalid -x` | ❌ W0 | ⬜ pending |
| 03-01-FSM-readiness | 01 | 1 | DOM-02 | unit | `uv run pytest tests/unit/modules/catalog/domain/test_product_aggregate.py::TestProductFSMReadiness -x` | ❌ W0 | ⬜ pending |
| 03-01-FSM-guard | 01 | 1 | DOM-02 | unit | `uv run pytest tests/unit/modules/catalog/domain/test_product_aggregate.py -k setattr_guard -x` | ❌ W0 | ⬜ pending |
| 03-01-hash | 01 | 1 | DOM-03 | unit | `uv run pytest tests/unit/modules/catalog/domain/test_product_aggregate.py::TestVariantHashUniqueness -x` | ❌ W0 | ⬜ pending |
| 03-01-cascade | 01 | 1 | DOM-04 | unit | `uv run pytest tests/unit/modules/catalog/domain/test_product_aggregate.py::TestSoftDeleteCascade -x` | ❌ W0 | ⬜ pending |
| 03-01-pav | 01 | 1 | DOM-06 | unit | `uv run pytest tests/unit/modules/catalog/domain/test_product_aggregate.py::TestProductAttributeValue -x` | ❌ W0 | ⬜ pending |
| 03-01-events | 01 | 1 | DOM-07 | unit | `uv run pytest tests/unit/modules/catalog/domain/test_product_aggregate.py::TestProductDomainEvents -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/unit/modules/catalog/domain/test_product_aggregate.py` — covers DOM-02, DOM-03, DOM-04, DOM-06, DOM-07
- [ ] `backend/tests/unit/modules/catalog/domain/__init__.py` — empty marker if not present

*Existing test infrastructure (pytest, builders, conftest) covers all framework needs. No new fixtures required since these are pure unit tests.*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [x] All tasks have automated verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 5s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
