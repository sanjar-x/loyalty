# Phase 8: Admin UI Enhancements - Research

**Researched:** 2026-03-30
**Domain:** Admin frontend (Next.js 16 / React 19 / JavaScript) -- product form completeness, FSM transitions, optimistic locking
**Confidence:** HIGH

## Summary

Phase 8 adds three distinct enhancements to the admin product management UI: (1) displaying missing required/recommended attributes sourced from the backend completeness endpoint, (2) showing all 5 valid FSM status transitions with invalid ones disabled, and (3) sending the `version` field in all PATCH requests for optimistic locking.

The backend already fully supports all three features. The completeness endpoint (`GET /products/{id}/completeness`) exists and returns `missingRequired` and `missingRecommended` arrays with `attributeId`, `code`, and `nameI18N`. The status change endpoint (`PATCH /products/{id}/status`) accepts any valid FSM transition string. The update endpoint (`PATCH /products/{id}`) already accepts an optional `version` field for optimistic locking with `ConcurrencyError` (409) on mismatch.

The admin frontend currently has NO product detail/edit page -- only a creation flow and a list page using seed data. The BFF has no route for `GET /api/catalog/products/{productId}` or `GET /api/catalog/products/{productId}/completeness`. The current `changeProductStatus` service function only sends `{status}`, and no PATCH calls include `version`. The primary work is: (a) adding missing BFF proxy routes, (b) adding service functions for fetching product detail and completeness, (c) building a product detail/edit page with completeness display and FSM UI, and (d) wiring `version` into all PATCH payloads.

**Primary recommendation:** Build a product detail page at `/admin/products/[productId]` that fetches the product (capturing `version`), displays completeness via a side panel or section, and provides FSM transition buttons. Wire `version` into all PATCH service calls by tracking it from the last API response.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
None -- all implementation choices are at Claude's discretion per CONTEXT.md.

### Claude's Discretion
All implementation choices are at Claude's discretion. Use ROADMAP success criteria and codebase patterns.

Key constraints from ROADMAP:
- Completeness endpoint: display missing required/recommended attributes
- FSM UI: show all 5 valid transitions, disable invalid ones based on current status
- Optimistic locking: all PATCH requests include version field from last-fetched product

FSM transitions (from product-creation-flow.md):
- DRAFT -> ENRICHING
- ENRICHING -> DRAFT, READY_FOR_REVIEW
- READY_FOR_REVIEW -> ENRICHING, PUBLISHED
- PUBLISHED -> ARCHIVED
- ARCHIVED -> DRAFT

### Deferred Ideas (OUT OF SCOPE)
None -- discuss phase skipped.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| UI-01 | Admin product form displays missing required/recommended attributes from completeness endpoint | Backend endpoint exists (`GET /products/{id}/completeness`); returns `missingRequired`/`missingRecommended` arrays. Need BFF proxy route + admin service function + UI component. |
| UI-02 | Admin FSM UI supports all 5 transitions (DRAFT<->ENRICHING, ENRICHING->READY_FOR_REVIEW, READY_FOR_REVIEW->PUBLISHED, PUBLISHED->ARCHIVED, ARCHIVED->DRAFT) | Backend FSM fully implemented in `Product._ALLOWED_TRANSITIONS`. `PATCH /products/{id}/status` with `{status: "..."}` body. Need FSM transition map in frontend + buttons with disable logic. |
| UI-03 | Admin sends version field in all PATCH requests for optimistic locking support | Backend `UpdateProductCommand` already handles `version` with `ConcurrencyError` (409). Need to track `version` from product fetch response and include it in PATCH calls. |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- **Language:** Admin frontend is JavaScript (ES2017+), no TypeScript
- **Framework:** Next.js 16.1.x with App Router, React 19
- **Architecture:** Admin BFF proxy -> backend directly for catalog operations via `backendFetch()`
- **I18n convention:** Backend returns `I18N` (uppercase N) -- e.g., `titleI18N`, `nameI18N`
- **State management:** Admin uses server-state via Next.js API routes, no global state manager
- **Styling:** Tailwind CSS 4 + CSS Modules (`.module.css`) -- admin uses custom `app-*` design tokens
- **Code style:** ESLint 9, Prettier with `prettier-plugin-tailwindcss`
- **API contracts:** Do NOT break existing contracts -- only extend

