# Sprint 3 — deferred items

## D0.3 — ETag/If-Match wiring on Brand / Category / Variant

**Status**: deferred to a follow-up sprint that includes a small
schema migration. Sprint 3 wired Recipient (the second mandatory
target after Product); the remaining three need a one-shot DDL
addition before the same template can apply.

**Why deferred**:

* `Product`, `SKU`, `Recipient` carry `version: int` columns —
  optimistic-lock conflicts already raise `OptimisticLockError`
  cleanly. Wiring ETag is a presentation-layer change only.
* `Brand`, `Category`, `ProductVariant` do **not** have a `version`
  column today. Adding ETag without a true monotonic counter would
  force us to fake the ETag from `updated_at` (timestamp ETag — RFC
  7232 weak validator territory) and bolt a parallel race-detection
  layer on top of the SQL UPDATE. Both options cost more time than
  the C4.1 spec budgeted.

**Required work for Sprint 4 wiring**:

1. **Migration**: add `version INTEGER NOT NULL DEFAULT 0` to
   `brands`, `categories`, `product_variants` tables.
2. **Domain**: add `version: int = 0` to the corresponding aggregates
   + repository's `update()` to bump on every flush (Strategy A,
   matching `Product`).
3. **Presentation**: same template applied in Sprint 2 to Product +
   Sprint 3 to Recipient — `attach_etag(response, model.version)` on
   GET, `Depends(parse_if_match)` on PATCH/DELETE,
   `OptimisticLockError → PreconditionFailedError` upgrade in the
   `if_match_version is not None` branch.

Estimated effort: ~3h total — 1h migration + 1h aggregate /
repository + 1h presentation × 3 entity (mostly copy-paste from
Recipient template). Frontend ETag interceptor is already shipping
for Product + Recipient and silently no-ops on responses without
the header, so the migration can land on its own cadence without a
breaking change.

**Reference templates**:

* Sprint 2 commit `d7044873` — Product template.
* Sprint 3 commit (this) — Recipient template (handler-side
  `expected_version` + handler-side `OptimisticLockError` raise +
  router-side `PreconditionFailedError` upgrade).

## C4.2 — Product mutations SSE channel

**Status**: still deferred (was deferred in Sprint 2). Frontend
Sprint 3 confirmed it's not blocking. Re-evaluate in Sprint 4 along
with the Brand/Category/Variant ETag wiring above (both touch the
admin product router).
