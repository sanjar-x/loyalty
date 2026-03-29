# Phase 4: BFF Upload Route - Research

**Researched:** 2026-03-30
**Domain:** Next.js Route Handlers, BFF proxy pattern, image_backend upload API
**Confidence:** HIGH

## Summary

Phase 4 creates a new BFF route `POST /api/media/upload` in the admin frontend that proxies upload requests to `image_backend POST /api/v1/media/upload` using the `imageBackendFetch()` utility created in Phase 3. The existing broken route at `/api/catalog/products/[productId]/media/upload/route.js` incorrectly uses `backendFetch()` targeting the main backend, which has no such endpoint (returns 404).

The core work is straightforward: create a new route file at `src/app/api/media/upload/route.js` that (1) reads the JSON body from the request, (2) strips product-specific fields that image_backend does not accept (`mediaType`, `role`, `sortOrder`), (3) forwards only `contentType` and `filename` to image_backend via `imageBackendFetch()`, and (4) returns the image_backend response (containing `storageObjectId`, `presignedUrl`, `expiresIn`) to the browser.

**Primary recommendation:** Create a new route at `src/app/api/media/upload/route.js` using `imageBackendFetch()`. Strip product-catalog fields before forwarding. Keep the existing broken route in place (Phase 6 will update the frontend to call the new route instead). The route requires auth check via `getAccessToken()` to prevent unauthorized proxy usage.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
None explicitly locked -- all implementation choices at Claude's discretion per CONTEXT.md.

Key constraints from ROADMAP (treated as locked):
- Forward POST /api/media/upload to image_backend POST /api/v1/media/upload (not main backend)
- Strip product-specific fields (mediaType, role, sortOrder) before forwarding to image_backend
- Response must return presignedUrl and storageObjectId from image_backend to browser

### Claude's Discretion
All implementation choices are at Claude's discretion -- pure infrastructure phase. Use ROADMAP phase goal, success criteria, and codebase conventions to guide decisions.

### Deferred Ideas (OUT OF SCOPE)
None -- discuss phase skipped.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| BFF-02 | Admin BFF route /api/media/upload proxies to image_backend POST /api/v1/media/upload | imageBackendFetch() utility available (Phase 3); image_backend UploadRequest schema accepts `{contentType, filename}`; UploadResponse returns `{storageObjectId, presignedUrl, expiresIn}` via CamelModel; existing broken route pattern documented for reference |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Next.js | 16.x | App Router Route Handlers for BFF proxy | Already installed, all existing BFF routes use this pattern |
| next/server | (bundled) | `NextResponse` for structured JSON responses | Used in every existing route handler |

### Supporting
No additional libraries needed. `imageBackendFetch()` from Phase 3 handles all HTTP communication with image_backend.

**Installation:**
```bash
# No new packages needed
```

## Architecture Patterns

### Recommended Project Structure
```
frontend/admin/src/
  app/
    api/
      media/
        upload/
          route.js              # NEW: Phase 4 — proxies to image_backend
      catalog/
        products/
          [productId]/
            media/
              upload/
                route.js        # EXISTING (broken) — left in place, Phase 6 redirects frontend
  lib/
    api-client.js               # backendFetch() -> main backend
    image-api-client.js         # imageBackendFetch() -> image_backend (Phase 3)
    auth.js                     # getAccessToken() from cookies
```

### Pattern 1: BFF Media Proxy Route (New Pattern)
**What:** A Route Handler that receives a request from the browser, strips fields the downstream service does not accept, forwards the cleaned payload to image_backend, and returns the response.
**When to use:** When the BFF must translate between frontend request shapes and backend API contracts.
**Example:**
```javascript
// NEW: frontend/admin/src/app/api/media/upload/route.js
import { NextResponse } from 'next/server';
import { imageBackendFetch } from '@/lib/image-api-client';
import { getAccessToken } from '@/lib/auth';

export async function POST(request) {
  const token = await getAccessToken();
  if (!token) {
    return NextResponse.json(
      { error: { code: 'UNAUTHORIZED', message: 'Not authenticated', details: {} } },
      { status: 401 },
    );
  }

  const body = await request.json();

  // Strip product-specific fields that image_backend doesn't accept
  const { contentType, filename } = body;
  const imagePayload = { contentType, filename };

  const { ok, status, data } = await imageBackendFetch('/api/v1/media/upload', {
    method: 'POST',
    body: JSON.stringify(imagePayload),
  });

  if (!ok) {
    return NextResponse.json(
      data ?? { error: { code: 'SERVICE_UNAVAILABLE', message: 'Image service unavailable', details: {} } },
      { status: status || 502 },
    );
  }

  return NextResponse.json(data, { status: 201 });
}
```