## Standard Stack

### Core (already installed -- no new dependencies needed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Next.js | 16.1.6 | App Router, BFF API routes | Already in use |
| React | 19.1.1 | UI rendering | Already in use |
| clsx + tailwind-merge | 2.1.1 / 3.4.0 | Conditional CSS class merging | Already in use via `cn()` |
| CSS Modules | built-in | Component-scoped styles | Already in use across admin |

### Supporting

No new libraries are needed. The admin frontend has zero external state management -- all product data is fetched via Next.js API routes and held in component-local state via `useState`/`useReducer`.

### Alternatives Considered

None -- all three requirements can be implemented with existing dependencies.

## Architecture Patterns

### Existing BFF Proxy Pattern

All admin API calls follow this established pattern:

```
Browser -> fetch('/api/catalog/...') -> Next.js API Route -> backendFetch('/api/v1/...') -> Backend
```

Each BFF route file exports named functions matching HTTP methods (`GET`, `POST`, `PATCH`). Authentication is handled by `getAccessToken()` from cookies.

### Existing Service Layer Pattern

`frontend/admin/src/services/products.js` provides a client-side `api()` wrapper that:
1. Calls BFF routes (not backend directly)
2. Parses JSON responses
3. Throws structured errors with `code`, `status`, `details`

### Recommended New Files Structure

```
frontend/admin/src/
├── app/
│   ├── api/catalog/products/
│   │   ├── [productId]/
│   │   │   ├── route.js                  # NEW: GET, PATCH proxy for product detail
│   │   │   ├── completeness/
│   │   │   │   └── route.js              # NEW: GET proxy for completeness
│   │   │   ├── status/
│   │   │   │   └── route.js              # EXISTS: PATCH status
│   │   │   └── ...
│   │   └── route.js                      # EXISTS: POST create
│   └── admin/products/
│       ├── [productId]/
│       │   └── page.jsx                  # NEW: Product detail/edit page
│       ├── add/                          # EXISTS: Product creation flow
│       └── page.jsx                      # EXISTS: Product list
├── components/admin/products/
│   ├── CompletenessPanel.jsx             # NEW: Shows missing required/recommended attrs
│   ├── StatusTransitionBar.jsx           # NEW: FSM transition buttons
│   └── ...                               # EXISTING components
├── hooks/
│   └── useProductDetail.js               # NEW: Fetch product + completeness, track version
└── services/
    └── products.js                       # EXTEND: Add getProduct, getCompleteness functions
```

### Pattern 1: BFF Proxy Route (GET product detail)

**What:** Next.js API route that proxies GET requests to backend
**When to use:** For any new backend endpoint the admin needs to access

```javascript
// frontend/admin/src/app/api/catalog/products/[productId]/route.js
import { NextResponse } from 'next/server';
import { backendFetch } from '@/lib/api-client';
import { getAccessToken } from '@/lib/auth';

export async function GET(request, { params }) {
  const token = await getAccessToken();
  if (!token) return NextResponse.json({ error: { code: 'UNAUTHORIZED' } }, { status: 401 });

  const { productId } = await params;
  const { ok, status, data } = await backendFetch(
    `/api/v1/catalog/products/${productId}`,
    { method: 'GET', headers: { Authorization: `Bearer ${token}` } },
  );

  const response = NextResponse.json(
    data ?? { error: { code: 'SERVICE_UNAVAILABLE' } },
    { status: ok ? 200 : (status || 502) },
  );
  if (ok) response.headers.set('Cache-Control', 'no-store');
  return response;
}

export async function PATCH(request, { params }) {
  const token = await getAccessToken();
  if (!token) return NextResponse.json({ error: { code: 'UNAUTHORIZED' } }, { status: 401 });

  const { productId } = await params;
  const body = await request.json();

  const { ok, status, data } = await backendFetch(
    `/api/v1/catalog/products/${productId}`,
    {
      method: 'PATCH',
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    },
  );

  return NextResponse.json(
    data ?? { error: { code: 'SERVICE_UNAVAILABLE' } },
    { status: ok ? 200 : (status || 502) },
  );
}
```

