# Architecture Patterns

**Domain:** Admin BFF media proxy to image_backend
**Researched:** 2026-03-29

## Current Architecture (Broken)

```
Browser                   Admin BFF (Next.js)           Main Backend         image_backend
  |                            |                            |                     |
  |-- POST .../media/upload -->|                            |                     |
  |   (JWT cookie)             |-- backendFetch() --------->|                     |
  |                            |   /api/v1/.../media/upload |                     |
  |                            |<-- 404 Not Found ----------|                     |
  |<-- 404 -------------------|                            |                     |
```

The main backend has media CRUD endpoints (add/list/update/delete/reorder) but NOT the upload lifecycle endpoints (presigned URL, confirm, external import). Those exist only on image_backend.

## Recommended Architecture (Fixed)

```
Browser (Admin Panel)
   |
   | Services layer (products.js)
   v
Next.js BFF (API Routes)
   |
   +--[catalog operations]--> backendFetch()  --> Main Backend (BACKEND_URL)
   |                                               POST /api/v1/catalog/products
   |                                               POST /api/v1/catalog/products/{id}/media  (attach)
   |                                               GET  /api/v1/catalog/products/{id}/completeness
   |                                               PATCH /api/v1/catalog/products/{id}/status
   |
   +--[media storage ops]--> imageBackendFetch() --> Image Backend (IMAGE_BACKEND_URL)
                                                      POST /api/v1/media/upload
                                                      POST /api/v1/media/{id}/confirm
                                                      POST /api/v1/media/external
                                                      GET  /api/v1/media/{id}        (metadata)
                                                      GET  /api/v1/media/{id}/status  (SSE)
```

### Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| Browser (admin panel) | UI, file selection, upload orchestration | BFF routes (via fetch/EventSource), S3 (via presigned URL) |
| BFF Route Handlers | Auth gate (JWT), request routing, response forwarding | Main backend (backendFetch), image_backend (imageBackendFetch) |
| `api-client.js` | HTTP client for main backend | Main backend only |
| `image-api-client.js` | HTTP client for image_backend (JSON + raw stream) | image_backend only |
| Main backend | Product CRUD, media asset linking, business rules | PostgreSQL, image_backend (for delete cleanup) |
| image_backend | File storage, image processing, presigned URLs, SSE | S3, PostgreSQL, Redis (pub/sub for SSE) |
| S3 | Binary file storage | Browser (presigned PUT), image_backend (processing) |

### Data Flow: Complete Upload Lifecycle

1. **Reserve** -- Browser -> BFF -> image_backend: creates storage record, returns presigned PUT URL
2. **Upload** -- Browser -> S3 (direct): uploads binary file using presigned URL
3. **Confirm** -- Browser -> BFF -> image_backend: verifies file in S3, starts background processing
4. **Monitor** -- Browser -> BFF -> image_backend (SSE or polling): streams/checks processing status
5. **Register** -- Browser -> BFF -> main backend: links storageObjectId to product as media asset

Steps 1-4 involve image_backend. Step 5 involves main backend. The BFF routes them correctly.

### Auth Flow

```
Browser --> [Cookie: access_token] --> BFF Route
  BFF verifies JWT cookie (existing getAccessToken())
  |
  +-- Catalog operations:
  |     BFF --> [Authorization: Bearer {jwt}] --> Main Backend
  |
  +-- Media storage operations:
        BFF --> [X-API-Key: {server_secret}] --> Image Backend
```

The BFF is the auth bridge: it trusts the admin user's JWT for authorization, then uses its own service-level API key to talk to image_backend.

## Patterns to Follow

### Pattern 1: Dual-Client BFF
**What:** Maintain two separate fetch utilities -- one per backend service.
**When:** Any BFF that talks to multiple microservices.
**Why:** Prevents auth confusion, makes routing explicit, simplifies debugging.

### Pattern 2: SSE Stream Passthrough
**What:** Forward upstream SSE stream as-is via `new Response(upstream.body, { headers })`.
**When:** BFF proxies a streaming endpoint from an upstream service.
**Why:** Zero transformation overhead, preserves event structure, no re-serialization.

