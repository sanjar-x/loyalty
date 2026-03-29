# Phase 7: Frontend Media Status Polling - Research

**Researched:** 2026-03-30
**Domain:** Admin frontend media upload flow -- polling for processing completion
**Confidence:** HIGH

## Summary

Phase 7 addresses audit issue #9 (MAJOR): after `confirmMedia()` returns 202 Accepted, the admin frontend immediately proceeds to the next step without waiting for image processing to complete. This means `url` and `variants` fields on the storage object are still empty when the product status change happens, resulting in broken media references.

The image_backend already provides two status-checking mechanisms: (1) GET `/api/v1/media/{id}` returns a `MetadataResponse` with `status`, `url`, and `variants` fields, and (2) GET `/api/v1/media/{id}/status` streams SSE events. Per project constraints, we use **polling via GET `/api/v1/media/{id}`** (not SSE) because Railway may buffer/timeout SSE connections.

The implementation requires: (1) a new BFF proxy route `GET /api/media/[id]/route.js` to forward metadata requests to image_backend, (2) a `pollMediaStatus()` service function that repeatedly calls this endpoint until status is `COMPLETED` or `FAILED`, and (3) integration into `useSubmitProduct.js` so that after `confirmMedia()`, each upload waits for `COMPLETED` before proceeding. A processing overlay on image thumbnails in `ImagesSection.jsx` provides user feedback.

**Primary recommendation:** Add a BFF GET route for `/api/media/[id]`, implement a `pollMediaStatus(storageObjectId)` function with exponential backoff (500ms/1s/2s/2s... up to 60s total timeout), and call it in `useSubmitProduct.js` after each `confirmMedia()` call.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
None -- all implementation choices are at Claude's discretion per CONTEXT.md.

### Claude's Discretion
All implementation choices are at Claude's discretion. Use ROADMAP success criteria and codebase patterns.

Key constraints from ROADMAP:
- After upload confirm, poll or subscribe for processing status
- Media only displayed/attached after status COMPLETED
- User sees processing indicator while processing

From STATE.md blockers:
- S3 CORS configuration needed for browser direct upload (infrastructure, verify before testing)
- Railway SSE behavior may buffer/timeout -- polling is simpler and deployment-safe

### Deferred Ideas (OUT OF SCOPE)
None -- discuss phase skipped.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MEDIA-03 | Admin frontend polls media processing status before attaching to product (wait for COMPLETED) | BFF proxy route for GET /media/{id}, pollMediaStatus service function, integration into useSubmitProduct.js after confirmMedia(), processing indicator UI |
</phase_requirements>

## Standard Stack

### Core

No new libraries needed. This phase uses only existing project dependencies.

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Next.js | ^16.1.6 | BFF route handler (App Router API route) | Already in use for all BFF proxies |
| React | ^19.1.1 | UI components, hooks | Already the project UI framework |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| fetch (Web API) | native | HTTP calls from BFF to image_backend, client-side polling | Used by all existing service functions |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Polling GET /media/{id} | SSE via GET /media/{id}/status | SSE exists in image_backend but Railway may buffer/timeout -- polling is deployment-safe (locked decision) |
| Custom interval logic | setInterval | setInterval doesn't handle variable delays or cleanup well -- use recursive setTimeout with exponential backoff |

## Architecture Patterns

### Recommended Changes

```
frontend/admin/src/
  app/api/media/[id]/
    route.js                  # NEW -- BFF proxy: GET /api/media/{id} -> image_backend
  services/
    products.js               # MODIFY -- add pollMediaStatus() function
  hooks/
    useSubmitProduct.js        # MODIFY -- call pollMediaStatus() after confirmMedia()
  app/admin/products/add/details/
    ImagesSection.jsx          # MODIFY -- show processing overlay on uploading images
    page.module.css            # MODIFY -- add processing indicator CSS
```

### Pattern 1: BFF Proxy Route for Media Metadata

**What:** Next.js App Router API route that proxies GET requests to image_backend's GET `/api/v1/media/{id}` endpoint, using the existing `imageBackendFetch()` utility.

**When to use:** Whenever the admin frontend needs to check media processing status.

**Example:**
```javascript
// Source: existing BFF proxy pattern from frontend/admin/src/app/api/media/upload/route.js
import { NextResponse } from 'next/server';
import { imageBackendFetch } from '@/lib/image-api-client';
import { getAccessToken } from '@/lib/auth';

export async function GET(request, { params }) {
  const token = await getAccessToken();
  if (!token) {
    return NextResponse.json(
      { error: { code: 'UNAUTHORIZED', message: 'Not authenticated', details: {} } },
      { status: 401 },
    );
  }

  const { id } = await params;
  const { ok, status, data } = await imageBackendFetch(`/api/v1/media/${id}`, {
    method: 'GET',
  });

  return NextResponse.json(
    data ?? { error: { code: 'SERVICE_UNAVAILABLE', message: 'Image service unavailable', details: {} } },
    { status: ok ? 200 : (status || 502) },
  );
}
```

