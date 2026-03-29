# Technology Stack: BFF Media Proxy Integration

**Project:** Loyality -- Admin BFF media proxy to image_backend
**Researched:** 2026-03-29
**Overall confidence:** HIGH

## Problem Statement

The admin frontend (Next.js 16, JavaScript) currently proxies ALL requests through `backendFetch()` to the main backend. Three media operations (`/upload`, `/confirm`, `/external`) target endpoints that exist only on the `image_backend` microservice, not the main backend. The BFF must route these to `image_backend` directly, using `X-API-Key` server-to-server auth instead of the user's JWT Bearer token.

Additionally, `image_backend` exposes SSE at `GET /media/{id}/status` for processing status -- the frontend needs a way to consume this through the BFF.

## Recommended Stack

### Core Pattern: Dual-Client BFF

Use **Route Handlers** (the existing `route.js` pattern), not the new `proxy.js` convention. The project already has ~30 route handlers working this way, and the media proxy routes already exist as files (they just target the wrong service). Consistency wins.

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Next.js Route Handlers | 16.2.x (installed) | BFF proxy layer | Already used for all 30+ existing BFF routes. Proven pattern in this codebase. |
| `imageBackendFetch()` | New utility | HTTP client for image_backend | Mirrors existing `backendFetch()` but targets IMAGE_BACKEND_URL with X-API-Key auth |
| Web Streams API (ReadableStream) | Built-in | SSE proxy forwarding | Native to Node.js runtime in Next.js. No library needed. |
| EventSource (browser) | Built-in | Client SSE consumption | Standard browser API. No library needed for the frontend. |

### Environment Configuration

| Variable | Value | Where |
|----------|-------|-------|
| `IMAGE_BACKEND_URL` | `http://127.0.0.1:8001` (dev) | `frontend/admin/.env.local` |
| `IMAGE_BACKEND_API_KEY` | Same as image_backend's `INTERNAL_API_KEY` | `frontend/admin/.env.local` |

Both are **server-only** (no `NEXT_PUBLIC_` prefix) -- they never reach the browser.

## Architecture: imageBackendFetch()

### Why a Separate Client (Not Extending backendFetch)

1. **Different base URL** -- `BACKEND_URL` vs `IMAGE_BACKEND_URL`
2. **Different auth mechanism** -- JWT Bearer vs X-API-Key header
3. **Different Content-Type defaults** -- JSON for most, but SSE stream forwarding needs no Content-Type
4. **Clear separation of concerns** -- when reading a route handler, `imageBackendFetch` immediately signals "this goes to image_backend"

### Implementation Pattern

```javascript
// frontend/admin/src/lib/image-api-client.js

const IMAGE_BACKEND_URL = process.env.IMAGE_BACKEND_URL;
const IMAGE_BACKEND_API_KEY = process.env.IMAGE_BACKEND_API_KEY;

/**
 * Fetch helper for image_backend microservice.
 *
 * Unlike backendFetch() which uses JWT Bearer auth,
 * this uses X-API-Key for server-to-server auth.
 * The admin user's auth is verified at the BFF route level
 * via getAccessToken() -- imageBackendFetch handles the
 * service-to-service hop.
 */
export async function imageBackendFetch(path, options = {}) {
  const { headers = {}, ...rest } = options;

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
}

/**
 * Raw fetch for image_backend -- returns the Response object directly.
 * Used for SSE stream forwarding where we need the raw stream body.
 */
export async function imageBackendRawFetch(path, options = {}) {
  const { headers = {}, ...rest } = options;

  return fetch(`${IMAGE_BACKEND_URL}${path}`, {
    ...rest,
    headers: {
      'X-API-Key': IMAGE_BACKEND_API_KEY,
      ...headers,
    },
  });
}
```

**Key design decision:** Two functions, not one. `imageBackendFetch` parses JSON (for upload/confirm/external). `imageBackendRawFetch` returns the raw `Response` (for SSE stream forwarding). Trying to make one function handle both adds needless complexity.

## Route Handler Patterns

### Pattern 1: JSON Proxy (upload, confirm, external)

