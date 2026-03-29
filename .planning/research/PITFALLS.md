# Domain Pitfalls

**Domain:** Admin BFF media proxy to image_backend
**Researched:** 2026-03-29

## Critical Pitfalls

Mistakes that cause the media flow to break entirely.

### Pitfall 1: Sending productId to image_backend
**What goes wrong:** The BFF currently has URLs like `/api/v1/catalog/products/{productId}/media/upload`. Developers might proxy to image_backend preserving this path structure. image_backend has NO product concept -- its URLs are flat: `/api/v1/media/upload`, `/api/v1/media/{storageObjectId}/confirm`.
**Why it happens:** The admin frontend URL structure mirrors the main backend's product-scoped URLs, creating an assumption that upstream services also use product-scoped paths.
**Consequences:** 404 from image_backend. The entire upload flow fails.
**Prevention:** The BFF route handler explicitly constructs the image_backend URL without productId. Code review must verify this.
**Detection:** Any 404 from image_backend on upload/confirm/external endpoints.

### Pitfall 2: Using Bearer token instead of X-API-Key for image_backend
**What goes wrong:** Copy-pasting from existing BFF routes (which use `Authorization: Bearer ${token}`) sends a JWT to image_backend.
**Why it happens:** All existing routes use the same pattern: `getAccessToken()` then pass to `backendFetch` with Bearer header.
**Consequences:** image_backend ignores JWT (it checks `X-API-Key` header). If `INTERNAL_API_KEY` is set, all requests get 401 `INVALID_API_KEY`.
**Prevention:** `imageBackendFetch()` injects X-API-Key automatically. Route handlers call `imageBackendFetch`, not `backendFetch`.
**Detection:** 401 responses from image_backend with `INVALID_API_KEY` error code.

### Pitfall 3: Field name mismatch breaks S3 upload silently
**What goes wrong:** Frontend reads `slot.presignedUploadUrl` but image_backend returns `presignedUrl` (camelCase of `presigned_url`). Frontend reads `slot.id` but image_backend returns `storageObjectId`.
**Why it happens:** Frontend was written against a spec or mock, not the actual image_backend response.
**Consequences:** `uploadToS3(undefined, file)` -- fetch to `undefined` URL. Silent failure. User sees "upload failed" with no useful error.
**Prevention:** Fix field names in `services/products.js` to match image_backend's actual response schema (verified from `image_backend/src/modules/storage/presentation/schemas.py`).
**Detection:** `TypeError: Failed to construct 'Request': Invalid URL` in browser console.

## Moderate Pitfalls

### Pitfall 4: SSE buffering by reverse proxy (nginx/Railway)
**What goes wrong:** SSE events are buffered by nginx or Railway's reverse proxy, arriving in batches instead of real-time.
**Prevention:** Set `X-Accel-Buffering: no` header on SSE responses. Set `Cache-Control: no-cache, no-transform`. Add `runtime = 'nodejs'` and `dynamic = 'force-dynamic'` exports on the route handler.
**Detection:** Events arrive in bursts instead of individually. Processing appears to jump from 0% to 100%.

### Pitfall 5: Forgetting to strip product-specific fields from image_backend requests
**What goes wrong:** Frontend sends `{ contentType, filename, mediaType, role, sortOrder }` to the BFF upload route. If BFF forwards all fields to image_backend, the extra fields (`mediaType`, `role`, `sortOrder`) may cause a 422 Unprocessable Entity from Pydantic's strict validation (or be silently ignored, depending on model config).
**Why it happens:** Frontend bundles all media info into one request. image_backend only cares about storage concerns (`contentType`, `filename`). Product-level media info (`role`, `sortOrder`) is for the main backend.
**Prevention:** BFF route handler explicitly destructures only the fields image_backend needs before forwarding.

