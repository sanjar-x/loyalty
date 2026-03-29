# Phase 5: BFF Confirm & External Routes - Research

**Researched:** 2026-03-30
**Domain:** Next.js App Router BFF proxy routes (admin -> image_backend)
**Confidence:** HIGH

## Summary

Phase 5 creates two new BFF proxy routes in the admin Next.js application that forward media confirm and external import requests directly to `image_backend` using the `imageBackendFetch()` utility created in Phase 3. This is a straightforward infrastructure task with well-established patterns already in the codebase.

The key insight is that the admin frontend currently has media routes nested under `/api/catalog/products/[productId]/media/...` that incorrectly proxy through the main backend using `backendFetch()` with JWT auth. The main backend does NOT have these media endpoints -- they only exist in `image_backend`. Phase 5 creates the correct top-level `/api/media/` routes that go directly to `image_backend` with X-API-Key auth. The old product-scoped routes remain temporarily (they will be replaced when frontend service calls are updated in Phase 6).

**Primary recommendation:** Create two new Next.js route handler files at `src/app/api/media/[id]/confirm/route.js` and `src/app/api/media/external/route.js`, each using `imageBackendFetch()` to proxy to the corresponding `image_backend` endpoint. No request body for confirm, JSON body passthrough for external.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
None -- all implementation choices are at Claude's discretion (infrastructure phase).

Key constraints from ROADMAP:
- POST /api/media/{id}/confirm forwards to image_backend POST /api/v1/media/{id}/confirm
- POST /api/media/external forwards to image_backend POST /api/v1/media/external
- Both routes use imageBackendFetch() with X-API-Key auth (not backendFetch with JWT)

### Claude's Discretion
All implementation choices are at Claude's discretion -- pure infrastructure phase. Use ROADMAP phase goal, success criteria, and codebase conventions to guide decisions.

### Deferred Ideas (OUT OF SCOPE)
None -- discuss phase skipped.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| BFF-03 | Admin BFF route /api/media/{id}/confirm proxies to image_backend POST /api/v1/media/{id}/confirm | Confirm endpoint takes no body, returns 202 with `{ storageObjectId, status: "processing" }`. Route must use `imageBackendFetch()` with path `/api/v1/media/${id}/confirm` |
| BFF-04 | Admin BFF route /api/media/external proxies to image_backend POST /api/v1/media/external | External endpoint takes JSON body `{ url: string }`, returns 201 with `{ storageObjectId, url, variants[] }`. Route must passthrough JSON body via `imageBackendFetch()` |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- **Architecture:** Admin BFF proxy -> image_backend directly for media operations (not through main backend)
- **Backend contracts:** Don't break existing API contracts -- only extend
- **Tech stack:** Existing stack without changes (Next.js 16, JavaScript ES2017+, no TypeScript in admin)
- **Admin frontend:** Server-state via Next.js API routes, no global state manager
- **BFF pattern:** One file per upstream service (`api-client.js` for backend, `image-api-client.js` for image_backend)

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Next.js | ^16.1.6 | App Router with Route Handlers for BFF | Already in use, provides file-based routing for API endpoints |
| imageBackendFetch | Phase 3 | HTTP client for image_backend with X-API-Key | Created in Phase 3 specifically for these routes |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| NextResponse | built-in | JSON response construction | All route handlers |

No additional packages needed -- everything is already installed.

## Architecture Patterns

### Recommended Route Structure
```
src/app/api/media/
  [id]/
    confirm/
      route.js          # POST -> image_backend POST /api/v1/media/{id}/confirm
  external/
    route.js            # POST -> image_backend POST /api/v1/media/external
```

### Pattern 1: BFF Proxy Route (no body, passthrough status)
**What:** Route that proxies a POST with no request body, forwarding the response and status code
**When to use:** Confirm endpoint -- client sends POST with empty body, image_backend returns 202
**Example:**
```javascript
// Source: Existing pattern from catalog/products/[productId]/status/route.js + Phase 3 imageBackendFetch
import { NextResponse } from 'next/server';
import { imageBackendFetch } from '@/lib/image-api-client';

export async function POST(request, { params }) {
  const { id } = await params;

  const { ok, status, data } = await imageBackendFetch(
    `/api/v1/media/${id}/confirm`,
    { method: 'POST' },
  );

  return NextResponse.json(
    data ?? { error: { code: 'SERVICE_UNAVAILABLE' } },
    { status: ok ? 202 : (status || 502) },
  );
}
```

