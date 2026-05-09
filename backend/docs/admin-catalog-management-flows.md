# Admin Catalog Management Flows

> [!info] Audience
> Frontend Admin developer building `/admin/settings/{brands,attributes,attribute-templates}`
> pages and the product editor. This doc spec'es every catalog admin
> endpoint with body shapes, side effects, and edge cases. Pair it
> with `frontend/admin/openapi/backend-mini.json` for the strict
> request/response schemas.

**Audience map** (from `backend/CLAUDE.md` — Router naming convention):

* All paths below sit under `/api/v1/admin/catalog/`.
* Permission baseline: every endpoint requires
  `Depends(RequireStaffRole)`; resource-level permissions are noted
  per route (`catalog:read` / `catalog:manage` / `catalog:manage_media`).

---

## 1. Brand

### 1.1 Create — `POST /admin/catalog/brands`

* **Permission**: `catalog:manage`
* **Body**:
  ```json
  {
    "name": "Nike",
    "slug": "nike",                              // optional — auto-derived if omitted
    "logoStorageObjectId": "uuid-from-upload",   // optional
    "logoUrl": "https://cdn.example/.../logo.png" // optional, validates `^https://`
  }
  ```
* **Side effects**: `BrandCreatedEvent` lands in outbox (audit-only — no
  consumer wired today; ready for future cache-bust / search-reindex).
* **Errors**:
  * 409 `BRAND_SLUG_CONFLICT` — duplicate slug.
  * 422 — `name`/`slug` validation (length, charset).

### 1.2 Bulk create — `POST /admin/catalog/brands/bulk`

* **Permission**: `catalog:manage`
* **Body**: array of `{ "name": ..., "slug": ... }`. Each item
  validated independently; per-item errors returned in a `errors[]`
  array on the response.

### 1.3 List — `GET /admin/catalog/brands`

* **Permission**: `catalog:read`
* **Query params**: `offset`, `limit`, `q` (free-text by name/slug).
* **Response**: paginated list per `PaginatedResponse[BrandResponse]`.

### 1.4 Detail — `GET /admin/catalog/brands/{brandId}`

* **Permission**: `catalog:read`
* **Response**: `BrandResponse` (`id, name, slug, logoUrl`).

> [!note] Follow-up — `productsCount` (Sprint 3+)
> The C3 spec called for `productsCount` in the detail response to
> drive a deletion-blocker UX hint. Not landed in this sprint —
> requires a new `IProductRepository.count_by_brand(brand_id)` method
> + cache strategy. Frontend should hit `GET /admin/catalog/products?brandId=...&limit=1`
> and use the `total` field as a stand-in for now.

### 1.5 Update — `PATCH /admin/catalog/brands/{brandId}`

* **Permission**: `catalog:manage`
* **Body**: any subset of create-time fields. Optimistic locking via
  `version` (legacy) — see C4.1 ETag/If-Match section once landed.
* **Errors**: 409 on slug conflict, 412 on If-Match mismatch (post-C4.1).

### 1.6 Delete — `DELETE /admin/catalog/brands/{brandId}`

* **Permission**: `catalog:manage`
* **Response**: 204 on success.
* **Behavior**: hard-delete on the Brand row.
* **Edge case** — Brand referenced by ≥1 active Product:
  * Today: DB FK constraint kicks in → handler maps to 409 / 422
    via the standard envelope. Frontend should pre-flight using
    `GET /admin/catalog/products?brandId=...&limit=1` to render a
    "cannot delete — N products" affordance before issuing the call.
  * Sprint 3+: explicit `Conflict` envelope with `referencingProductCount`
    in `details` (FOLLOW-UP).

### 1.7 Logo upload flow

3-step pattern shared with product/category logos (REC-028 unified
media flow):

1. `POST /admin/media` (image module) — reserve a `storageObjectId`
   + presigned PUT URL.
2. Upload bytes directly to S3.
3. `POST /admin/media/{id}/confirm` — flips status to `PROCESSING`,
   triggers async resize.
4. `POST /admin/catalog/brands` (or `PATCH .../{id}`) with
   `logoStorageObjectId=<id>` — catalog joins the storage row at
   read time so the public URL is always the latest processed
   version.

---

## 2. Category

### 2.1 Create / Bulk create / List / Detail / Update / Delete

Mirror the Brand layout. Two extras:

* `GET /admin/catalog/categories/tree` — return the full tree as a
  nested structure for the category-picker UI. Cached per
  `STOREFRONT_PRODUCT_GENERATION_KEY` bump.
* Categories are hierarchical: `parentId` is mutable on update;
  cycle-detection enforced at the domain level.

### 2.2 Edge case — delete with children

Today: domain-level guard — categories with non-deleted children
return 409 with code `CATEGORY_HAS_CHILDREN`. Frontend should walk
the tree breadth-first when offering a "delete category" UI.

---

## 3. Attribute

EAV backbone. Three resources in this slice: `Attribute` (the
metadata), `AttributeGroup` (visual grouping in the admin), and
`AttributeValue` (the list of allowed values for `enum`-type
attributes).

### 3.1 `POST /admin/catalog/attributes`

* **Permission**: `catalog:manage`
* **Body** (excerpt):
  ```json
  {
    "code": "color",
    "nameI18n": {"ru": "Цвет", "en": "Color"},
    "dataType": "enum",                    // string / number / bool / enum / multi_enum
    "uiType": "select",                    // select / radio / chips / ...
    "level": "variant",                    // product / variant
    "groupId": "uuid",
    "isRequired": false,
    "isVariantDefining": true              // affects SKU.variant_hash
  }
  ```
* **Side effects**: none today. Storefront cache generation does NOT
  bump on attribute create; bump only on a `Product` mutation that
  references the attribute.

### 3.2 `POST /admin/catalog/attributes/bulk`

Same body shape as create, wrapped in `items`.

### 3.3 `GET /admin/catalog/attributes` / `{id}` / `PATCH` / `DELETE`

Standard CRUD. `GET .../usage` returns aggregated counts (which
templates / categories / SKUs reference this attribute) — frontend
shows it before delete.

### 3.4 Edge case — delete with references

* If `usage.product_attribute_value_count > 0` OR
  `usage.template_binding_count > 0` → 409
  `ATTRIBUTE_IN_USE` with `details` carrying the breakdown.
* Otherwise hard-delete.

### 3.5 AttributeGroup

`POST /admin/catalog/attribute-groups` + the standard CRUD. Soft
delete with re-assignment: deleting a group with attached attributes
returns 409 with `ATTRIBUTE_GROUP_NOT_EMPTY`; the operator must
reassign first via `PATCH /attributes/{id}` with a new `groupId`.

### 3.6 AttributeValue

Nested under attribute: `/admin/catalog/attributes/{attributeId}/values`.

Two non-trivial endpoints:

* `PATCH .../{valueId}/activate` and `PATCH .../{valueId}/deactivate` —
  toggle `isActive`. **Important**: deactivating a value that is
  currently bound to a SKU's `variantAttributes` does NOT remove the
  SKU from the storefront immediately. The SKU stays visible until
  the next ADR-005 recompute; if the operator wants instant hiding,
  they must also flip the SKU's `isActive` to false. Ramp this up
  loudly in the UI (confirmation dialog).
* `POST .../reorder` — bulk-reorder values for an attribute. Same
  single-statement contract as media reorder (C2.3).

---

## 4. AttributeTemplate

The most complex entity. A `Template` is a named bundle of
`(Attribute, isRequired, sortOrder)` bindings that can be assigned
to one or more categories. Editing a template fans out the
recommendation set across every product whose primary category
matches.

### 4.1 `POST /admin/catalog/attribute-templates`

Body: `{ "name": "...", "description": "...", "categoryIds": [...] }`.

### 4.2 `POST /admin/catalog/attribute-templates/clone`

Body: `{ "sourceTemplateId": "...", "newName": "..." }`.

Returns: a fresh template with the source's bindings duplicated.
Use case — "Like template X but for category Y".

### 4.3 `GET /admin/catalog/attribute-templates`

Query params: `categoryId` (filter to templates assigned to a
category), pagination.

### 4.4 `GET /admin/catalog/attribute-templates/{templateId}`

Detail: includes `bindings[]` (each `{ attributeId, isRequired,
sortOrder }`). Frontend renders this as an editable list.

### 4.5 `PATCH /admin/catalog/attribute-templates/{templateId}`

Update name / description / category assignments.

### 4.6 Bindings (sub-resource)

* `POST /attribute-templates/{templateId}/attributes` — attach an
  attribute. Body: `{ attributeId, isRequired, sortOrder }`. Returns
  `TemplateAttributeBindingEnrichedResponse` with the count of
  affected categories so the admin UI can show "this will appear on
  N product editor pages" before saving.
* `PATCH /attribute-templates/{templateId}/attributes/{bindingId}` —
  flip `isRequired` or change `sortOrder`.
* `DELETE /attribute-templates/{templateId}/attributes/{bindingId}` —
  remove a binding (does NOT delete the underlying Attribute).
* `POST /attribute-templates/{templateId}/attributes/reorder` —
  bulk reorder bindings within one template. Body: array of
  `{ bindingId, sortOrder }`.

### 4.7 Edge case — delete a template with category assignments

Today: hard-delete via `DELETE /admin/catalog/attribute-templates/{id}`.
The delete cascades the bindings + drops the category-template links.
Existing products keep their `productAttributeValues` rows untouched —
the template is just a recommendation surface, never a constraint.

---

## 5. Product, Variant, SKU

Documented in `backend/CLAUDE.md` (architecture + FSM) and
`docs/audit-order-event-chains-2026-05.md` (downstream events).
This doc only covers the C1 / C2 additions:

### 5.1 `POST /admin/catalog/products/{id}/_validate-publish` (C1.1)

Read-only preview of the publish gate. Returns
`{ ok, currentStatus, nextStatus, skuDiagnostics, gateFailures }`
with structured codes (`STATUS_NOT_TRANSITIONABLE`,
`NO_ACTIVE_SKU`, `ALL_SKUS_UNPRICED`). `ok=false` is a valid
verdict (200, not 4xx) — render as a "fix these before publishing"
panel.

### 5.2 `POST /admin/catalog/products/{id}/_validate-update` (C1.2)

Read-only preview of a PATCH body. Accepts the same shape as
`PATCH /admin/catalog/products/{id}` and returns
`{ ok, diff, warnings, validationErrors }` so the UI can render
a "saving will…" panel before commit. `warnings` carry advisory
codes (`SUPPLIER_CHANGE_TRIGGERS_RECOMPUTE`,
`CATEGORY_CHANGE_TRIGGERS_RECOMPUTE`, `BRAND_CHANGE`); they do NOT
close the gate.

### 5.3 Media gallery

* `POST /products/{id}/media` — attach a new asset. Body carries
  `storageObjectId` (3-step upload flow); the catalog row joins the
  storage_object at read time.
* `POST /products/{id}/media/reorder` (C2.3) — bulk reorder via a
  single SQL `UPDATE ... CASE WHEN`. Frontend can ship 5-50 items in
  one call without N+1 risk; integration test pins the contract.
* `PATCH /products/{id}/media/{mediaId}` — set `role` (`main` /
  `gallery` / `bg_removed`) or `isActive`.
* `DELETE /products/{id}/media/{mediaId}` — detach. Triggers the
  IMG-005 outbox cleanup chain
  (`MediaAssetDetachedEvent` → `cleanup_storage_after_detached` →
  S3 delete + `storageObjects` row soft-delete).
* `POST /admin/media/{id}/remove-background` (C2.2) — request a
  bg-removal derivation. Idempotent: `alreadyExisted=true` returns
  the existing derivation. `status` is now `Literal["processing",
  "completed", "failed"]` (was opaque string) — the `failed` branch
  surfaces a previous run's terminal state instead of collapsing to
  `processing`. Disabled-feature returns 503 with code
  `BG_REMOVAL_DISABLED` and `details.featureFlag`.

### 5.4 `DELETE /admin/catalog/products/{id}` (C2.1 fix)

Soft-deletes the product, cascades to variants + SKUs, AND now
detaches every media asset via the IMG-005 outbox chain. Pre-fix:
`media_assets` rows + S3 keys orphaned forever. Post-fix: cleanup
runs asynchronously with the same retry + DLQ guarantees as the
per-row update path.

---

## 6. Cross-cutting edge cases

| Scenario | Today's behaviour | Frontend hint |
| --- | --- | --- |
| Delete brand with N products | 409 with `BRAND_HAS_PRODUCTS` (FK guard) | Pre-flight `?brandId=` count |
| Delete attribute with bound values on SKUs | 409 `ATTRIBUTE_IN_USE` | Show `usage` from `GET .../usage` |
| Deactivate AttributeValue used by SKU | SKU stays storefront-visible until next ADR-005 recompute | Confirm dialog with explicit "this will not hide N SKUs immediately" |
| Delete attribute template with active assignments | Hard-deletes — bindings cascade | Confirm dialog; product editors lose recommendations |
| Update product with `supplierId` change | Triggers per-SKU recompute fan-out (PENDING → PRICED), SKUs hidden until recompute lands | C1.2 surfaces `SUPPLIER_CHANGE_TRIGGERS_RECOMPUTE` warning |

## Related

* `[[ADR-005a Pricing → Catalog ACL Inversion]]` — the recompute path
  every "change supplier/category/brand" warning refers to.
* `backend/CLAUDE.md` — Router naming convention, RBAC permissions,
  outbox patterns.
* `docs/audit-media-lifecycle-2026-05.md` — IMG-005 cleanup chain
  details (post-C2.1 fix).
* `frontend/admin/openapi/backend-mini.json` — strict request/response
  schemas (regenerate via `make openapi-sync`).

## Follow-ups (not landed in Sprint 2)

* Brand `productsCount` in detail response (C3.1 spec line — deferred).
* Conflict-aware `BRAND_HAS_PRODUCTS` envelope with explicit count.
* Attribute group reassignment helper endpoint
  (`POST /attribute-groups/{src}/reassign?targetGroupId=...`).
* Template diff preview (mirror of C1.2 for attribute templates).