### Pitfall 6: Race condition between confirm and media registration
**What goes wrong:** Frontend calls `confirmMedia()` (image_backend) then immediately calls `POST /products/{id}/media` (main backend) with the `storageObjectId`. But image processing is still running -- the `url` and `image_variants` fields may be null.
**Why it happens:** The presigned URL flow is confirm -> async processing -> completed. Confirm returns 202, not 200. Processing takes 2-10 seconds.
**Prevention:** The current main backend `AddProductMediaCommand` does NOT check storage object status -- it just stores the `storageObjectId` reference. This is fine for now. But add processing status polling before displaying the image in the UI. Consider polling `GET /media/{id}` after confirm until status is `completed`.
**Detection:** Product media shows broken image URLs immediately after creation. URLs become valid after a few seconds.

### Pitfall 7: Missing auth check on SSE route
**What goes wrong:** The SSE status route is a GET request. If the developer forgets `getAccessToken()` check, anyone can monitor processing status by guessing UUIDs.
**Prevention:** Every BFF route, including GET SSE routes, MUST start with the JWT auth check. Add to code review checklist.

## Minor Pitfalls

### Pitfall 8: Not handling image_backend being down
**What goes wrong:** If image_backend is unreachable, `imageBackendFetch` throws a network error instead of returning a structured error response.
**Prevention:** Wrap fetch in try/catch. Return `{ ok: false, status: 502, data: { error: { code: 'IMAGE_SERVICE_UNAVAILABLE' } } }` on network failure. Match existing `backendFetch` pattern.

### Pitfall 9: EventSource reconnection loop
**What goes wrong:** If the SSE endpoint returns an error (e.g., 401, 404), `EventSource` in the browser auto-reconnects infinitely, hammering the server.
**Prevention:** On the `error` event, check `eventSource.readyState`. If `EventSource.CLOSED`, stop. Also, the BFF should return non-SSE error responses (JSON with proper status code) when auth fails, which will cause EventSource to fire `error` and close.

### Pitfall 10: Presigned URL expiration
**What goes wrong:** The presigned URL expires in 300 seconds (5 minutes). If the user's browser is slow or they switch tabs during upload, the PUT to S3 fails with 403.
**Prevention:** This is an existing edge case, not introduced by the BFF fix. The frontend could detect 403 from S3 and offer a "retry" by calling `/upload` again for a fresh presigned URL.

### Pitfall 11: S3 CORS not configured for browser direct upload
**What goes wrong:** The browser makes a cross-origin PUT request to S3 using the presigned URL. If S3/MinIO does not have CORS configured, the browser blocks the upload.
**Prevention:** Verify S3 CORS allows PUT from the admin frontend's origin. Include `Content-Type` in allowed headers. This is infrastructure config, not code.

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| BFF infrastructure (imageBackendFetch) | Auth model mismatch (Pitfall 2), missing env vars | Create separate client with X-API-Key. Add to Railway config. |
| JSON proxy routes | Sending productId to image_backend (Pitfall 1) | Explicit URL construction without productId |
| JSON proxy routes | Forwarding extra fields (Pitfall 5) | Destructure only needed fields |
| SSE route | Buffering (Pitfall 4), missing auth (Pitfall 7) | X-Accel-Buffering header + force-dynamic. Auth check first. |
| Frontend integration | Wrong field names (Pitfall 3) | Verify against image_backend schemas.py |
| Frontend integration | EventSource loop (Pitfall 9) | Check readyState on error event |

## Sources

- Codebase: `image_backend/src/modules/storage/presentation/router.py` -- actual endpoint URLs
- Codebase: `image_backend/src/modules/storage/presentation/schemas.py` -- actual response field names
- Codebase: `image_backend/src/api/dependencies/auth.py` -- X-API-Key auth mechanism
- Codebase: `frontend/admin/src/hooks/useSubmitProduct.js` -- current field name usage
- Codebase: `audit.md` -- documented field name mismatches
- [SSE in Next.js discussion](https://github.com/vercel/next.js/discussions/48427) -- SSE buffering issues
- [Fixing Slow SSE Streaming in Next.js](https://medium.com/@oyetoketoby80/fixing-slow-sse-server-sent-events-streaming-in-next-js-and-vercel-99f42fbdb996)
