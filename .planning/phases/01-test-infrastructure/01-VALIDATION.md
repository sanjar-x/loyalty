---
phase: 1
slug: test-infrastructure
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-28
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property               | Value                                               |
| ---------------------- | --------------------------------------------------- |
| **Framework**          | pytest 9.0.2 + pytest-asyncio 1.3.0                |
| **Config file**        | `backend/pytest.ini` + `backend/pyproject.toml`     |
| **Quick run command**  | `cd backend && uv run pytest tests/unit -x -q --no-cov --timeout=30` |
| **Full suite command** | `cd backend && uv run pytest --timeout=60`          |
| **Estimated runtime**  | ~15 seconds                                         |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && uv run pytest tests/unit -x -q --no-cov --timeout=30`
- **After every plan wave:** Run `cd backend && uv run pytest --timeout=60`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID   | Plan | Wave | Requirement | Test Type   | Automated Command | File Exists | Status    |
| --------- | ---- | ---- | ----------- | ----------- | ----------------- | ----------- | --------- |
| INFRA-01  | 01   | 1    | INFRA-01    | unit/smoke  | `cd backend && uv run python -c "import hypothesis; import schemathesis; import respx; import dirty_equals; import pytest_randomly; import pytest_timeout"` | N/A | ⬜ pending |
| INFRA-02  | 02   | 1    | INFRA-02    | unit        | `cd backend && uv run pytest tests/unit/test_builders_smoke.py -x --no-cov` | ❌ W0 | ⬜ pending |
| INFRA-03  | 03   | 1    | INFRA-03    | unit        | `cd backend && uv run pytest tests/unit/test_fake_uow_smoke.py -x --no-cov` | ❌ W0 | ⬜ pending |
| INFRA-04  | 04   | 1    | INFRA-04    | unit        | `cd backend && uv run pytest tests/unit/test_strategies_smoke.py -x --no-cov --timeout=30` | ❌ W0 | ⬜ pending |
| INFRA-05  | 05   | 1    | INFRA-05    | integration | `cd backend && uv run pytest tests/integration/test_query_counter_smoke.py -x --no-cov` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/test_builders_smoke.py` — smoke tests that each builder produces a valid entity
- [ ] `tests/unit/test_fake_uow_smoke.py` — smoke test that FakeUoW commit/rollback/event collection works
- [ ] `tests/unit/test_strategies_smoke.py` — smoke test that each hypothesis strategy generates valid instances
- [ ] `tests/integration/test_query_counter_smoke.py` — smoke test that query counter counts correctly in nested-transaction context

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