### Pattern 2: Polling with Exponential Backoff

**What:** A service function that polls GET `/api/media/{id}` at increasing intervals until the status is terminal (`COMPLETED` or `FAILED`).

**When to use:** After `confirmMedia()` returns 202 Accepted for each file upload.

**Key design decisions:**
- Intervals: 500ms, 1000ms, 2000ms, 2000ms, 2000ms... (cap at 2s)
- Total timeout: 60 seconds (image processing typically takes 2-10 seconds)
- On `COMPLETED`: return the metadata (url, variants)
- On `FAILED`: throw an error (non-fatal -- media upload continues for other images)
- On timeout: throw an error (treat as failure for this image, don't block the rest)

**Example:**
```javascript
// Service function pattern
export async function pollMediaStatus(storageObjectId, { maxWait = 60000 } = {}) {
  const intervals = [500, 1000, 2000]; // then repeat last
  const start = Date.now();
  let attempt = 0;

  while (Date.now() - start < maxWait) {
    const data = await api(`/api/media/${storageObjectId}`);

    if (data.status === 'COMPLETED') return data;
    if (data.status === 'FAILED') {
      const error = new Error('Media processing failed');
      error.code = 'MEDIA_PROCESSING_FAILED';
      throw error;
    }

    const delay = intervals[Math.min(attempt, intervals.length - 1)];
    await new Promise((resolve) => setTimeout(resolve, delay));
    attempt++;
  }

  const error = new Error('Media processing timed out');
  error.code = 'MEDIA_PROCESSING_TIMEOUT';
  throw error;
}
```

### Pattern 3: Integration into Upload Flow

**What:** After `confirmMedia(slot.storageObjectId)`, call `pollMediaStatus(slot.storageObjectId)` to wait for processing completion before counting the upload as successful.

**When to use:** In `useSubmitProduct.js` Step 5 (Upload media) and Step 5b (Size guide).

**Key design:**
- Polling happens inside the `Promise.allSettled` chunk, so it runs in parallel per image (up to 3 concurrent)
- Each image independently waits for its own processing
- A failure in one image's processing does not block the others (already handled by `Promise.allSettled`)
- Progress text updated to reflect "processing" state

### Pattern 4: Processing Indicator UI

**What:** While media is being uploaded/processed, show a visual overlay on the image thumbnail.

**When to use:** In `ImagesSection.jsx` when images are in a "processing" state.

**Design:** The submit hook already has a `step` state showing "media" phase and a progress counter. The simplest approach is to keep the existing progress display (`Загрузка изображений (2/5)...`) which already communicates that media is being processed. No per-image processing overlay is needed in `ImagesSection` because:
1. Images are only uploaded during the submit flow (not visible in gallery during processing)
2. The step/progress state in `useSubmitProduct` already provides user feedback
3. The submit button is disabled during submission

However, if per-image visual feedback is desired, the approach would be adding a `processing` flag per image in local state and showing a pulse/spinner overlay.

**Recommendation:** Keep it simple -- update the progress text to distinguish upload vs. processing stages within the existing step display. For example: `"Обработка изображений (3/5)..."` after all uploads complete and polling begins.

### Anti-Patterns to Avoid

- **No timeout on polling:** Always set a maximum wait time. Without it, a stuck image_backend could block the entire product creation indefinitely.
- **Polling too fast:** Don't poll every 100ms. Image processing involves Pillow resize + S3 upload, typically taking 2-10 seconds. Start at 500ms, cap at 2s.
- **Blocking the entire batch on one failure:** Use `Promise.allSettled` (already in use) so one failed image doesn't prevent others from completing.
- **Using SSE through the BFF:** The BFF is a Next.js API route (serverless function on Railway), not suited for long-lived SSE connections. Polling via GET is the correct pattern.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTTP polling | WebSocket/SSE client | Simple async loop with setTimeout | Polling 5-15 times max is trivial; no library needed |
| Exponential backoff | npm library (e.g., p-retry) | ~10 lines of custom code | Too simple to justify a dependency; the project has no retry library |
| Processing animation | Complex animation library | CSS `@keyframes pulse` | Already exists in page.module.css |

**Key insight:** This phase is a small integration fix -- adding ~60 lines across 4 files. No new dependencies are needed.

## Common Pitfalls

### Pitfall 1: CamelCase vs Snake_case Field Mismatch

**What goes wrong:** The image_backend returns fields in camelCase (via `CamelModel` / `to_camel`). For example, `storage_object_id` becomes `storageObjectId`, `size_bytes` becomes `sizeBytes`, `content_type` becomes `contentType`, `image_variants` becomes `imageVariants`, `created_at` becomes `createdAt`.

**Why it happens:** The `CamelModel` base in `image_backend/src/shared/schemas.py` uses `pydantic.alias_generators.to_camel`. This was already a source of bugs fixed in Phase 6.

**How to avoid:** The `MetadataResponse` fields arrive as: `storageObjectId`, `status`, `url`, `contentType`, `sizeBytes`, `variants` (array of `{size, width, height, url}`), `createdAt`. Use these exact camelCase names in the frontend code.

**Warning signs:** 404 or undefined values when accessing response fields.

### Pitfall 2: StorageStatus Enum Values are UPPERCASE

**What goes wrong:** The `StorageStatus` enum in `value_objects.py` uses UPPERCASE values: `PENDING_UPLOAD`, `PROCESSING`, `COMPLETED`, `FAILED`. But the `MetadataResponse.status` field serializes the raw enum `.value` string, so the frontend receives these as UPPERCASE strings.

**Why it happens:** `StorageStatus(StrEnum)` has `COMPLETED = "COMPLETED"` (uppercase values), and the router returns `storage_file.status.value` which is the raw string.

**How to avoid:** Compare against uppercase strings: `data.status === 'COMPLETED'`, `data.status === 'FAILED'`. Do NOT compare against lowercase `'completed'` or `'failed'`.

**Warning signs:** Polling never terminates because `'processing' !== 'PROCESSING'`.

**HOWEVER** -- double-check needed: The SSE endpoint and task code use lowercase strings (`"completed"`, `"failed"`) in the Redis publish payloads. The GET metadata endpoint returns `storage_file.status.value` which IS uppercase. So the polling endpoint (GET /media/{id}) returns UPPERCASE, while the SSE endpoint uses lowercase. Since we use polling (GET), compare against UPPERCASE.

### Pitfall 3: External Media Doesn't Need Polling

**What goes wrong:** Calling `pollMediaStatus()` after `addExternalMedia()` wastes time because external imports complete synchronously (status is already `COMPLETED` when the 201 response returns).

**Why it happens:** The `/external` endpoint in image_backend downloads, processes, and persists the image synchronously before responding.

**How to avoid:** Only add polling after `confirmMedia()` (file upload flow). Skip polling for `addExternalMedia()` (URL flow).

**Warning signs:** Unnecessary 1-2 second delays for URL-imported images.

### Pitfall 4: Confirm Response Shape

**What goes wrong:** Assuming `confirmMedia()` returns processing status or url. The `ConfirmResponse` only returns `{ storageObjectId, status: "processing" }`. The full metadata with url/variants is only available from GET `/media/{id}`.

**Why it happens:** The confirm endpoint is fire-and-forget (202 Accepted) -- it dispatches a background task and returns immediately.

**How to avoid:** After confirm, immediately start polling GET `/media/{id}` to get the full metadata.

### Pitfall 5: BFF Route Path Collision

**What goes wrong:** Creating a route at `app/api/media/[id]/route.js` that handles GET, while `app/api/media/[id]/confirm/route.js` handles POST. The dynamic segment `[id]` must be consistent in both paths.

**Why it happens:** Next.js App Router uses folder-based routing. Both routes share the `[id]` segment.

**How to avoid:** This is already the correct structure. `GET /api/media/123` resolves to `app/api/media/[id]/route.js` and `POST /api/media/123/confirm` resolves to `app/api/media/[id]/confirm/route.js`. No collision.

## Code Examples

### Image Backend MetadataResponse (what GET /media/{id} returns)

```json
// Source: image_backend/src/modules/storage/presentation/schemas.py MetadataResponse
// Via CamelModel (to_camel aliasing)
{
  "storageObjectId": "019...",
  "status": "COMPLETED",          // PENDING_UPLOAD | PROCESSING | COMPLETED | FAILED
  "url": "https://cdn.example.com/public/019....webp",
  "contentType": "image/webp",
  "sizeBytes": 45230,
  "variants": [
    { "size": "thumb", "width": 150, "height": 150, "url": "https://cdn.../019..._thumb.webp" },
    { "size": "md", "width": 600, "height": 600, "url": "https://cdn.../019..._md.webp" },
    { "size": "lg", "width": 1200, "height": 1200, "url": "https://cdn.../019..._lg.webp" }
  ],
  "createdAt": "2026-03-30T12:00:00Z"
}
```

### Confirm Response (what POST /media/{id}/confirm returns)

```json
// Source: image_backend/src/modules/storage/presentation/schemas.py ConfirmResponse
{
  "storageObjectId": "019...",
  "status": "processing"    // Note: lowercase hardcoded default in schema
}
```

### Current Upload Flow in useSubmitProduct.js (before this phase)

```javascript
// Source: frontend/admin/src/hooks/useSubmitProduct.js lines 131-139
// Currently: reserve -> upload to S3 -> confirm -> DONE (no polling)
const slot = await reserveMediaUpload({
  contentType: image.file.type || 'image/jpeg',
  filename: image.file.name,
});
await uploadToS3(slot.presignedUrl, image.file);
await confirmMedia(slot.storageObjectId);
// BUG: No waiting for COMPLETED -- url and variants may be empty
```

### Target Upload Flow (after this phase)

```javascript
// After fix: reserve -> upload to S3 -> confirm -> poll until COMPLETED -> DONE
const slot = await reserveMediaUpload({
  contentType: image.file.type || 'image/jpeg',
  filename: image.file.name,
});
await uploadToS3(slot.presignedUrl, image.file);
await confirmMedia(slot.storageObjectId);
const result = await pollMediaStatus(slot.storageObjectId);
// result.status === 'COMPLETED', result.url has the CDN URL
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No status check after confirm | Will poll GET /media/{id} | Phase 7 | Ensures url/variants populated before product attachment |
| Frontend proceeds immediately after 202 | Frontend waits for COMPLETED | Phase 7 | Fixes audit issue #9 (MAJOR) |

**Deprecated/outdated:**
- SSE for status streaming: exists in image_backend (GET /media/{id}/status) but explicitly deferred per REQUIREMENTS.md ("SSE can be added later"). Polling is the chosen approach.

## Open Questions

1. **Should pollMediaStatus return value be used for anything beyond status check?**
   - What we know: The metadata includes `url` and `variants` after COMPLETED. Currently the useSubmitProduct flow does not attach media to the product (no POST `/products/{id}/media` call exists yet).
   - What's unclear: Whether Phase 7 should also add the product media attachment call, or if that's Phase 8 (UI enhancements).
   - Recommendation: Phase 7 scope is MEDIA-03 (poll for status). The attach-to-product step is not listed as a Phase 7 requirement. Keep Phase 7 focused on polling; the returned data is currently unused beyond confirming COMPLETED status. Future phases can use it for attachment.

2. **Status string comparison: uppercase vs lowercase?**
   - What we know: `StorageStatus` enum values are UPPERCASE (`"COMPLETED"`, `"FAILED"`). The `MetadataResponse` serializes `storage_file.status.value` which preserves UPPERCASE. The SSE payloads use lowercase (`"completed"`, `"failed"`).
   - What's unclear: Whether `CamelModel` or any middleware transforms the status value before it reaches the frontend.
   - Recommendation: The `MetadataResponse.status` field is `str` type, not an enum, and receives `storage_file.status.value` directly. CamelModel's `to_camel` alias generator only affects field NAMES, not field VALUES. So the frontend receives UPPERCASE. Compare against `'COMPLETED'` and `'FAILED'`. Verify during implementation by checking actual response.

## Sources

### Primary (HIGH confidence)
- `image_backend/src/modules/storage/presentation/router.py` -- all media endpoints, confirm returns 202, GET /{id} returns MetadataResponse
- `image_backend/src/modules/storage/presentation/schemas.py` -- MetadataResponse shape, ConfirmResponse shape, CamelModel aliasing
- `image_backend/src/modules/storage/domain/value_objects.py` -- StorageStatus enum (PENDING_UPLOAD, PROCESSING, COMPLETED, FAILED)
- `image_backend/src/modules/storage/presentation/tasks.py` -- background processing task, publishes SSE on completion
- `frontend/admin/src/hooks/useSubmitProduct.js` -- current upload flow (lines 131-139), chunk processing pattern
- `frontend/admin/src/services/products.js` -- existing API functions (reserveMediaUpload, uploadToS3, confirmMedia)
- `frontend/admin/src/lib/image-api-client.js` -- imageBackendFetch utility for BFF proxy
- `frontend/admin/src/app/api/media/[id]/confirm/route.js` -- existing BFF pattern for media routes
- `backend/docs/api/product-creation-flow.md` -- spec STEP 5 (Polling) describes GET /media/{id} approach

### Secondary (MEDIUM confidence)
- `audit.md` issue #9 -- confirms this is a MAJOR issue: no polling after confirm causes empty url/variants

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new libraries, uses existing project patterns
- Architecture: HIGH -- BFF proxy pattern is well-established in Phase 3-6, polling logic is straightforward
- Pitfalls: HIGH -- directly read from source code (enum values, response shapes, CamelModel behavior)

**Research date:** 2026-03-30
**Valid until:** 2026-04-30 (stable -- no external dependency changes expected)
