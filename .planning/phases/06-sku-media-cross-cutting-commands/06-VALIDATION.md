---
phase: 6
slug: sku-media-cross-cutting-commands
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-03-28
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property               | Value                                                                 |
| ---------------------- | --------------------------------------------------------------------- |
| **Framework**          | pytest 9.x with pytest-asyncio (mode: auto)                          |
| **Config file**        | `backend/pyproject.toml`                                              |
| **Quick run command**  | `cd backend && uv run pytest tests/unit/modules/catalog/application/commands/ -x --no-cov -q` |
| **Full suite command** | `cd backend && uv run pytest tests/unit/ -x --no-cov -q`             |
| **Estimated runtime**  | ~5 seconds                                                            |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && uv run pytest tests/unit/modules/catalog/application/commands/ -x --no-cov -q`
- **After every plan wave:** Run `cd backend && uv run pytest tests/unit/ -x --no-cov -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID   | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status    |
| --------- | ---- | ---- | ----------- | --------- | ----------------- | ----------- | --------- |
| 06-01-01  | 01   | 1    | CMD-06      | unit      | `cd backend && uv run pytest tests/unit/modules/catalog/application/commands/test_sku_handlers.py -x --no-cov -q` | ❌ W0 | ⬜ pending |
| 06-01-02  | 01   | 1    | CMD-06      | unit      | `cd backend && uv run pytest tests/unit/modules/catalog/application/commands/test_sku_handlers.py -x --no-cov -q` | ❌ W0 | ⬜ pending |
| 06-02-01  | 02   | 1    | CMD-07      | unit      | `cd backend && uv run pytest tests/unit/modules/catalog/application/commands/test_media_handlers.py -x --no-cov -q` | ❌ W0 | ⬜ pending |
| 06-02-02  | 02   | 1    | CMD-07      | unit      | `cd backend && uv run pytest tests/unit/modules/catalog/application/commands/test_media_handlers.py -x --no-cov -q` | ❌ W0 | ⬜ pending |
| 06-03-01  | 03   | 2    | CMD-08, CMD-09, CMD-10 | unit | `cd backend && uv run pytest tests/unit/modules/catalog/application/commands/test_cross_cutting.py -x --no-cov -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/fakes/fake_catalog_repos.py` — implement FakeMediaAssetRepository.bulk_update_sort_order and check_main_exists
- [ ] Verify FakeTemplateAttributeBindingRepository.get_bindings_for_templates is implemented (needed by GenerateSKUMatrixHandler)

*Existing infrastructure covers all other phase requirements.*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 10s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