### Pattern 2: FSM Transition Map (client-side constant)

**What:** Static map of allowed transitions per status, used to render/disable buttons
**When to use:** For the FSM UI requirement (UI-02)

```javascript
// Matches Product._ALLOWED_TRANSITIONS from backend exactly
const STATUS_TRANSITIONS = {
  draft:             [{ target: 'enriching',        label: 'Начать обогащение' }],
  enriching:         [{ target: 'draft',            label: 'Вернуть в черновик' },
                      { target: 'ready_for_review', label: 'На модерацию' }],
  ready_for_review:  [{ target: 'enriching',        label: 'Вернуть на обогащение' },
                      { target: 'published',        label: 'Опубликовать' }],
  published:         [{ target: 'archived',         label: 'В архив' }],
  archived:          [{ target: 'draft',            label: 'Вернуть в черновик' }],
};

const STATUS_LABELS = {
  draft: 'Черновик',
  enriching: 'Обогащение',
  ready_for_review: 'На модерации',
  published: 'Опубликован',
  archived: 'Архив',
};
```

### Pattern 3: Version Tracking for Optimistic Locking (UI-03)

**What:** Track `version` from every product fetch response, include in all PATCH requests
**When to use:** For all PATCH calls to products

```javascript
// Service function pattern -- version is passed explicitly
export async function updateProduct(productId, payload) {
  // payload must include { version } from last fetch
  return api(`/api/catalog/products/${productId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

// Status change also benefits from version (backend accepts it)
export async function changeProductStatus(productId, status, version) {
  return api(`/api/catalog/products/${productId}/status`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status }),
    // Note: status endpoint doesn't use version currently,
    // but the response returns the updated product with new version
  });
}
```

### Anti-Patterns to Avoid

- **Duplicating FSM logic in frontend:** Do NOT validate transitions client-side beyond disabling buttons. The backend is the source of truth -- if a transition is attempted and invalid, the backend returns a clear error.
- **Caching product version:** Do NOT cache version separately from the product data. Always use the version from the most recent API response. Stale versions cause 409 Conflict errors.
- **Polling completeness:** Do NOT poll the completeness endpoint. Fetch it once when the product detail page loads, and re-fetch after attribute changes.
- **Building a full product edit form in this phase:** The requirement is to display completeness and FSM transitions, not to rebuild the entire product creation form for editing. Keep the detail page focused.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| FSM transition validation | Client-side FSM engine | Static `STATUS_TRANSITIONS` map + backend validation | Backend already enforces all rules including readiness checks (active SKUs, media assets) |
| Completeness calculation | Frontend attribute comparison | Backend `GET /products/{id}/completeness` endpoint | Backend has access to template bindings, product attributes, and all the ORM joins needed |
| Optimistic locking | Custom version-diff mechanism | Backend `version` field + `ConcurrencyError` (409) | Infrastructure-level concern already handled by SQLAlchemy version_id_col |
| i18n display | Custom locale picker | Existing `i18n()` helper from `@/lib/utils` | Already used across the admin for `nameI18N` display |

## Common Pitfalls

### Pitfall 1: Missing BFF Proxy Routes
**What goes wrong:** Frontend calls `/api/catalog/products/{id}` or `/api/catalog/products/{id}/completeness` but gets 404 because no Next.js API route exists.
**Why it happens:** The admin uses BFF proxy routes for ALL backend calls. The backend endpoints exist, but the admin has no proxy for GET product detail or GET completeness.
**How to avoid:** Create BFF proxy routes BEFORE writing any frontend code that calls them.
**Warning signs:** 404 errors in browser console when loading product detail page.

### Pitfall 2: CamelCase Response Field Names
**What goes wrong:** Frontend code references `missing_required` instead of `missingRequired`, or `is_complete` instead of `isComplete`.
**Why it happens:** Backend Pydantic schemas use `CamelModel` which auto-converts snake_case to camelCase in JSON responses. The backend Python code uses `snake_case`, but the JSON API returns `camelCase`.
**How to avoid:** Always use camelCase when reading API response fields in JavaScript: `data.isComplete`, `data.missingRequired`, `data.nameI18N`, `data.version`.
**Warning signs:** `undefined` values when destructuring API responses.

### Pitfall 3: Version Field Not Flowing Through PATCH Calls
**What goes wrong:** Product updates succeed the first time but the version is not refreshed, so subsequent PATCH calls send stale version and get 409.
**Why it happens:** After a successful PATCH, the backend returns the updated product with incremented version. If the frontend doesn't capture this new version, the next PATCH will fail.
**How to avoid:** After every successful PATCH response, update the locally-held `version` from the response data (`data.version`). The `ProductResponse` always includes `version`.
**Warning signs:** 409 Conflict errors on second edit operation within the same session.

### Pitfall 4: Status Transition Button Enabled for Impossible Transitions
**What goes wrong:** "Publish" button is enabled but clicking it returns 422 because product has no active SKUs or no media.
**Why it happens:** The FSM map only captures which transitions are structurally valid, but the backend also checks readiness conditions (at least one active SKU, at least one priced SKU for publish, at least one media asset for publish).
**How to avoid:** Use the completeness data to enhance button state -- e.g., if `isComplete` is false, add a warning tooltip on the "Publish" button. But still allow the click (the backend will return a descriptive error).
**Warning signs:** Users confused by error messages after clicking apparently-enabled buttons.

### Pitfall 5: Product List Page Uses Seed Data
**What goes wrong:** The product list page at `/admin/products` uses `getProducts()` which returns `productsSeed` (hardcoded data), not real API data.
**Why it happens:** The product list was built as a UI prototype before the API was connected.
**How to avoid:** This is OUT OF SCOPE for Phase 8. The requirements only cover the detail page completeness, FSM transitions, and version in PATCH calls. Do not refactor the product list page.
**Warning signs:** N/A -- explicitly out of scope.

## Code Examples

### Backend API Response: Product Detail (what GET /products/{id} returns as camelCase JSON)

```json
{
  "id": "019...",
  "slug": "nike-air-max",
  "titleI18N": { "ru": "Nike Air Max", "en": "Nike Air Max" },
  "descriptionI18N": { "ru": "...", "en": "..." },
  "status": "draft",
  "brandId": "019...",
  "primaryCategoryId": "019...",
  "supplierId": null,
  "sourceUrl": null,
  "countryOfOrigin": null,
  "tags": [],
  "version": 1,
  "createdAt": "2026-03-30T...",
  "updatedAt": "2026-03-30T...",
  "publishedAt": null,
  "minPrice": null,
  "maxPrice": null,
  "priceCurrency": null,
  "variants": [...],
  "attributes": [...]
}
```

### Backend API Response: Completeness (GET /products/{id}/completeness)

```json
{
  "isComplete": false,
  "totalRequired": 3,
  "filledRequired": 1,
  "totalRecommended": 5,
  "filledRecommended": 2,
  "missingRequired": [
    {
      "attributeId": "019...",
      "code": "material",
      "nameI18N": { "ru": "Материал", "en": "Material" }
    }
  ],
  "missingRecommended": [
    {
      "attributeId": "019...",
      "code": "shoe_size",
      "nameI18N": { "ru": "Размер обуви", "en": "Shoe Size" }
    }
  ]
}
```

### Backend API: Status Change Request

```json
// PATCH /api/v1/catalog/products/{id}/status
{
  "status": "enriching"
}
// Returns full ProductResponse (includes new version)
```

### Backend API: Update Product with Version (PATCH /products/{id})

```json
// Request
{
  "titleI18N": { "ru": "Updated Name", "en": "Updated Name" },
  "version": 1
}
// Response: full ProductResponse with version: 2
```

### Backend Error: ConcurrencyError (409)

```json
{
  "error": {
    "code": "CONCURRENCY_ERROR",
    "message": "Product was modified by another user. Please refresh and try again.",
    "details": {
      "entity_type": "Product",
      "entity_id": "019...",
      "expected_version": 1,
      "actual_version": 2
    }
  }
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Seed data product list | BFF proxy + backend API | In progress (Phase 8 adds detail) | Product detail page will use real API |
| No version tracking | Optimistic locking via version | Phase 8 | Prevents lost updates on concurrent edits |
| Two-state FSM UI (draft/archive only) | Full 5-status FSM with transition buttons | Phase 8 | Complete product lifecycle management |

## Open Questions

1. **Product detail page navigation entry point**
   - What we know: The product list page (`/admin/products`) currently uses seed data and ProductRow has an edit button that does nothing.
   - What's unclear: Should the detail page be reachable from the product list (seed data page) or only by direct URL for now?
   - Recommendation: Add a Link on the edit button in ProductRow to `/admin/products/{id}` so it works when the list eventually uses real data. For now, the detail page is reachable via direct navigation.

2. **Scope of "product detail page"**
   - What we know: Requirements say "product form displays missing attributes" and "FSM UI shows transitions."
   - What's unclear: Should this be a full edit form or a read-only detail view with FSM controls?
   - Recommendation: Build a read-only detail view with completeness panel and FSM transition bar. Full editing is not in the Phase 8 requirements. The `version` tracking should be demonstrated by including it in the status change call payload flow (re-fetch product after status change to get new version).

## Sources

### Primary (HIGH confidence)
- Backend source code: `backend/src/modules/catalog/presentation/router_products.py` -- completeness and status endpoints
- Backend source code: `backend/src/modules/catalog/presentation/schemas.py` -- `ProductCompletenessResponse`, `ProductStatusChangeRequest`, `ProductUpdateRequest` schemas
- Backend source code: `backend/src/modules/catalog/domain/entities/product.py` -- `_ALLOWED_TRANSITIONS` FSM table
- Backend source code: `backend/src/modules/catalog/application/commands/update_product.py` -- version check logic
- Backend source code: `backend/src/modules/catalog/domain/exceptions.py` -- `ConcurrencyError`
- Admin frontend source: `frontend/admin/src/services/products.js` -- existing service layer pattern
- Admin frontend source: `frontend/admin/src/app/api/catalog/products/[productId]/status/route.js` -- BFF proxy pattern

### Secondary (MEDIUM confidence)
- `product-creation-flow.md` -- optimistic locking section, FSM diagram

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies needed, all existing patterns documented from source code
- Architecture: HIGH -- follows established BFF proxy and service layer patterns from existing codebase
- Pitfalls: HIGH -- identified from direct code reading (missing BFF routes, camelCase mapping, version tracking gaps)

**Key findings summary:**
1. Backend is fully ready -- completeness endpoint, FSM, and optimistic locking all implemented
2. Admin lacks: BFF proxy for GET product/{id}, BFF proxy for GET completeness, product detail page, version tracking in PATCH calls
3. No new dependencies needed -- pure JS/React with existing patterns
4. FSM transition map must match backend `_ALLOWED_TRANSITIONS` exactly (5 statuses, 7 transitions)
5. `version` must be captured from every product API response and included in subsequent PATCH calls

**Research date:** 2026-03-30
**Valid until:** 2026-04-30 (stable -- backend contracts are established)