### Pattern 2: Existing BFF Route Pattern (Reference)
**What:** All existing BFF routes follow the same structure: auth check, parse body, call backend, return response.
**Reference:**
```javascript
// Source: frontend/admin/src/app/api/catalog/products/route.js (working example)
import { NextResponse } from 'next/server';
import { backendFetch } from '@/lib/api-client';
import { getAccessToken } from '@/lib/auth';

export async function POST(request) {
  const token = await getAccessToken();
  if (!token) {
    return NextResponse.json(
      { error: { code: 'UNAUTHORIZED', message: 'Not authenticated', details: {} } },
      { status: 401 },
    );
  }
  const body = await request.json();
  const { ok, status, data } = await backendFetch('/api/v1/catalog/products', {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!ok) {
    return NextResponse.json(
      data ?? { error: { code: 'SERVICE_UNAVAILABLE', message: 'Backend unavailable', details: {} } },
      { status: status || 502 },
    );
  }
  return NextResponse.json(data, { status: 201 });
}
```

### Anti-Patterns to Avoid
- **Forwarding all fields blindly:** The frontend sends `{ mediaType, role, contentType, sortOrder }` but image_backend only accepts `{ contentType, filename }`. Sending unknown fields will cause image_backend to return 422 (Pydantic strict validation). Always extract only the fields the downstream expects.
- **Passing JWT Bearer token to image_backend:** `imageBackendFetch()` already handles auth via X-API-Key. Do NOT pass `Authorization: Bearer` to image_backend. The `getAccessToken()` check is only for verifying the browser user is authenticated.
- **Modifying image_backend response:** The response should be forwarded as-is. Do NOT rename `storageObjectId` to `id` or `presignedUrl` to `presignedUploadUrl` in the BFF. Phase 6 will update the frontend to use the correct field names.
- **Keeping productId in the route path:** The new route should be at `/api/media/upload` (no productId), because image_backend's upload endpoint is product-agnostic. Product-media association is a separate concern handled by the main backend's `POST /products/{id}/media` endpoint.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTTP client for image_backend | Custom fetch wrapper | `imageBackendFetch()` from Phase 3 | Already handles base URL, X-API-Key auth, 502 error handling |
| Request validation | Pydantic-style validation in JS | Simple destructuring to extract expected fields | image_backend does its own Pydantic validation; BFF just strips extra fields |
| Auth middleware | Custom middleware | `getAccessToken()` from `@/lib/auth` | Standard pattern used by all existing BFF routes |

**Key insight:** The BFF route is a thin proxy. Its value is in (1) correct routing to image_backend instead of main backend, (2) field stripping, and (3) auth gating. It should NOT add logic beyond these three responsibilities.

## Common Pitfalls

### Pitfall 1: Sending extra fields to image_backend
**What goes wrong:** image_backend uses Pydantic models with strict validation. The `UploadRequest` schema only accepts `contentType` and `filename`. If the BFF forwards `mediaType`, `role`, or `sortOrder`, image_backend will return 422 with "extra fields not permitted".
**Why it happens:** Developer forwards `body` directly to image_backend without stripping product-specific fields.
**How to avoid:** Destructure only `contentType` and `filename` from the incoming body and build a new clean object for forwarding.
**Warning signs:** 422 response from image_backend with "Extra inputs are not permitted" error.

### Pitfall 2: Missing auth check in the BFF route
**What goes wrong:** Without the `getAccessToken()` check, anyone can use the BFF as an anonymous proxy to image_backend, uploading arbitrary files.
**Why it happens:** Since `imageBackendFetch()` already handles API key auth with image_backend, developer assumes browser auth is unnecessary.
**How to avoid:** Always check `getAccessToken()` first. The API key authenticates the BFF with image_backend; the JWT cookie authenticates the browser user with the BFF.
**Warning signs:** Unauthenticated requests succeed instead of returning 401.

### Pitfall 3: Wrong HTTP status code on success
**What goes wrong:** Using 200 instead of 201 for the upload response.
**Why it happens:** Default NextResponse status is 200, and developer forgets to set 201.
**How to avoid:** image_backend returns 201 for upload. The BFF should mirror this: `NextResponse.json(data, { status: 201 })`.
**Warning signs:** Frontend may not notice (it checks `res.ok`), but it violates REST conventions and breaks strict status checks.

