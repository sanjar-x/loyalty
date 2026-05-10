# Sprint 4 — final pre-launch sprint

**Period**: 2026-05-10 → 2026-05-10 (closed in one session).
**Goal**: close all deferred items + production deploy hardening.
**Status**: ready for merge — 9 commits across 2 mandatory phases.

## Phase 1 — deferred items close

| Task | Title | Status | Commit |
| --- | --- | --- | --- |
| T-1.1 | Brand ETag/If-Match | ✅ committed | a1585788 |
| T-1.2 | Category ETag/If-Match | ✅ committed | 780504af |
| T-1.3 | ProductVariant ETag/If-Match | ✅ committed | c1ae4b05 |
| T-1.4 | SKU ETag/If-Match | ✅ committed | 56a233a2 |
| T-2 | Telegram bot push consumer (shipment events) | ✅ committed | fc0f6f18 |
| T-3 | Activity enrichment (favorites events) | ✅ committed | 27e49b6d |

## Phase 2 — pre-launch hardening

| Task | Title | Status | Commit |
| --- | --- | --- | --- |
| T-4 | Secrets rotation playbook + .env.example finalization | ✅ committed | 1a2d1013 |
| T-5 | Deploy playbook + rollback procedure | ✅ committed | 587c84de |
| T-6 | Production readiness checklist + findings | ✅ committed | b6da488a |

## Phase 3 — optional polishing

| Task | Title | Status | Commit |
| --- | --- | --- | --- |
| T-7 | Product mutations SSE channel (C4.2 deferred) | deferred | Sprint 5 backlog |

T-7 deferred to Sprint 5 — Phase 1+2 closed all release-blocking
items, and Frontend Sprint 3 part 2 confirmed C4.2 is not on the
launch path. Same recipe as the SKU pricing SSE bridge already in
place (CAT-005) so picking it up later is mechanical.

## Notes

* Frontend Sprint 3 part 2 runs in parallel — Phase C (a11y/perf/i18n)
  switches to Phase B (logistics shipments admin UI) at the next
  breakpoint. Backend coordination signals after each merged T-1.* —
  Frontend ETag interceptor automatically picks up new ``ETag``/
  ``If-Match`` endpoints without code changes.
* MVP launch is "ready when ready" — Sprint 4 is the final tuning pass.

## Sprint 5 backlog (carried over)

* **T-7 Product mutations SSE channel (C4.2)** — bridge product /
  variant / sku / media mutation events into a per-product Redis
  pub/sub channel for cross-tab admin sync. Recipe identical to the
  SKU pricing SSE bridge (`SKUPricedEvent` → `publish_sku_pricing_status`).
* **JWT RS256 migration** — replace HS256 single-secret signing with
  RS256 + key-rotation friendly. Out-of-scope for MVP; touched on
  in `docs/secrets-rotation.md §2.1`.
* **Pre-launch yellows close-out** — see
  `docs/production-readiness-findings-2026-05.md` summary (7 items,
  all release-day TL-actionable per `docs/deploy-playbook.md §1`).
