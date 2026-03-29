# Phase 6: Frontend Media Field Alignment - Research

**Researched:** 2026-03-30
**Domain:** Admin frontend media upload service layer (JavaScript, Next.js App Router)
**Confidence:** HIGH

## Summary

Phase 6 fixes the mismatch between what the admin frontend sends/reads in media API calls and what the image_backend (via BFF proxy routes created in Phases 4+5) actually expects/returns. The problem is concentrated in two files: `src/services/products.js` (API service functions) and `src/hooks/useSubmitProduct.js` (orchestration hook that calls those services).

The current code has three categories of bugs: (1) service functions call OLD broken routes (`/api/catalog/products/{id}/media/upload`, `.../confirm`, `.../external`) that proxy through main backend instead of calling the new BFF routes (`/api/media/upload`, `/api/media/{id}/confirm`, `/api/media/external`) that proxy directly to image_backend; (2) request payloads include fields image_backend does not accept (`mediaType`, `role`, `sortOrder`, `externalUrl`) and omit fields it does accept (`filename`); (3) response field names are wrong (`slot.presignedUploadUrl` should be `slot.presignedUrl`, `slot.id` should be `slot.storageObjectId`).

**Primary recommendation:** Rewrite the three media service functions in `products.js` to use new BFF routes with correct field names, then update `useSubmitProduct.js` to use the corrected response fields. The old broken BFF routes at `/api/catalog/products/{id}/media/*` should be deleted as cleanup.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MEDIA-01 | Admin frontend uses correct field names from image_backend responses (presignedUrl, storageObjectId) | Upload response returns `{ storageObjectId, presignedUrl, expiresIn }` via CamelModel aliasing. Frontend currently reads `slot.presignedUploadUrl` and `slot.id` -- both wrong. Fix in useSubmitProduct.js lines 145, 146, 181, 182. |
| MEDIA-02 | Admin frontend sends correct upload request schema to image_backend ({contentType, filename}) | image_backend UploadRequest accepts `{ contentType: str, filename?: str }`. Frontend sends `{ mediaType, role, contentType, sortOrder }` -- BFF strips extras, but `filename` is missing. Fix in useSubmitProduct.js lines 139-143 and 175-179. Also external import expects `{ url }` not `{ externalUrl, mediaType, role, sortOrder }`. |
</phase_requirements>

## Standard Stack

No new libraries needed. This phase modifies existing JavaScript files only.

### Core (existing, no changes)
| Library | Version | Purpose | Role in Phase |
|---------|---------|---------|---------------|
| Next.js | ^16.1.x | App Router, API routes | BFF routes already created in Phases 4+5 |
| React | 19.x | UI rendering | No UI changes needed |

## Architecture Patterns

### Current Architecture (broken)

```
useSubmitProduct.js
  --> products.js::reserveMediaUpload(productId, payload)
      --> /api/catalog/products/{productId}/media/upload   [OLD broken BFF route -> main backend]
  --> products.js::uploadToS3(slot.presignedUploadUrl, file)
      --> S3 direct upload [presignedUploadUrl is WRONG field name]
  --> products.js::confirmMedia(productId, slot.id)
      --> /api/catalog/products/{productId}/media/{slot.id}/confirm [OLD broken route, slot.id is WRONG]
  --> products.js::addExternalMedia(productId, { externalUrl, mediaType, role, sortOrder })
      --> /api/catalog/products/{productId}/media/external [OLD broken route, WRONG payload]
```

### Target Architecture (fixed)

```
useSubmitProduct.js
  --> products.js::reserveMediaUpload({ contentType, filename })
      --> /api/media/upload  [NEW BFF route -> image_backend directly]
      returns { storageObjectId, presignedUrl, expiresIn }
  --> products.js::uploadToS3(slot.presignedUrl, file)
      --> S3 direct upload [CORRECT field name]
  --> products.js::confirmMedia(slot.storageObjectId)
      --> /api/media/{storageObjectId}/confirm [NEW BFF route, CORRECT field]
  --> products.js::addExternalMedia({ url })
      --> /api/media/external [NEW BFF route, CORRECT payload { url }]
```

### Key Insight: Decoupling media storage from product attachment

The image_backend is a standalone media service -- it knows nothing about products. Upload/confirm/external are product-agnostic operations. The `productId` parameter in current service functions is vestigial from the old architecture that routed through main backend.

In the corrected flow, `productId` is NOT needed for media upload/confirm/external. It will only be needed later (Phase 7+) when attaching a completed storage object to a product via the main backend's `POST /api/v1/catalog/products/{productId}/media` endpoint.

### Files to Modify

| File | Changes | Lines Affected |
|------|---------|----------------|
| `src/services/products.js` | Rewrite `reserveMediaUpload`, `confirmMedia`, `addExternalMedia` to use new BFF routes + correct field names. Remove `productId` parameter from signatures. | Lines 63-87 |
| `src/hooks/useSubmitProduct.js` | Update all callsites to use new service signatures + correct response field names (`presignedUrl`, `storageObjectId`). Remove `productId` from media service calls. | Lines 130-183 |