### Pitfall 4: Content-Type header conflict
**What goes wrong:** `imageBackendFetch()` sets `Content-Type: application/json` by default, which is correct for this route since the upload request is a JSON body (not multipart). No conflict here.
**Why it happens:** Confusion between "upload route" (which sends metadata as JSON to get a presigned URL) and actual file upload (which happens client-to-S3 via the presigned URL).
**How to avoid:** Understand the flow: BFF sends JSON metadata -> gets presigned URL -> browser uploads file directly to S3 using presigned URL. The BFF never handles the actual binary file.
**Warning signs:** Attempting to handle multipart file uploads in the BFF route.

### Pitfall 5: Forgetting the filename field
**What goes wrong:** The frontend currently does not send `filename` in the upload request (it sends `mediaType`, `role`, `contentType`, `sortOrder`). If the BFF only extracts these fields, `filename` will be undefined.
**Why it happens:** Phase 4 is BFF-only; the frontend payload shape is fixed in Phase 6.
**How to avoid:** Extract `filename` from the body alongside `contentType`. If `filename` is undefined, image_backend will use its default: `upload.{extension}`. This is acceptable behavior until Phase 6 adds filename to the frontend payload.
**Warning signs:** All uploaded files get generic names like `upload.jpeg`. Not a blocker, but noted.

## Code Examples

Verified patterns from the actual codebase:

### image_backend UploadRequest schema (what BFF must send)
```python
# Source: image_backend/src/modules/storage/presentation/schemas.py
class UploadRequest(CamelModel):
    content_type: str
    filename: str | None = None
```
CamelModel converts snake_case to camelCase via `to_camel`. So the JSON body must be:
```json
{"contentType": "image/jpeg", "filename": "photo.jpg"}
```
`filename` is optional (defaults to `None`, then image_backend generates a name).

### image_backend UploadResponse schema (what browser receives)
```python
# Source: image_backend/src/modules/storage/presentation/schemas.py
class UploadResponse(CamelModel):
    storage_object_id: uuid.UUID
    presigned_url: str
    expires_in: int = 300
```
JSON output via CamelModel:
```json
{
  "storageObjectId": "550e8400-e29b-41d4-a716-446655440000",
  "presignedUrl": "https://s3.example.com/bucket/raw/550e.../upload.jpeg?X-Amz-...",
  "expiresIn": 300
}
```

### image_backend upload endpoint (target)
```python
# Source: image_backend/src/modules/storage/presentation/router.py
@media_router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def request_upload(body: UploadRequest, ...):
    # Creates StorageFile, generates presigned PUT URL, returns UploadResponse
```
Full URL: `{IMAGE_BACKEND_URL}/api/v1/media/upload`

### imageBackendFetch() utility (Phase 3 output)
```javascript
// Source: frontend/admin/src/lib/image-api-client.js
export async function imageBackendFetch(path, options = {}) {
  const { headers = {}, ...rest } = options;
  try {
    const res = await fetch(`${IMAGE_BACKEND_URL}${path}`, {
      ...rest,
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': IMAGE_BACKEND_API_KEY,
        ...headers,
      },
    });
    const data = await res.json().catch(() => null);
    return { ok: res.ok, status: res.status, data };
  } catch {
    return {
      ok: false, status: 502,
      data: { error: { code: 'IMAGE_BACKEND_UNAVAILABLE', message: 'Image service unreachable', details: {} } },
    };
  }
}
```
Return shape: `{ ok: boolean, status: number, data: object | null }`

### What the frontend currently sends (Phase 6 will fix)
```javascript
// Source: frontend/admin/src/hooks/useSubmitProduct.js lines 139-143
const slot = await reserveMediaUpload(productId, {
  mediaType: 'image',       // product-specific — strip
  role,                     // product-specific — strip
  contentType: image.file.type || 'image/jpeg',  // keep — image_backend needs this
  sortOrder,                // product-specific — strip
});
// Frontend reads: slot.presignedUploadUrl (wrong name, Phase 6 fix)
// Frontend reads: slot.id (wrong name, Phase 6 fix)
```

