# Sprint 3 — Tracker (live)

> Updated as each task lands. Frontend should poll this between
> mini-tasks; the **Frontend trigger** column tells the parallel
> session what to do next.

## Phase 1 — Catch-up Sprint 2

| Task | Status | Commit | Frontend trigger |
| --- | --- | --- | --- |
| D0.1 C-5 (enrichment) | ⏳ in progress | — | recipientSnapshot ready → drop `TODO(backend-gap)` in OrderDetailsView; enums + `_meta` ready → swap provisional taxonomy in ForceCancelModal/HoldResumeModal |
| D0.2 C-6 PC-201c | ⏳ pending | — | none — internal hygiene |
| D0.3 C4.1 remaining 5 entity | ⏳ pending | — | F-5 ETag interceptor unblocked for Brand/Category/Variant/SKU/Recipient |

## Phase 2 — Pre-launch hardening

| Task | Status | Commit | Frontend trigger |
| --- | --- | --- | --- |
| D1.1 cart freeze cron | ⏳ pending | — | none — silent UX fix |
| D1.2 async DobroPost booking | ⏳ pending | — | Sprint 3 Logistics admin UI: procure returns 204 immediately; add `BOOKING_FAILED` HoldReason + poll on shipment_id |
| D1.3 Recipient validation fix | ⏳ pending | — | none — internal correctness |

## Phase 3 — Observability

| Task | Status | Commit |
| --- | --- | --- |
| D2.1 outbox lag metric | ⏳ pending | — |
| D2.2 DLQ growth alerting | ⏳ pending | — |
| D2.3 PII redaction | ⏳ pending | — |

## Phase 4 — Optional

| Task | Status | Notes |
| --- | --- | --- |
| D3.1 Telegram bot push | ⏳ pending | only if Phase 1-3 wraps with margin |
| D3.2 Favorites → activity | ⏳ pending | same |
| D3.3 Product mutations SSE | ⏳ deferred | confirmed not blocking |

## Notes for the Frontend session

* Sprint 2 OpenAPI snapshot already up to date (228 paths, 158 admin)
  — no need to regenerate before D0.1 lands. After D0.1 the snapshot
  will gain enums + `_meta` endpoint; I'll ping here.
* `frontend/admin/openapi/*.json` files are still uncommitted in the
  submodule — please commit them at your earliest convenience so my
  next `make openapi-sync` doesn't conflict.
