---
phase: 5
slug: product-variant-command-handlers
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-28
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property               | Value                                                                              |
| ---------------------- | ---------------------------------------------------------------------------------- |
| **Framework**          | pytest 9.x with pytest-asyncio (mode: auto)                                       |
| **Config file**        | `backend/pyproject.toml`                                                           |
| **Quick run command**  | `cd backend && uv run pytest tests/unit/modules/catalog/application/commands/ -x`  |
| **Full suite command** | `cd backend && uv run pytest tests/unit/modules/catalog/ -x --timeout=30`          |
| **Estimated runtime**  | ~5 seconds                                                                         |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && uv run pytest tests/unit/modules/catalog/application/commands/ -x`
- **After every plan wave:** Run `cd backend && uv run pytest tests/unit/modules/catalog/ -x --timeout=30`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID   | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status    |
| --------- | ---- | ---- | ----------- | --------- | ----------------- | ----------- | --------- |
| 05-01-01  | 01   | 1    | CMD-04      | unit      | `uv run pytest tests/unit/modules/catalog/application/commands/test_product_handlers.py -x` | ❌ W0 | ⬜ pending |
| 05-01-02  | 01   | 1    | CMD-04      | unit      | `uv run pytest tests/unit/modules/catalog/application/commands/test_product_handlers.py -x` | ❌ W0 | ⬜ pending |
| 05-02-01  | 02   | 1    | CMD-05      | unit      | `uv run pytest tests/unit/modules/catalog/application/commands/test_variant_handlers.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending / ✅ green / ❌ red / ⚠ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/unit/modules/catalog/application/commands/__init__.py` — package marker for test discovery
- [ ] Fix `FakeTemplateAttributeBindingRepository.get_bindings_for_templates()` — currently raises NotImplementedError, needed by attribute assignment handler tests

*Existing infrastructure (FakeUoW, builders, fake repos) covers most phase requirements. Only the binding repo method and directory creation are needed.*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
