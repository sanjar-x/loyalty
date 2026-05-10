# Sprint 4 — final pre-launch sprint

**Period**: 2026-05-10 →
**Goal**: close all deferred items + production deploy hardening.
**Status**: in-flight.

## Phase 1 — deferred items close

| Task | Title | Status | Commit |
| --- | --- | --- | --- |
| T-1.1 | Brand ETag/If-Match | ✅ committed | a1585788 |
| T-1.2 | Category ETag/If-Match | ✅ committed | 780504af |
| T-1.3 | ProductVariant ETag/If-Match | ✅ committed | c1ae4b05 |
| T-1.4 | SKU ETag/If-Match | ✅ committed | 56a233a2 |
| T-2 | Telegram bot push consumer (shipment events) | ✅ committed | fc0f6f18 |
| T-3 | Activity enrichment (favorites events) | ⏳ in-flight | — |

## Phase 2 — pre-launch hardening

| Task | Title | Status | Commit |
| --- | --- | --- | --- |
| T-4 | Secrets rotation playbook + .env.example finalization | pending | — |
| T-5 | Deploy playbook + rollback procedure | pending | — |
| T-6 | Production readiness checklist + findings | pending | — |

## Phase 3 — optional polishing

| Task | Title | Status | Commit |
| --- | --- | --- | --- |
| T-7 | Product mutations SSE channel (C4.2 deferred) | optional | — |

## Notes

* Frontend Sprint 3 part 2 runs in parallel — Phase C (a11y/perf/i18n)
  switches to Phase B (logistics shipments admin UI) at the next
  breakpoint. Backend coordination signals after each merged T-1.* —
  Frontend ETag interceptor automatically picks up new ``ETag``/
  ``If-Match`` endpoints without code changes.
* MVP launch is "ready when ready" — Sprint 4 is the final tuning pass.
