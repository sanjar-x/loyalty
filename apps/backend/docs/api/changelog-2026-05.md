# Backend API Changelog — 2026-05

> [!info] Audience
> Frontend Admin and Frontend Main developers consuming the OpenAPI
> snapshot (`frontend/admin/openapi/{backend,backend-mini}.json`).
> Each entry below points at the commit and notes whether action is
> required on the client side.

## 2026-05-09 — Sprint 2 (Catalog Hardening)

### `LOG-002` — fix: russian carrier tracking → order FSM bridge

* Commit: `5ac403a5` `fix(logistics,order): bridge russian carrier tracking events to order FSM (LOG-002, fixes GAP A from B1 audit)`
* **Behaviour change, no API surface change.** Orders now actually
  progress through `ARRIVED_IN_RU → IN_LAST_MILE → AWAITING_PICKUP →
  DELIVERED` once their CDEK / Yandex / Russian-Post shipment moves
  forward. Pre-fix any order past ARRIVED_IN_RU was stuck forever.
* **Frontend action**: none — endpoints unchanged. The Sprint 2
  Logistics UI can now rely on the customer-facing `tracking` view
  to actually advance.

### `C1.1` — feat: `POST /admin/catalog/products/{id}/_validate-publish`

* Commit: `671e8033` `feat(catalog): _validate-publish preview endpoint (C1.1)`
* **New endpoint, additive.** Read-only validator that mirrors the
  publish gate without committing. Returns
  `{ ok, currentStatus, nextStatus, skuDiagnostics, gateFailures }`.
  `gateFailures[].code` is one of `STATUS_NOT_TRANSITIONABLE`,
  `NO_ACTIVE_SKU`, `ALL_SKUS_UNPRICED`. `ok=false` is a valid 200
  response — render the panel, do not toast an error.
* **Frontend action**: wire to the `PublishGateBlocker` panel
  before the operator clicks the actual `PATCH .../status` to
  `published`.

### `C1.2` — feat: `POST /admin/catalog/products/{id}/_validate-update`

* Commit: `cd4d1369` `feat(catalog): _validate-update preview endpoint (C1.2)`
* **New endpoint, additive.** Read-only PATCH preview. Body shape
  identical to `PATCH /admin/catalog/products/{id}`. Returns
  `{ ok, diff, warnings, validationErrors }`. `warnings` carry
  advisory codes
  (`SUPPLIER_CHANGE_TRIGGERS_RECOMPUTE`,
  `CATEGORY_CHANGE_TRIGGERS_RECOMPUTE`, `BRAND_CHANGE`); they do
  NOT close the gate.
* **Frontend action**: render the "saving will…" panel before
  committing the PATCH.

### `C2.1` — fix: cascade media cleanup on product delete (IMG-005 gap)

* Commit: `1a141c41` `fix(catalog): cascade media cleanup on product delete (C2.1, IMG-005 gap)`
* **Behaviour change, no API surface change.** `DELETE /admin/catalog/products/{id}`
  now correctly drops every attached media row + scheduling S3
  cleanup via the IMG-005 outbox chain. Pre-fix `media_assets`
  rows + S3 keys were orphaned forever.
* **Frontend action**: none.

### `C2.2` — fix: bg-removal idempotency + 503 envelope

* Commit: `51022fd5` `fix(image): bg-removal idempotency surfaces FAILED + 503 envelope (C2.2)`
* **Schema change** —
  `RemoveBackgroundResponse.status` widened from opaque `string` to
  `Literal["processing", "completed", "failed"]`. Pre-fix: a previous
  failed run collapsed into `processing`, leaving the UI listening
  to a dead SSE stream forever. Post-fix: `failed` surfaces honestly.
* **Schema change** —
  feature-flag-off response is now 503 (was 400) with envelope
  `{ "error": { "code": "BG_REMOVAL_DISABLED", "details": { "featureFlag": "BG_REMOVAL_ENABLED" }, ... } }`.
* **Frontend action**: handle the `failed` branch (offer a "retry"
  button — the UI is responsible for an explicit DELETE + POST cycle
  because BG removal is an expensive ML op and we won't auto-replay).
  Update the 4xx interceptor to also handle 503 with this code.

### `C2.3` — test: lock single-statement contract for bulk media reorder

* Commit: `e3466094` `test(catalog): lock single-statement contract for bulk media reorder (C2.3)`
* **No API change.** Adds an integration test that pins
  `MediaAssetRepository.bulk_update_sort_order` at exactly one
  `UPDATE` statement for batch sizes up to 50.
* **Frontend action**: none — drag-and-drop with 5-50 items in one
  reorder call remains safe.

### `C3` — docs: admin catalog management flows spec

* Commit: `389da4b5` `docs(catalog): admin catalog management flows spec for frontend (C3)`
* **Documentation only.** New `backend/docs/admin-catalog-management-flows.md`
  with body shapes, side-effects, error envelopes, and edge cases for
  every Brand / Category / Attribute / AttributeGroup / AttributeValue
  / AttributeTemplate admin endpoint.
* **Frontend action**: build the
  `/admin/settings/{brands,attributes,attribute-templates}` pages
  against this doc + `frontend/admin/openapi/backend-mini.json`.

### `C4.1` — feat: ETag / If-Match optimistic locking (Product wired)

* Commit: `d7044873` `feat(api,catalog): ETag/If-Match optimistic locking — Product wired (C4.1)`
* **Schema change, additive** —
  `GET /admin/catalog/products/{id}` now emits `ETag: "v{version}"`.
  `PATCH /admin/catalog/products/{id}` accepts an optional
  `If-Match: "v{N}"` header; mismatch returns 412 with envelope code
  `PRECONDITION_FAILED` and `details: { entityType, entityId, expectedVersion, currentVersion }`.
  When the header is absent, the legacy `body.version` + 409 path is
  preserved (backward-compat through M+1).
* **Frontend action**: store the `ETag` on the read, echo as
  `If-Match` on the next mutate, handle 412 with a "refetch and try
  again" interceptor.
* **Status**: the remaining five entity (Brand, Category, Variant,
  SKU, Recipient) are documented in `docs/sprint-2-deferred.md` for
  Sprint 3 — the shared infra (`PreconditionFailedError`,
  `parse_if_match`, `attach_etag`) is in place; per-entity wiring is
  ~1.5h each.

### `C4.2` — defer: product mutations SSE channel

* Documented in `docs/sprint-2-deferred.md`. Pricing-events SSE
  remains the only admin-detail-page channel for Sprint 2.

---

## Earlier (Sprint 1)

See commits `b0753d0d` (B3 — payment auth-expiry cron),
`c7e2edd9` (B1 — order event-chain audit), and `1b53a11b` (B2 —
OpenAPI snapshot regeneration + `make openapi-sync`).