The existing route handler files already exist at the correct paths. They just need to switch from `backendFetch()` to `imageBackendFetch()` and adjust the target URL path.

**Current (broken) -- routes to main backend:**
```javascript
// /api/catalog/products/[productId]/media/upload/route.js
import { backendFetch } from '@/lib/api-client';

const { ok, status, data } = await backendFetch(
  `/api/v1/catalog/products/${productId}/media/upload`,  // <-- does not exist on main backend
  { method: 'POST', headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify(body) },
);
```

**Fixed -- routes to image_backend:**
```javascript
// /api/catalog/products/[productId]/media/upload/route.js
import { imageBackendFetch } from '@/lib/image-api-client';

// Note: productId is NOT passed to image_backend -- it doesn't know about products.
// image_backend only deals with storage objects. The productId is used later when
// registering the media asset on the main backend.
const { ok, status, data } = await imageBackendFetch(
  '/api/v1/media/upload',
  { method: 'POST', body: JSON.stringify({ contentType: body.contentType, filename: body.filename }) },
);
```

**Critical insight:** The image_backend endpoints are NOT nested under products. The URL mapping is:

| Admin BFF Route | Targets | image_backend Endpoint |
|----------------|---------|----------------------|
| `POST /api/catalog/products/[productId]/media/upload` | image_backend | `POST /api/v1/media/upload` |
| `POST /api/catalog/products/[productId]/media/[mediaId]/confirm` | image_backend | `POST /api/v1/media/{storageObjectId}/confirm` |
| `POST /api/catalog/products/[productId]/media/external` | image_backend | `POST /api/v1/media/external` |
| `GET /api/catalog/products/[productId]/media/[mediaId]/status` | image_backend | `GET /api/v1/media/{storageObjectId}/status` |

The `productId` in the BFF URL is for frontend routing convenience only -- `image_backend` does not use it. The productId will be needed later when the frontend calls `POST /products/{id}/media` on the main backend to link the `storageObjectId` to the product.

### Pattern 2: SSE Stream Forwarding

For the processing status endpoint (`GET /media/{id}/status`), the BFF must forward the SSE stream from image_backend to the browser. This requires the raw `Response` with its `ReadableStream` body.

```javascript
// /api/catalog/products/[productId]/media/[mediaId]/status/route.js
import { NextResponse } from 'next/server';
import { imageBackendRawFetch } from '@/lib/image-api-client';
import { getAccessToken } from '@/lib/auth';

export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

export async function GET(request, { params }) {
  const token = await getAccessToken();
  if (!token) {
    return NextResponse.json({ error: { code: 'UNAUTHORIZED' } }, { status: 401 });
  }

  const { mediaId } = await params;

  const upstream = await imageBackendRawFetch(
    `/api/v1/media/${mediaId}/status`,
    { method: 'GET' },
  );

  if (!upstream.ok) {
    const data = await upstream.json().catch(() => null);
    return NextResponse.json(
      data ?? { error: { code: 'SERVICE_UNAVAILABLE' } },
      { status: upstream.status || 502 },
    );
  }

  // Forward the SSE stream directly
  return new Response(upstream.body, {
    status: 200,
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache, no-transform',
      'Connection': 'keep-alive',
      'X-Accel-Buffering': 'no',
    },
  });
}
```

**Why this works:**
- `upstream.body` is a `ReadableStream` -- we pass it directly to the new `Response`
- The SSE headers tell the browser and any reverse proxies to not buffer
- `X-Accel-Buffering: no` prevents nginx from buffering (production requirement)
- `dynamic = 'force-dynamic'` prevents Next.js from trying to cache this route
- `runtime = 'nodejs'` ensures we're in Node.js runtime (required for streaming)

**Why NOT `proxy.js` for this:**
- `proxy.js` is the new name for middleware -- it runs before route resolution, not as a route handler
- It cannot produce streaming responses in the same way
- The project has zero `proxy.js` usage; adding it for one endpoint adds a new concept for the team
- Route handlers are the documented pattern for SSE in Next.js 16

### Pattern 3: Auth Gate at BFF Level

Every media BFF route must verify the user's JWT token **before** forwarding to image_backend. The user-facing auth check happens at the BFF; the service-to-service auth (X-API-Key) is injected by `imageBackendFetch`.