### Files to Delete (cleanup)

| File | Reason |
|------|--------|
| `src/app/api/catalog/products/[productId]/media/upload/route.js` | Replaced by `/api/media/upload` (Phase 4) |
| `src/app/api/catalog/products/[productId]/media/[mediaId]/confirm/route.js` | Replaced by `/api/media/[id]/confirm` (Phase 5) |
| `src/app/api/catalog/products/[productId]/media/external/route.js` | Replaced by `/api/media/external` (Phase 5) |

Phase 4 summary explicitly flagged this: "Leave existing broken route at /api/catalog/products/[productId]/media/upload for Phase 6 cleanup."

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Content type detection | Custom MIME type mapping | `file.type` from browser File API | Browser already knows the MIME type from the file picker |
| Filename extraction | Custom filename generation | `file.name` from browser File API | Browser File objects have the original filename |

## Common Pitfalls

### Pitfall 1: Forgetting the external import request schema difference
**What goes wrong:** Frontend sends `{ externalUrl, mediaType, role, sortOrder }` but image_backend's `ExternalImportRequest` only accepts `{ url }`. The BFF external route passes body through as-is. image_backend will reject or ignore the extra fields, and fail to find the `url` field (it receives `externalUrl` instead).
**Why it happens:** The old code used product-scoped external media naming (`externalUrl` = the URL of the external image). image_backend's schema simply uses `url`.
**How to avoid:** Change the service function to send `{ url: imageUrl }` instead of `{ externalUrl: imageUrl, mediaType, role, sortOrder }`.
**Warning signs:** 422 error from image_backend, "url field required" validation error.

### Pitfall 2: Breaking the role/sortOrder information loss
**What goes wrong:** The current code passes `role` and `sortOrder` to the media upload. After this fix, they are no longer sent to image_backend (because image_backend does not care about product-specific roles). However, these values ARE needed when later attaching the storage object to the product via main backend.
**Why it happens:** role/sortOrder are product-catalog concepts, not media-storage concepts. They belong in the "attach media to product" step, not the "upload to image storage" step.
**How to avoid:** Keep `role` and `sortOrder` in the `useSubmitProduct.js` orchestration logic (they are already computed in the `uploadTasks` array). They just should NOT be sent to the image_backend. They will be used in a future step (Phase 7/8) when calling `POST /api/v1/catalog/products/{productId}/media` on the main backend to attach the storage object.
**Warning signs:** If role/sortOrder are completely removed from the orchestration code, the attach-to-product step (future phase) will not have them available.

### Pitfall 3: The `slot.id` vs `slot.storageObjectId` confusion
**What goes wrong:** Current code does `confirmMedia(productId, slot.id)` -- reads `id` from the upload response. But image_backend's `UploadResponse` serializes as `{ storageObjectId, presignedUrl, expiresIn }` -- there is no `id` field.
**Why it happens:** The old architecture expected a media asset ID from the main backend. The new architecture returns a storage object ID from image_backend.
**How to avoid:** Use `slot.storageObjectId` everywhere.

### Pitfall 4: Size guide upload uses same broken pattern
**What goes wrong:** The size guide upload (lines 165-184 in useSubmitProduct.js) has the SAME bugs as the main image upload -- wrong field names, wrong routes, wrong payload.
**Why it happens:** It was copy-pasted from the main image upload logic.
**How to avoid:** Apply the same fixes to both the main image upload block (lines 127-158) and the size guide upload block (lines 163-184).

## Code Examples

### Current broken service functions (products.js)
```javascript
// BROKEN: Uses old product-scoped routes, wrong field names
export async function reserveMediaUpload(productId, payload) {
  return api(`/api/catalog/products/${productId}/media/upload`, jsonOpts(payload));
}

export async function confirmMedia(productId, mediaId) {
  return api(`/api/catalog/products/${productId}/media/${mediaId}/confirm`, { method: 'POST' });
}

export async function addExternalMedia(productId, payload) {
  return api(`/api/catalog/products/${productId}/media/external`, jsonOpts(payload));
}
```

### Fixed service functions (products.js)
```javascript
// FIXED: Uses new BFF routes, correct field names
export async function reserveMediaUpload(payload) {
  // payload = { contentType, filename }
  return api('/api/media/upload', jsonOpts(payload));
}

export async function confirmMedia(storageObjectId) {
  return api(`/api/media/${storageObjectId}/confirm`, { method: 'POST' });
}

export async function addExternalMedia(payload) {
  // payload = { url }
  return api('/api/media/external', jsonOpts(payload));
}
```