```javascript
const upstream = await imageBackendRawFetch(`/api/v1/media/${id}/status`);
return new Response(upstream.body, {
  headers: {
    'Content-Type': 'text/event-stream',
    'Cache-Control': 'no-cache, no-transform',
    'X-Accel-Buffering': 'no',
  },
});
```

### Pattern 3: Auth Boundary Separation
**What:** Verify user identity at BFF, inject service credentials for upstream calls.
**When:** BFF proxies to a service that uses different auth than the user.
**Why:** Users never see or interact with service-to-service credentials.

### Pattern 4: Request Body Filtering
**What:** The BFF strips fields that the upstream service doesn't expect and may need later for a different service.
**When:** Frontend sends a superset of fields needed by multiple services.
**Why:** Prevents 422 errors from strict validation on upstream services.

```javascript
// Frontend sends: { contentType, filename, mediaType, role, sortOrder }
// image_backend expects only: { contentType, filename }
const { contentType, filename } = body;
const result = await imageBackendFetch('/api/v1/media/upload', {
  method: 'POST',
  body: JSON.stringify({ contentType, filename }),
});
```

## Anti-Patterns to Avoid

### Anti-Pattern 1: Catch-All Proxy Route
**What:** Using `[...slug]/route.js` to proxy all requests to image_backend.
**Why bad:** Loses explicit routing, makes it impossible to transform individual endpoints, obscures which routes go where.
**Instead:** Explicit route files per endpoint. The project already follows this pattern.

### Anti-Pattern 2: Passing User JWT to image_backend
**What:** Forwarding `Authorization: Bearer <token>` to image_backend.
**Why bad:** image_backend uses X-API-Key, not JWT. The JWT would be ignored at best, cause auth failure at worst.
**Instead:** BFF verifies JWT, then uses X-API-Key for the upstream call.

### Anti-Pattern 3: Binary Upload Through BFF
**What:** Having the browser upload the file to the BFF, then BFF uploads to S3 or image_backend.
**Why bad:** Doubles bandwidth usage, BFF becomes a bottleneck for large files (up to 50MB per config).
**Instead:** Use presigned URLs -- browser uploads directly to S3, BFF only handles the small JSON requests.

### Anti-Pattern 4: Parsing and Re-emitting SSE
**What:** Reading SSE events from upstream, parsing them, then creating new SSE events for the browser.
**Why bad:** Adds latency, complexity, and potential for data loss. The SSE format is already correct.
**Instead:** Pass the ReadableStream through unchanged.

## Scalability Considerations

| Concern | Current (dev) | Production | Notes |
|---------|---------------|------------|-------|
| SSE connections | Few concurrent | ~10-50 concurrent admin users | Each image upload creates one short-lived SSE connection (~5-30s). Not a scaling concern. |
| Upload throughput | Local S3 (MinIO) | S3-compatible cloud storage | Presigned URLs offload all binary traffic to S3. BFF handles only small JSON. |
| image_backend availability | Single instance | Single instance (Railway) | If image_backend is down, uploads fail gracefully (502 from BFF). No cascading failure. |
| BFF route handler concurrency | Unlimited (dev) | Railway container limits | Route handlers are stateless. Scales with container instances. |

## Sources

- Codebase: `frontend/admin/src/lib/api-client.js` -- current BFF client (single-backend)
- Codebase: `image_backend/src/modules/storage/presentation/router.py` -- actual image_backend endpoints
- Codebase: `image_backend/src/api/dependencies/auth.py` -- X-API-Key auth mechanism
- Codebase: `backend/src/modules/catalog/presentation/router_media.py` -- main backend media attachment endpoints
- [Next.js 16 BFF Guide](https://nextjs.org/docs/app/guides/backend-for-frontend)
- [Next.js 16 Route Handlers](https://nextjs.org/docs/app/api-reference/file-conventions/route)