### Pattern 2: BFF Proxy Route (JSON body passthrough)
**What:** Route that reads JSON body from client and forwards it to image_backend
**When to use:** External import endpoint -- client sends `{ url }`, image_backend returns 201
**Example:**
```javascript
// Source: Existing pattern from catalog/products/[productId]/media/external/route.js (adapted)
import { NextResponse } from 'next/server';
import { imageBackendFetch } from '@/lib/image-api-client';

export async function POST(request) {
  const body = await request.json();

  const { ok, status, data } = await imageBackendFetch(
    '/api/v1/media/external',
    { method: 'POST', body: JSON.stringify(body) },
  );

  return NextResponse.json(
    data ?? { error: { code: 'SERVICE_UNAVAILABLE' } },
    { status: ok ? 201 : (status || 502) },
  );
}
```

### Key Difference From Old Routes: No JWT Auth, No productId

The existing broken routes at `src/app/api/catalog/products/[productId]/media/...`:
1. Import `backendFetch` (wrong upstream -- main backend)
2. Import `getAccessToken` and check JWT (wrong auth -- image_backend uses API key)
3. Include `productId` in the path (wrong -- image_backend is not product-scoped)

The new routes:
1. Import `imageBackendFetch` (correct upstream -- image_backend directly)
2. No JWT auth needed -- `imageBackendFetch` adds X-API-Key automatically
3. No `productId` -- image_backend operates on `storageObjectId` only

### Anti-Patterns to Avoid
- **Adding JWT auth to these routes:** imageBackendFetch handles auth via X-API-Key header. Adding getAccessToken/Bearer would be redundant and wrong.
- **Nesting under /api/catalog/products/[productId]/media/:** These routes are NOT product-scoped. Image_backend deals with storage objects independently of products.
- **Setting Content-Type in the confirm route:** imageBackendFetch already sets `Content-Type: application/json` by default. The confirm endpoint has no body, but the default header is harmless.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| X-API-Key auth to image_backend | Manual header injection | `imageBackendFetch()` from Phase 3 | Already handles auth, error wrapping, 502 fallback |
| Error response formatting | Custom error shapes | Passthrough `data` from imageBackendFetch | image_backend returns structured errors; just relay them |
| Network error handling | try/catch in route handler | `imageBackendFetch()` internal catch | Already returns `{ ok: false, status: 502, data: { error: {...} } }` on network failure |

## Common Pitfalls

### Pitfall 1: Forgetting `await params` in Next.js 16
**What goes wrong:** Next.js 16 changed route handler params to be a Promise -- accessing `params.id` without `await` returns undefined.
**Why it happens:** Next.js 15+ made params async; older patterns used `const { id } = params` directly.
**How to avoid:** Always destructure after await: `const { id } = await params;`
**Warning signs:** `id` is `undefined`, image_backend returns 422 or 404 for path `/api/v1/media/undefined/confirm`.

### Pitfall 2: Sending Content-Type Without Body on Confirm Route
**What goes wrong:** Not actually a problem here. `imageBackendFetch` always sets `Content-Type: application/json`. FastAPI ignores Content-Type when there's no body expected, so this is harmless.
**How to avoid:** No action needed -- just documenting that this is not a concern.

### Pitfall 3: Using Wrong Success Status Code
**What goes wrong:** Returning 200 instead of 202 for confirm, or 200 instead of 201 for external.
**Why it happens:** Copy-paste from other routes that use 200.
**How to avoid:** Match image_backend's documented status codes:
- Confirm: 202 Accepted (processing starts asynchronously)
- External: 201 Created (import is synchronous, resource created)

### Pitfall 4: Old Routes Still Exist (Not a Bug)
**What goes wrong:** Developers may be confused that both `/api/media/{id}/confirm` and `/api/catalog/products/[productId]/media/[mediaId]/confirm` exist.
**Why it happens:** Phase 5 creates new correct routes; Phase 6 updates frontend to use them. Old routes remain until unused.
**How to avoid:** This is expected. Phase 6 will update the frontend service calls to point to the new routes. Old routes can be removed after Phase 6 verification.

## Code Examples

### image_backend Confirm Endpoint Contract
```
POST /api/v1/media/{storage_object_id}/confirm

Request: No body
Response (202):
{
  "storageObjectId": "uuid",
  "status": "processing"
}

Errors:
- 404: Storage object not found
- 422: File not found in S3 (upload not completed)
- 409: (for reupload, not confirm -- but worth noting)
```
Source: `image_backend/src/modules/storage/presentation/router.py` lines 165-200, `schemas.py` ConfirmResponse

