# Sprint 3 — Tracker (live)

> Final state. Frontend should pull this for the canonical commit list
> + per-task action items. Sprint 4 picks up the deferred entries
> documented in `sprint-3-deferred.md`.

## Phase 1 — Catch-up Sprint 2

| Task | Status | Commit | Frontend trigger |
| --- | --- | --- | --- |
| D0.1 C-5 (enrichment) | ✅ done | `ec8581d1` | **GO** — drop `TODO(backend-gap)` in OrderDetailsView; swap provisional taxonomy in ForceCancelModal / HoldResumeModal for the typed enums + `_meta` endpoint. |
| D0.2 C-6 PC-201c | ✅ done | `20cf66a0` | none — internal hygiene; pre-push hook now runs the full unit suite (1778 tests). |
| D0.3 C4.1 remaining 5 entity | 🟡 partial | `e16ca1de` | **Recipient ready** for F-5 ETag interceptor. Brand / Category / Variant deferred (`docs/sprint-3-deferred.md`) — needs a small DDL migration in Sprint 4. |

## Phase 2 — Pre-launch hardening

| Task | Status | Commit | Frontend trigger |
| --- | --- | --- | --- |
| D1.1 cart freeze cron | ✅ done | `76dc6b89` | none — silent UX fix. |
| D1.2 async DobroPost booking | ✅ done | `9fed188b` | **Logistics admin UI**: procure returns 204 immediately. New `HoldReason.BOOKING_FAILED` available via `_meta` (re-fetch the schema). Poll the order detail until `crossBorderShipmentId` is populated OR `holdReason === "booking_failed"`. |
| D1.3 Recipient validation fix | ✅ done | `484f5136` | none — internal correctness. UX side-effect: phone / email edits no longer trigger spurious "verification pending" state. |

## Phase 3 — Observability

| Task | Status | Commit |
| --- | --- | --- |
| D2.1 outbox lag metric | ✅ done | `bc491d87` |
| D2.2 DLQ growth alerting | ✅ done | `bc491d87` |
| D2.3 PII redaction | ✅ done | `12d6b732` |

See `docs/observability-runbook.md` for alert names + first-five-minutes
runbook.

## Phase 4 — Optional

| Task | Status | Notes |
| --- | --- | --- |
| D3.1 Telegram bot push | ⏸ deferred | Sprint 3 wrapped Phase 3 with no margin — see `sprint-3-deferred.md`. |
| D3.2 Favorites → activity | ⏸ deferred | same. |
| D3.3 Product mutations SSE | ⏸ deferred | confirmed not blocking — was deferred in Sprint 2 too. |

## Notes for the Frontend session

* OpenAPI snapshot regenerated this sprint after D0.1 (229 paths) and
  D0.3 (no path delta but `RecipientSchema.version` added). No further
  changes between then and Sprint 3 close.
* `frontend/admin/openapi/*.json` updates are still uncommitted in the
  submodule — please flush them in your next merge so my next
  `make openapi-sync` doesn't conflict.
* `BOOKING_FAILED` is a new `HoldReason` value — when frontend renders
  the resume / cancel UI from `HoldResumeModal`, this case should
  show a "DobroPost booking failed — manager will retry" copy block.