```
Browser                      BFF (Next.js)                    image_backend
  |                              |                                 |
  |-- POST /api/.../upload ----->|                                 |
  |   (cookie: access_token)     |                                 |
  |                              |-- verify JWT (getAccessToken) ->|
  |                              |   (401 if invalid)              |
  |                              |                                 |
  |                              |-- POST /api/v1/media/upload --->|
  |                              |   (X-API-Key: server-secret)    |
  |                              |                                 |
  |                              |<-- 201 { storageObjectId, ... } |
  |<-- 201 (JSON) --------------|                                 |
```

This is the same pattern used by all existing BFF routes -- no architectural change needed.

## Client-Side: Presigned URL Flow

The presigned URL flow is already implemented correctly in `services/products.js`. The sequence:

1. `reserveMediaUpload()` -> BFF -> image_backend -> returns `{ storageObjectId, presignedUrl, expiresIn }`
2. `uploadToS3(presignedUrl, file)` -> **direct to S3** (browser -> S3, not through BFF)
3. `confirmMedia(productId, storageObjectId)` -> BFF -> image_backend -> starts processing

The only fix needed in `services/products.js` is the field name mapping (issue #2 from audit):

```javascript
// Current (broken):
const slot = await reserveMediaUpload(productId, { ... });
await uploadToS3(slot.presignedUploadUrl, image.file);  // wrong field name
await confirmMedia(productId, slot.id);                   // wrong field name

// Fixed:
const slot = await reserveMediaUpload(productId, { ... });
await uploadToS3(slot.presignedUrl, image.file);          // matches image_backend response
await confirmMedia(productId, slot.storageObjectId);       // matches image_backend response
```

## Client-Side: SSE Status Polling

For monitoring image processing status after `confirmMedia()`, add an SSE consumer:

```javascript
// In services/products.js or a new services/media.js

export function subscribeToMediaStatus(productId, storageObjectId, { onStatus, onError, onComplete }) {
  const url = `/api/catalog/products/${productId}/media/${storageObjectId}/status`;
  const eventSource = new EventSource(url);

  eventSource.addEventListener('status', (event) => {
    const data = JSON.parse(event.data);
    onStatus?.(data);

    if (data.status === 'completed' || data.status === 'failed') {
      eventSource.close();
      if (data.status === 'completed') onComplete?.(data);
      if (data.status === 'failed') onError?.(data);
    }
  });

  eventSource.addEventListener('error', (event) => {
    // EventSource auto-reconnects on network error.
    // Only close on permanent failures.
    if (eventSource.readyState === EventSource.CLOSED) {
      onError?.({ status: 'failed', error: 'Connection closed' });
    }
  });

  // Return close function for cleanup
  return () => eventSource.close();
}
```

**Why EventSource over fetch-based polling:**
- SSE is what image_backend already provides -- no polling interval to tune
- EventSource handles reconnection automatically
- Simpler code than a polling loop with setInterval
- Real-time updates instead of delayed polling

**Fallback strategy:** If SSE connection fails or is unavailable (some deployment environments kill long-lived connections), fall back to polling `GET /api/v1/media/{id}` every 2 seconds:

```javascript
export function pollMediaStatus(productId, storageObjectId, { onStatus, onError, onComplete }) {
  let stopped = false;

  async function poll() {
    while (!stopped) {
      try {
        const data = await api(`/api/catalog/products/${productId}/media/${storageObjectId}`);
        onStatus?.(data);

        if (data.status === 'completed') { onComplete?.(data); return; }
        if (data.status === 'failed') { onError?.(data); return; }
      } catch (err) {
        onError?.({ status: 'failed', error: err.message });
        return;
      }
      await new Promise(r => setTimeout(r, 2000));
    }
  }

  poll();
  return () => { stopped = true; };
}
```

## File Structure Summary

```
frontend/admin/
  .env.local                                        # Add IMAGE_BACKEND_URL, IMAGE_BACKEND_API_KEY
  .env.local.example                                # Add IMAGE_BACKEND_URL template
  src/
    lib/
      api-client.js                                 # Existing -- no changes needed
      image-api-client.js                           # NEW: imageBackendFetch, imageBackendRawFetch
      auth.js                                       # Existing -- no changes needed
    services/
      products.js                                   # FIX: field name mapping (presignedUrl, storageObjectId)
    app/api/catalog/products/[productId]/media/
      upload/route.js                               # FIX: switch to imageBackendFetch, fix URL path
      external/route.js                             # FIX: switch to imageBackendFetch, fix URL path
      [mediaId]/
        confirm/route.js                            # FIX: switch to imageBackendFetch, fix URL path
        status/route.js                             # NEW: SSE stream forwarding from image_backend
```

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| BFF pattern | Route Handlers | `proxy.js` (new middleware) | Project has 30+ route handlers, zero proxy.js. Don't introduce a new concept for 4 routes. |
| Image client | Separate `imageBackendFetch()` | Extend `backendFetch()` with target param | Different auth, different base URL, different response handling (SSE). Mixing concerns. |
| SSE forwarding | Raw stream passthrough | Parse and re-emit SSE | Unnecessary overhead. The stream format is already correct. Just pipe it. |
| Status polling | SSE (primary) + polling (fallback) | Polling only | SSE already exists in image_backend. Using it is simpler and real-time. Polling as fallback for edge cases. |
| New library | None | `eventsource` npm package | Browser EventSource API is sufficient. No polyfill needed for admin panel (desktop browsers only). |
| Auth at BFF | JWT check then X-API-Key forward | Pass user JWT to image_backend | image_backend uses X-API-Key, not JWT. This is a deliberate service-to-service boundary. |

## Important Caveats

### 1. No New Dependencies Required

Everything uses built-in APIs:
- `fetch` (Node.js built-in in Next.js 16)
- `ReadableStream` (Web Streams API, built-in)
- `EventSource` (browser built-in)
- `Response` (Web API, built-in)

### 2. image_backend API Key Auth Supports Query Params for SSE

The `verify_api_key` dependency in image_backend accepts the API key via `X-API-Key` header OR `api_key` query parameter. This is explicitly designed for SSE, where `EventSource` cannot set custom headers. However, since the BFF (server-side) makes the request with `fetch`, it CAN set headers. The query param fallback is for browser-direct SSE (not our pattern).

### 3. Railway Deployment

Both backends are deployed on Railway. The `IMAGE_BACKEND_URL` in production will be an internal Railway service URL (private networking), not a public URL. This is more secure and faster than going through a public endpoint.

### 4. Request Body Transformation

The BFF routes may need to transform request bodies between what the frontend sends and what image_backend expects. For example, the frontend sends `contentType` (camelCase from CamelModel convention) and image_backend expects `contentType` (also camelCase -- CamelModel used there too). In this case, no transformation is needed because both use CamelModel.

However, the frontend currently sends fields that image_backend does not expect (like `mediaType`, `role`, `sortOrder`). These are main-backend-only fields for the product media asset. The BFF should strip them before forwarding to image_backend, and potentially use them later when registering the media on the main backend.

## Sources

- [Next.js 16 Route Handlers -- Official Docs](https://nextjs.org/docs/app/getting-started/route-handlers) (v16.2.1, 2026-03-25) -- HIGH confidence
- [Next.js BFF Guide -- Official Docs](https://nextjs.org/docs/app/guides/backend-for-frontend) (v16.2.1, 2026-03-25) -- HIGH confidence
- [Next.js proxy.js Convention -- Official Docs](https://nextjs.org/docs/app/getting-started/proxy) (v16.2.1, 2026-03-25) -- HIGH confidence
- [Next.js route.js API Reference](https://nextjs.org/docs/app/api-reference/file-conventions/route) (v16.2.1, 2026-03-25) -- HIGH confidence
- [SSE in Next.js Discussion](https://github.com/vercel/next.js/discussions/48427) -- MEDIUM confidence (community)
- Codebase analysis: `frontend/admin/src/lib/api-client.js`, `image_backend/src/modules/storage/presentation/router.py`, `image_backend/src/api/dependencies/auth.py` -- HIGH confidence (primary source)
