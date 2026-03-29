# Project Research Summary

**Project:** Loyality -- Product Creation Flow Integration Fix
**Domain:** Multi-service integration (Admin BFF / Main Backend / Image Backend)
**Researched:** 2026-03-29
**Confidence:** HIGH

## Executive Summary

This project addresses 14 integration issues that collectively prevent the admin panel's product creation flow from working end-to-end. The issues fall into three distinct categories: (1) BFF media proxy routes that target the wrong backend service, (2) schema and field name mismatches between the admin frontend, main backend, and image_backend, and (3) missing or incomplete UI integration for backend features like status FSM, completeness checking, and version-aware PATCH. The root cause is that three systems were developed against assumed contracts rather than verified ones -- the admin frontend was built against a spec, not the actual image_backend API, and the BFF blindly proxied media requests to the main backend where they return 404.

The recommended approach is to fix these issues in dependency order: backend schema fixes first (they are additive and non-breaking), then frontend locale enforcement (independent, frontend-only), then BFF media proxy rewrite (the most complex change, requiring a new `imageBackendFetch()` utility and route handler rewrites), and finally frontend integration completion (field names, media linking, status monitoring). The BFF architecture follows a well-established dual-client pattern -- two separate fetch utilities (`backendFetch` for main backend, `imageBackendFetch` for image_backend), each with its own auth mechanism and base URL. No new libraries are needed; everything uses built-in Web APIs.

The key risks are: (a) auth model confusion when developers copy-paste existing BFF route patterns that use JWT Bearer auth instead of X-API-Key, (b) field name mismatches between image_backend responses and frontend expectations (e.g., `presignedUrl` vs `presignedUploadUrl`), and (c) the i18n naming convention (`I18N` vs `I18n`) which has already been verified as a Pydantic `to_camel` behavior -- the decision is to keep `I18N` and update documentation. All three risks have concrete, verified mitigation strategies.

## Key Findings

### Recommended Stack

No new dependencies are needed. The fix uses existing technologies already present in the codebase. The core addition is a new `imageBackendFetch()` utility that mirrors the existing `backendFetch()` pattern but targets image_backend with X-API-Key auth.

**Core technologies (all existing):**
- **Next.js 16 Route Handlers**: BFF proxy layer -- 30+ existing routes use this pattern, and the broken media routes already exist as files
- **`imageBackendFetch()` (new utility)**: HTTP client for image_backend -- mirrors `backendFetch()` with different base URL (`IMAGE_BACKEND_URL`) and auth (`X-API-Key`)
- **`imageBackendRawFetch()` (new utility)**: Raw HTTP client for SSE stream passthrough -- returns `Response` object directly for stream forwarding
- **Browser `EventSource` API**: Client-side SSE consumption for media processing status -- built-in, no polyfill needed for admin panel (desktop browsers only)
- **Web Streams API (`ReadableStream`)**: Server-side SSE passthrough in BFF -- built-in to Node.js runtime in Next.js 16

**Environment additions:**
- `IMAGE_BACKEND_URL` and `IMAGE_BACKEND_API_KEY` in `frontend/admin/.env.local` (server-only, no `NEXT_PUBLIC_` prefix)

### Expected Features (Integration Fixes)