### Existing broken route (what Phase 4 replaces)
```javascript
// Source: frontend/admin/src/app/api/catalog/products/[productId]/media/upload/route.js
import { backendFetch } from '@/lib/api-client';  // Wrong: targets main backend
// ... forwards to /api/v1/catalog/products/${productId}/media/upload (doesn't exist in backend)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Product-scoped BFF route at `/api/catalog/products/{id}/media/upload` using `backendFetch()` | Generic BFF route at `/api/media/upload` using `imageBackendFetch()` | Phase 4 | Requests now reach image_backend instead of 404-ing at main backend |
| Forward all frontend fields blindly | Strip `mediaType`, `role`, `sortOrder`; forward only `contentType` and `filename` | Phase 4 | Prevents 422 from image_backend's strict Pydantic validation |

**Important note about the existing route:** The broken route at `src/app/api/catalog/products/[productId]/media/upload/route.js` should NOT be deleted in Phase 4. The frontend currently calls this product-scoped path. Phase 6 will update the frontend to call `/api/media/upload` instead, and then the old route can optionally be removed. Deleting it now would break the existing (already broken) flow in a different way.

## Open Questions

1. **Should the old broken route be removed or kept?**
   - What we know: The old route at `/api/catalog/products/[productId]/media/upload` is currently 404-ing because it uses `backendFetch()` targeting main backend. The new route will be at `/api/media/upload`.
   - What's unclear: Whether the old route should be deleted now or after Phase 6 updates the frontend.
   - Recommendation: Keep it for now. Phase 6 will update frontend call paths. Removing old routes can be a cleanup step after Phase 6 verification. This avoids any risk of breaking something unexpected.

2. **Should the BFF route handle `filename` derivation from `contentType`?**
   - What we know: image_backend already derives filename from contentType when filename is not provided: `body.filename or f"upload.{body.content_type.split('/')[-1]}"`.
   - What's unclear: Whether the BFF should add any filename logic.
   - Recommendation: No. Pass `filename` through if the frontend provides it, let image_backend handle the default. Keep the BFF thin.

## Project Constraints (from CLAUDE.md)

- **Architecture:** Admin BFF proxy -> image_backend directly for media operations (not through main backend)
- **Backend contracts:** Do not break existing API contracts -- only extend
- **Tech stack:** Existing stack without changes (Next.js, no additional libraries)
- **Code style:** JavaScript ES2017+, no TypeScript for admin frontend
- **BFF pattern:** Route Handlers in `src/app/api/` directory using App Router convention
- **Auth pattern:** `getAccessToken()` from `@/lib/auth` for browser auth; `imageBackendFetch()` handles service-to-service X-API-Key auth
- **Error envelope:** Uniform `{ error: { code, message, details } }` JSON structure

## Sources

### Primary (HIGH confidence)
- `frontend/admin/src/lib/image-api-client.js` -- Phase 3 output, `imageBackendFetch()` utility (full file, 36 lines)
- `frontend/admin/src/lib/api-client.js` -- existing `backendFetch()` pattern (17 lines)
- `frontend/admin/src/lib/auth.js` -- `getAccessToken()` from cookies
- `image_backend/src/modules/storage/presentation/schemas.py` -- UploadRequest/UploadResponse with CamelModel
- `image_backend/src/modules/storage/presentation/router.py` -- upload endpoint (`POST /media/upload`, returns 201)
- `image_backend/src/shared/schemas.py` -- CamelModel with `to_camel` alias generator
- `frontend/admin/src/app/api/catalog/products/[productId]/media/upload/route.js` -- existing broken route
- `frontend/admin/src/hooks/useSubmitProduct.js` -- frontend payload shape (what BFF receives)
- `frontend/admin/src/services/products.js` -- `reserveMediaUpload()` service function
- `frontend/admin/src/app/api/catalog/products/route.js` -- working BFF route pattern reference
- `audit.md` -- documents the 3 broken media routes and field mismatches

### Secondary (MEDIUM confidence)
- `.planning/workstreams/milestone/phases/03-bff-media-proxy-infrastructure/03-01-SUMMARY.md` -- Phase 3 completion summary and return shape documentation
- `.planning/workstreams/milestone/phases/03-bff-media-proxy-infrastructure/03-RESEARCH.md` -- Phase 3 research with verified auth mechanism details

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new libraries, uses Phase 3 utility and existing patterns
- Architecture: HIGH -- all source/target schemas verified from actual codebase, routing path verified from image_backend router
- Pitfalls: HIGH -- all based on actual schema analysis and field comparison between frontend payload and image_backend UploadRequest

**Research date:** 2026-03-30
**Valid until:** 2026-04-30 (stable infrastructure, no external dependency version concerns)