### image_backend External Import Endpoint Contract
```
POST /api/v1/media/external

Request:
{
  "url": "https://example.com/image.jpg"
}

Response (201):
{
  "storageObjectId": "uuid",
  "url": "https://s3.../public/uuid.webp",
  "variants": [
    { "size": "thumb", "width": 150, "height": 150, "url": "..." },
    { "size": "md", "width": 600, "height": 600, "url": "..." },
    { "size": "lg", "width": 1200, "height": 1200, "url": "..." }
  ]
}

Errors:
- 422: Failed to download image (HTTP error) or file too large (>10MB)
```
Source: `image_backend/src/modules/storage/presentation/router.py` lines 331-404, `schemas.py` ExternalImportRequest/Response

### imageBackendFetch API (Phase 3 Output)
```javascript
// From: frontend/admin/src/lib/image-api-client.js
import { imageBackendFetch } from '@/lib/image-api-client';

// Signature: imageBackendFetch(path, options = {})
// Returns: { ok: boolean, status: number, data: object|null }
// Auth: X-API-Key header added automatically
// Default: Content-Type: application/json
// Error: Returns { ok: false, status: 502, data: { error: { code: 'IMAGE_BACKEND_UNAVAILABLE', ... } } }
```

### Existing BFF Pattern Reference (Compact Style)
```javascript
// From: src/app/api/catalog/products/[productId]/status/route.js
// This is the compact proxy pattern used throughout the codebase
return NextResponse.json(
  data ?? { error: { code: 'SERVICE_UNAVAILABLE' } },
  { status: ok ? 200 : (status || 502) },
);
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `backendFetch` + JWT for media | `imageBackendFetch` + X-API-Key | Phase 3 (2026-03-30) | Media routes go directly to image_backend |
| Product-scoped media URLs `/catalog/products/{id}/media/...` | Top-level media URLs `/media/...` | Phase 4-5 (this phase) | Matches image_backend's actual API structure |
| `const { id } = params` (sync) | `const { id } = await params` (async) | Next.js 15+ | All route handlers must await params |

## Open Questions

1. **Should these routes require any auth check (e.g., user session)?**
   - What we know: The old broken routes checked JWT via `getAccessToken()`. The new routes use server-side `imageBackendFetch()` which handles X-API-Key. The image_backend trusts X-API-Key callers.
   - What's unclear: Should the BFF still verify the user is logged in before proxying? Without it, anyone who can reach the admin BFF can confirm/import media.
   - Recommendation: For consistency with the rest of the admin BFF and security, add a session check (getAccessToken). If no token, return 401. This is the pattern used in ALL other BFF routes. The token itself is NOT forwarded to image_backend -- it's only used to verify the caller is authenticated. **Decision: Follow existing codebase convention -- check getAccessToken before proxying.**

2. **Should old product-scoped routes be deleted now?**
   - What we know: Old routes at `catalog/products/[productId]/media/[mediaId]/confirm` and `catalog/products/[productId]/media/external` exist but are broken (they proxy to main backend which doesn't have these endpoints).
   - Recommendation: Leave them for now. Phase 6 will update frontend service calls to use the new routes. Old routes can be cleaned up then or in a later cleanup phase.

## Sources

### Primary (HIGH confidence)
- `image_backend/src/modules/storage/presentation/router.py` -- actual endpoint implementations, path params, status codes
- `image_backend/src/modules/storage/presentation/schemas.py` -- request/response schemas with CamelModel
- `frontend/admin/src/lib/image-api-client.js` -- imageBackendFetch() utility (Phase 3 output)
- `frontend/admin/src/app/api/catalog/products/[productId]/media/[mediaId]/confirm/route.js` -- existing broken confirm route (pattern reference)
- `frontend/admin/src/app/api/catalog/products/[productId]/media/external/route.js` -- existing broken external route (pattern reference)
- `image_backend/src/bootstrap/web.py` + `src/api/router.py` -- confirms API_V1_STR = "/api/v1" and media prefix
- `frontend/admin/src/services/products.js` -- current frontend service calls (Phase 6 will update these)

### Secondary (MEDIUM confidence)
- `audit.md` -- original problem identification, confirms main backend lacks media endpoints

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all dependencies already exist in the project
- Architecture: HIGH -- exact pattern established by existing BFF routes and Phase 3 output
- Pitfalls: HIGH -- based on direct codebase analysis and Next.js 16 known behavior

**Research date:** 2026-03-30
**Valid until:** 2026-04-30 (stable infrastructure, no external dependencies)
