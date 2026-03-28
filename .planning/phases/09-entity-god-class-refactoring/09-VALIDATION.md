---
phase: 9
slug: entity-god-class-refactoring
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-28
---

# Phase 9 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property               | Value                                                        |
| ---------------------- | ------------------------------------------------------------ |
| **Framework**          | pytest >=9.0.2 with pytest-asyncio                           |
| **Config file**        | `backend/pyproject.toml`                                     |
| **Quick run command**  | `cd backend && python -m pytest tests/unit/modules/catalog/domain/ -x -q` |
| **Full suite command** | `cd backend && python -m pytest tests/ -x -q`                |
| **Estimated runtime**  | ~30 seconds (unit), ~120 seconds (full with integration)     |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && python -m pytest tests/unit/modules/catalog/domain/ -x -q`
- **After every plan wave:** Run `cd backend && python -m pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 120 seconds

---

## Per-Task Verification Map

| Task ID   | Plan | Wave | Requirement | Test Type  | Automated Command | File Exists | Status    |
| --------- | ---- | ---- | ----------- | ---------- | ----------------- | ----------- | --------- |
| 09-01-01  | 01   | 1    | REF-01      | structural | `test -d backend/src/modules/catalog/domain/entities && echo OK` | N/A (creates dir) | ⬜ pending |
| 09-01-02  | 01   | 1    | REF-01      | structural | `python -c "from src.modules.catalog.domain.entities._common import _validate_slug"` | N/A (creates file) | ⬜ pending |
| 09-01-03  | 01   | 1    | REF-01      | unit       | `cd backend && python -m pytest tests/unit/modules/catalog/domain/ -x -q` | ✅ existing | ⬜ pending |
| 09-02-01  | 02   | 1    | REF-02      | import     | `python -c "from src.modules.catalog.domain.entities import Brand, Category, Product"` | N/A (creates file) | ⬜ pending |
| 09-02-02  | 02   | 1    | REF-03      | full suite | `cd backend && python -m pytest tests/ -x -q` | ✅ existing | ⬜ pending |

*Status: ⬜ pending . ✅ green . ❌ red . ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. The full test suite from Phases 1-8 serves as the safety net — no new test files needed for this refactoring phase.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
| -------- | ----------- | ---------- | ----------------- |
| Stale `__pycache__` cleanup | REF-03 | Bytecode cache may retain old module paths | Delete all `__pycache__` dirs under `backend/src/modules/catalog/domain/` before test run |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 120s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