### Current broken orchestration (useSubmitProduct.js -- file upload block)
```javascript
// BROKEN: Wrong payload, wrong response fields, wrong function signatures
const slot = await reserveMediaUpload(productId, {
  mediaType: 'image',
  role,
  contentType: image.file.type || 'image/jpeg',
  sortOrder,
});
await uploadToS3(slot.presignedUploadUrl, image.file);  // WRONG: presignedUploadUrl
await confirmMedia(productId, slot.id);                   // WRONG: slot.id
```

### Fixed orchestration (useSubmitProduct.js -- file upload block)
```javascript
// FIXED: Correct payload, correct response fields
const slot = await reserveMediaUpload({
  contentType: image.file.type || 'image/jpeg',
  filename: image.file.name,
});
await uploadToS3(slot.presignedUrl, image.file);           // CORRECT: presignedUrl
await confirmMedia(slot.storageObjectId);                   // CORRECT: storageObjectId
```

### Current broken orchestration (useSubmitProduct.js -- external URL block)
```javascript
// BROKEN: Wrong payload, wrong function signature
await addExternalMedia(productId, {
  externalUrl: image.url,
  mediaType: 'image',
  role,
  sortOrder,
});
```

### Fixed orchestration (useSubmitProduct.js -- external URL block)
```javascript
// FIXED: Correct payload -- image_backend ExternalImportRequest only accepts { url }
await addExternalMedia({ url: image.url });
```

## Image Backend API Contract Reference

These are the exact JSON shapes the BFF routes forward to/from image_backend (CamelModel converts snake_case to camelCase):

### POST /api/v1/media/upload
**Request:** `{ "contentType": "image/jpeg", "filename": "photo.jpg" }` (filename optional)
**Response (201):** `{ "storageObjectId": "uuid", "presignedUrl": "https://s3...", "expiresIn": 300 }`

### POST /api/v1/media/{storageObjectId}/confirm
**Request:** (no body)
**Response (202):** `{ "storageObjectId": "uuid", "status": "processing" }`

### POST /api/v1/media/external
**Request:** `{ "url": "https://example.com/image.jpg" }`
**Response (201):** `{ "storageObjectId": "uuid", "url": "https://cdn.../public/uuid.webp", "variants": [...] }`

## Scope Boundary

### In scope (Phase 6)
- Fix service function URLs (old routes -> new BFF routes)
- Fix service function signatures (remove unnecessary productId)
- Fix request payloads (send correct fields)
- Fix response field reads (presignedUrl, storageObjectId)
- Delete old broken BFF route files (cleanup per Phase 4 decision)

### Out of scope (future phases)
- Attaching storageObjectId to a product via main backend (Phase 7/8 -- `POST /api/v1/catalog/products/{id}/media`)
- Media processing status polling (Phase 7 -- MEDIA-03)
- Product-level role/sortOrder assignment (Phase 7/8 -- when attaching to product)

## Open Questions

1. **Filename for external URL imports**
   - What we know: External import on image_backend extracts filename from URL path (`body.url.split("/")[-1].split("?")[0]`), so no explicit filename needed from frontend.
   - What's unclear: Nothing -- this is handled server-side.
   - Recommendation: No action needed.

2. **Should uploadToS3 function name change?**
   - What we know: The function signature `uploadToS3(presignedUrl, file)` already takes a presigned URL. The parameter was just named correctly in the function definition even though the callsite passed the wrong field.
   - What's unclear: Nothing.
   - Recommendation: No change to uploadToS3 function -- just fix the callsite to pass `slot.presignedUrl`.

## Sources

### Primary (HIGH confidence)
- `image_backend/src/modules/storage/presentation/schemas.py` -- UploadRequest, UploadResponse, ExternalImportRequest, ExternalImportResponse exact field definitions
- `image_backend/src/shared/schemas.py` -- CamelModel confirming `to_camel` aliasing (snake_case -> camelCase in JSON)
- `image_backend/src/modules/storage/presentation/router.py` -- Exact endpoint paths and response models
- `frontend/admin/src/services/products.js` -- Current broken service functions (lines 63-87)
- `frontend/admin/src/hooks/useSubmitProduct.js` -- Current broken orchestration (lines 127-184)
- `frontend/admin/src/app/api/media/upload/route.js` -- New BFF upload route (Phase 4)
- `frontend/admin/src/app/api/media/[id]/confirm/route.js` -- New BFF confirm route (Phase 5)
- `frontend/admin/src/app/api/media/external/route.js` -- New BFF external route (Phase 5)
- `audit.md` -- Original audit identifying field mismatches (issues #2 and #3)
- Phase 4 summary (04-01-SUMMARY.md) -- Confirms old routes left for Phase 6 cleanup

### Secondary (MEDIUM confidence)
- None needed -- all findings are from direct codebase inspection.

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - no new libraries, existing code only
- Architecture: HIGH - all service function signatures, request/response schemas verified by reading actual source code on both sides (frontend + image_backend)
- Pitfalls: HIGH - every pitfall identified from actual code inspection of current vs expected behavior

**Research date:** 2026-03-30
**Valid until:** Stable -- these are code-level facts, not library version concerns
