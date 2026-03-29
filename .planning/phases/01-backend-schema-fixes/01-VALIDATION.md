---
phase: 1
slug: backend-schema-fixes
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-29
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >=9.0.2 with pytest-asyncio (mode: auto) |
| **Config file** | `backend/pyproject.toml` [tool.pytest.ini_options] |
| **Quick run command** | `cd backend && uv run pytest tests/ -x -q --timeout=30` |
| **Full suite command** | `cd backend && uv run pytest tests/ --timeout=60` |
| **Estimated runtime** | ~15 seconds (unit), ~60 seconds (integration with testcontainers) |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && uv run pytest tests/ -x -q --timeout=30`
- **After every plan wave:** Run `cd backend && uv run pytest tests/ --timeout=60`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 1 | BKND-01 | integration | `uv run pytest tests/ -k "product" -x` | ✅ existing | ⬜ pending |
| 01-01-02 | 01 | 1 | BKND-02 | integration | `uv run pytest tests/ -k "product" -x` | ✅ existing | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. No new test framework or fixtures needed.

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
