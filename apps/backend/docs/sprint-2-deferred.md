# Sprint 2 — deferred items

Items that the Sprint 2 brief listed as mandatory but are deferred to
Sprint 3 with a documented template / reason. Every entry has the
acceptance criteria + the rough work estimate so the team can pick
them up cleanly.

## C4.1 — ETag / If-Match for the remaining 5 entity

**Status**: shared infra landed in Sprint 2 + Product wired as the
template. Brand / Category / Variant / SKU / Recipient need the same
3-step wiring per entity:

1. `GET /{id}` — call `attach_etag(response, read_model.version)`
   after fetching.
2. `PATCH/PUT/DELETE /{id}` — add
   `if_match_version: int | None = Depends(parse_if_match)` to the
   signature, pass it down to the command's `version` field (or
   substitute it for the body's `version`), and translate
   `ConcurrencyError` to `PreconditionFailedError(412)` in the
   `if_match_version is not None` branch — keep the legacy 409
   behaviour when the header is absent.

**Reference template**: `src/modules/catalog/presentation/router_admin_products.py`
(`get_product` + `update_product` after C4.1 commit).

**Estimated effort**: ~1.5h per entity (route wiring + 1 unit test
+ 1 e2e test). The shared infra and the cross-cutting envelope
(``PreconditionFailedError``) are already in place.

**Frontend impact**: the interceptor can light up the 412 path
incrementally — every entity that ships ETag header on its GET
becomes safe for cross-tab edits the moment it lands. Until then
the legacy ``version`` body field + 409 path keeps working.

### Per-entity work breakdown

| Entity | Routers | Mutating endpoints | Owns version? |
| --- | --- | --- | --- |
| Brand | `router_admin_brands.py` | PATCH, DELETE | yes (`Brand.version`) |
| Category | `router_admin_categories.py` | PATCH, DELETE | yes |
| ProductVariant | `router_admin_variants.py` | PATCH, DELETE | yes (`ProductVariant.version`) |
| SKU | `router_admin_skus.py` | PATCH, DELETE | yes (`SKU.version`) |
| Recipient | `recipient/router_recipients.py` | PATCH, DELETE | yes |

## C4.2 — Product mutations SSE channel

**Status**: deferred. Pricing-events SSE
(`GET /admin/catalog/products/{id}/skus/pricing-events`) already exists
for `SKUPricedEvent` / `SKUPricingFailedEvent` per CAT-005. The C4.2
spec asked for a parallel `mutations` channel that broadcasts
`ProductUpdated`, `Variant{Added,Deleted}`, `SKU{Added,Deleted}`,
`StatusChanged`, `MediaAttached/Detached` — the front-end would
subscribe to both on a single product detail page.

**Why deferred**:
* Largest per-event work yet — needs an outbox bridge (similar to
  CAT-005) for at least 6 event types, a new Redis pub/sub channel
  pattern (`product:{id}:mutations`), and a new SSE endpoint.
* No frontend blocker for Sprint 2 cutover — the existing
  pricing-events channel covers the highest-frequency invalidation
  signal; cross-tab sync of attribute / variant edits remains a UX
  improvement, not a correctness gate.

**When to land**: Sprint 3 alongside the outstanding C4.1 entity
wiring — both touch the same routers and the same admin SSE
infrastructure, batching them keeps the diffs reviewable.