**Must have (blocks product creation entirely):**
- **BFF media proxy rewrite** (audit #1, #3) -- 3 route handlers must target image_backend, not main backend
- **Field name alignment** (audit #2) -- `presignedUrl`/`storageObjectId` instead of `presignedUploadUrl`/`id`
- **i18n locale enforcement** (audit #4) -- frontend must always send both `ru` and `en` locales
- **Optional `description_i18n`** (audit #7) -- `I18nDict | None = None` instead of `default_factory=dict`
- **`countryOfOrigin` in create request** (audit #8) -- field exists in domain/command but missing from Pydantic schema and router

**Should have (significantly improves reliability):**
- **Media processing status polling** (audit #9) -- SSE stream forwarding through BFF for real-time processing feedback
- **Request body filtering** (audit #3) -- BFF strips product-specific fields (`mediaType`, `role`, `sortOrder`) before forwarding to image_backend
- **Product-media linking step** -- `useSubmitProduct.js` must call main backend's `POST /products/{id}/media` after confirm to create the `MediaAsset` record
- **Error handling for image_backend unavailability** -- `imageBackendFetch` returns structured 502 errors on network failure

**Defer (v2+, not blocking creation):**
- **Full FSM UI** (audit #12) -- only DRAFT->ENRICHING needed for initial creation; all transitions can wait
- **Completeness endpoint UI** (audit #11) -- nice-to-have progress indicator, not a blocker
- **Version tracking in PATCH** (audit #13) -- no edit page exists yet; needed when edit is built
- **Spec doc I18n->I18N fix** (audit #14) -- cosmetic documentation correction

### Architecture Approach

The architecture follows a dual-client BFF pattern where the Next.js admin panel routes requests to two separate backend services based on the operation type. Catalog operations (product CRUD, media asset linking, status transitions) go through `backendFetch()` to the main backend with JWT Bearer auth. Media storage operations (presigned URL generation, upload confirmation, external import, processing status) go through `imageBackendFetch()` to the image_backend with X-API-Key server-to-server auth. The browser never communicates directly with image_backend -- the BFF is the auth bridge.

**Major components and their responsibilities:**

1. **`image-api-client.js`** (new) -- dual-function HTTP client: `imageBackendFetch()` for JSON endpoints, `imageBackendRawFetch()` for SSE stream forwarding
2. **3 BFF route handlers** (rewrite) -- `upload/route.js`, `confirm/route.js`, `external/route.js` switch from `backendFetch` to `imageBackendFetch` with URL remapping and request/response shape transformation
3. **1 BFF route handler** (new) -- `status/route.js` for SSE stream passthrough from image_backend to browser
4. **Backend schemas** (fix) -- `ProductCreateRequest` gains `country_of_origin`; 3 schemas change `description_i18n` from `I18nDict = Field(default_factory=dict)` to `I18nDict | None = None`
5. **Frontend form hook** (fix) -- `useProductForm.js` always sends both `ru` and `en` locales with Russian fallback

**Key data flow (complete upload lifecycle):**
1. Reserve -- Browser -> BFF -> image_backend -> returns presigned PUT URL
2. Upload -- Browser -> S3 directly (using presigned URL, bypasses BFF entirely)
3. Confirm -- Browser -> BFF -> image_backend -> starts async processing
4. Monitor -- Browser -> BFF -> image_backend (SSE) -> real-time status updates
5. Register -- Browser -> BFF -> main backend -> links storageObjectId to product as MediaAsset

### Critical Pitfalls

1. **Sending productId to image_backend** -- image_backend has flat URLs (`/api/v1/media/upload`), not product-scoped ones. The BFF must strip productId from the path when constructing the upstream URL. Detection: 404 from image_backend.
2. **Using JWT Bearer instead of X-API-Key** -- copy-pasting from existing BFF routes sends JWT to image_backend, which expects X-API-Key. The `imageBackendFetch()` utility prevents this by injecting X-API-Key automatically. Detection: 401 `INVALID_API_KEY`.
3. **Field name mismatch silently breaks S3 upload** -- `presignedUploadUrl` is undefined because image_backend returns `presignedUrl`. The fetch to `undefined` fails silently. Fix field names in `services/products.js` to match actual image_backend response.
4. **SSE buffering by reverse proxy** -- nginx/Railway buffers SSE events. Set `X-Accel-Buffering: no`, `Cache-Control: no-cache, no-transform`, `dynamic = 'force-dynamic'`, and `runtime = 'nodejs'` on the route handler.
5. **Race between confirm and media registration** -- `confirmMedia()` returns 202 (processing started, not completed). Frontend must poll/subscribe for completion before displaying the image. The MediaAsset record on main backend can be created immediately (it stores the reference, not the processed URL).

## Implications for Roadmap

Based on research, suggested phase structure (5 phases):

### Phase 1: Backend Schema Fixes
**Rationale:** These are additive, non-breaking backend changes with zero frontend dependencies. They unblock product creation for any API consumer, not just the admin panel. Smallest scope, highest confidence, fastest to verify.
**Delivers:** Products can be created with optional descriptions and country of origin via API.
**Addresses:** Fix 2 (optional I18nDict -- 6 locations across schemas and commands), Fix 3 (countryOfOrigin -- 2 files: schema + router)
**Avoids:** No pitfalls -- these are straightforward schema changes with existing domain support.
**Estimated scope:** ~15 lines changed across 4-5 files.

### Phase 2: Frontend i18n Locale Enforcement
**Rationale:** Independent frontend-only fix. No backend changes needed. Eliminates 422 errors when English fields are empty.
**Delivers:** Product creation form always sends valid i18n payloads with both required locales.
**Addresses:** Fix 5 (always send `ru` + `en`, fallback to Russian value for empty English fields)
**Avoids:** No pitfalls -- straightforward conditional logic change in one file.
**Estimated scope:** ~8 lines changed in `useProductForm.js`.

### Phase 3: BFF Media Proxy Infrastructure
**Rationale:** The BFF rewrite is the most complex change and the core blocker. It must come before any frontend media integration work. Creating `imageBackendFetch()` first establishes the foundation that all media route handlers depend on.
**Delivers:** Working `imageBackendFetch()` and `imageBackendRawFetch()` utilities with X-API-Key auth, proper error handling, and env var configuration.
**Addresses:** STACK.md dual-client pattern, ARCHITECTURE.md auth boundary separation
**Avoids:** Pitfall 2 (JWT vs X-API-Key), Pitfall 8 (image_backend unavailability)
**Estimated scope:** 1 new file (`image-api-client.js`), env var additions.

### Phase 4: BFF Route Handler Rewrites + SSE
**Rationale:** Depends on Phase 3 (needs `imageBackendFetch`). Each route handler is a discrete unit that can be tested independently. SSE route is new (not a rewrite).
**Delivers:** All 4 media BFF routes correctly proxy to image_backend with proper URL mapping, request/response shape transformation, and auth.
**Addresses:** Fix 4 (BFF media transformation -- 3 route rewrites + 1 new SSE route), field name mapping, request body filtering
**Avoids:** Pitfall 1 (productId in image_backend URL), Pitfall 3 (field name mismatch), Pitfall 4 (SSE buffering), Pitfall 5 (extra fields), Pitfall 7 (missing auth on SSE)
**Estimated scope:** 4 route handler files (3 rewrites, 1 new).

### Phase 5: Frontend Integration Completion
**Rationale:** Depends on Phases 1-4 (backend accepts correct payloads, BFF proxies correctly). This phase wires up the frontend submit flow and adds media status monitoring.
**Delivers:** End-to-end product creation with media upload working through the admin panel.
**Addresses:** Field name fixes in `services/products.js`, product-media linking in `useSubmitProduct.js`, SSE/polling status consumer, Fix 1 (spec doc update)
**Avoids:** Pitfall 3 (field names), Pitfall 6 (race condition -- poll before displaying), Pitfall 9 (EventSource reconnection loop)
**Estimated scope:** 2-3 files changed in admin frontend.

### Phase Ordering Rationale

- **Phases 1 and 2 are independent** and can be executed in parallel. They have no mutual dependencies and fix different systems (backend vs frontend).
- **Phase 3 must precede Phase 4** because route handlers depend on the `imageBackendFetch` utility.
- **Phase 4 must precede Phase 5** because frontend integration depends on working BFF routes.
- **Backend fixes (Phase 1) before frontend (Phase 5)** because the frontend cannot test correct behavior against a backend that rejects valid payloads.
- **Grouping BFF infrastructure (Phase 3) separately from route handlers (Phase 4)** enables focused testing: verify the client utility works before using it in route handlers.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 4 (SSE route):** SSE stream passthrough through Next.js BFF is the least commonly documented pattern. The research provides a working implementation, but edge cases around Railway deployment (connection timeouts, proxy buffering) may need validation in staging.
- **Phase 5 (media linking):** The exact sequence of confirm -> poll -> register needs to be verified against the current `useSubmitProduct.js` orchestration logic. The research identified that the linking step (`POST /products/{id}/media`) is missing entirely from the submit hook.

Phases with standard patterns (skip research-phase):
- **Phase 1 (backend schemas):** Pydantic schema changes and router parameter passing are well-documented and verified against live code.
- **Phase 2 (locale enforcement):** Simple conditional logic change in a React hook.
- **Phase 3 (imageBackendFetch):** Direct mirror of existing `backendFetch()` pattern with different credentials.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | No new dependencies. All patterns verified against existing codebase (30+ route handlers, existing `backendFetch` utility). |
| Features | HIGH | All 14 issues traced to specific lines of code. Root causes verified with live Pydantic tests (i18n aliasing, I18nDict validation). |
| Architecture | HIGH | Dual-client BFF is the established pattern. Auth boundaries verified against image_backend source code. URL mappings verified. |
| Pitfalls | HIGH | All pitfalls derived from actual code analysis, not hypothetical scenarios. Field name mismatches verified against image_backend schemas. |

**Overall confidence:** HIGH

All research was conducted against primary sources (actual codebase, Pydantic runtime behavior verification, image_backend endpoint inspection). No findings rely on inference or community opinion alone.

### Gaps to Address

- **Product-media linking step:** The research identified that `useSubmitProduct.js` does not call `POST /products/{id}/media` after confirming the upload with image_backend. The exact integration point and timing (before or after SSE monitoring) needs to be determined during Phase 5 planning.
- **S3 CORS configuration:** Browser direct upload to S3 via presigned URL requires CORS configuration on S3/MinIO. This is infrastructure config, not code. Needs verification before Phase 5 testing.
- **Railway SSE behavior:** SSE stream passthrough works in local dev but Railway's reverse proxy may buffer or timeout SSE connections. Needs production validation. The `X-Accel-Buffering: no` header is the known mitigation.
- **Deferred fixes scope:** Audit items #11 (completeness UI), #12 (full FSM), #13 (version PATCH) are deferred. They should be tracked for a follow-up milestone when the product edit page is built.

## Sources

### Primary (HIGH confidence)
- `image_backend/src/modules/storage/presentation/router.py` -- actual endpoint URLs and methods
- `image_backend/src/modules/storage/presentation/schemas.py` -- actual request/response field names
- `image_backend/src/api/dependencies/auth.py` -- X-API-Key auth mechanism
- `backend/src/modules/catalog/presentation/schemas.py` -- ProductCreateRequest, I18nDict validator
- `backend/src/modules/catalog/application/commands/create_product.py` -- CreateProductCommand fields
- `backend/src/modules/catalog/presentation/router_products.py` -- router parameter passing
- `backend/src/modules/catalog/domain/entities/product.py` -- Product.create() factory
- `backend/src/shared/schemas.py` -- CamelModel with `alias_generator=to_camel`
- `frontend/admin/src/lib/api-client.js` -- existing `backendFetch()` pattern
- `frontend/admin/src/hooks/useProductForm.js` -- form payload construction
- `frontend/admin/src/hooks/useSubmitProduct.js` -- submit orchestration
- `frontend/admin/src/services/products.js` -- API client functions with field name usage
- Live Pydantic verification: `to_camel("title_i18n")` produces `"titleI18N"` (uppercase N)
- Live Pydantic verification: `I18nDict` rejects empty dict `{}` with "Missing required locales: en, ru"

### Secondary (MEDIUM confidence)
- [Next.js 16 Route Handlers docs](https://nextjs.org/docs/app/api-reference/file-conventions/route) -- BFF patterns
- [Next.js 16 BFF Guide](https://nextjs.org/docs/app/guides/backend-for-frontend) -- dual-backend architecture
- [SSE in Next.js discussion](https://github.com/vercel/next.js/discussions/48427) -- SSE buffering workarounds
- `audit.md` -- full integration audit (14 issues catalogued)
- `product-creation-flow.md` -- product creation spec with media flow architecture

---
*Research completed: 2026-03-29*
*Ready for roadmap: yes*
