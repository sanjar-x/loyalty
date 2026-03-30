# Phase 3: BFF Media Proxy Infrastructure - Research

**Researched:** 2026-03-30
**Domain:** Next.js Route Handlers, server-side HTTP client utility, service-to-service auth
**Confidence:** HIGH

## Summary

Phase 3 creates a foundational `imageBackendFetch()` utility in the admin frontend's BFF layer. Currently, all BFF proxy routes use `backendFetch()` from `@/lib/api-client.js`, which targets the main backend (`BACKEND_URL`) and uses JWT Bearer auth. The media routes (upload, confirm, external) incorrectly proxy through the main backend, which does not have these endpoints -- resulting in 404 errors.

The fix is straightforward: create a parallel utility `imageBackendFetch()` that targets `IMAGE_BACKEND_URL` with `X-API-Key` auth header instead of JWT Bearer. This utility follows the exact same pattern as `backendFetch()` (which is only 17 lines), making it a minimal, well-scoped change. Two new server-only environment variables (`IMAGE_BACKEND_URL` and `IMAGE_BACKEND_API_KEY`) must be configured.

**Primary recommendation:** Create `frontend/admin/src/lib/image-api-client.js` with `imageBackendFetch()` following the existing `backendFetch()` pattern, plus add the two env vars to `.env.local.example`. Do not modify existing BFF routes in this phase -- that is Phase 4 and 5 work.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
None explicitly locked -- all implementation choices at Claude's discretion per CONTEXT.md.

Key constraints from ROADMAP (treated as locked):
- Auth: X-API-Key header (NOT JWT Bearer) targeting IMAGE_BACKEND_URL
- Error handling: structured error (502) when image_backend unreachable
- Env vars: IMAGE_BACKEND_URL and IMAGE_BACKEND_API_KEY as server-only (not NEXT_PUBLIC_)

### Claude's Discretion
All implementation choices are at Claude's discretion -- pure infrastructure phase. Use ROADMAP phase goal, success criteria, and codebase conventions to guide decisions.

### Deferred Ideas (OUT OF SCOPE)
None -- discuss phase skipped.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID     | Description                                                                               | Research Support                                                                                                                                                 |
| ------ | ----------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| BFF-01 | Admin BFF has imageBackendFetch() utility targeting IMAGE_BACKEND_URL with X-API-Key auth | Existing `backendFetch()` pattern documented; image_backend auth mechanism verified (X-API-Key header, hmac.compare_digest); env var naming convention confirmed |
</phase_requirements>

## Standard Stack

### Core
| Library     | Version   | Purpose                                      | Why Standard                                           |
| ----------- | --------- | -------------------------------------------- | ------------------------------------------------------ |
| Next.js     | 16.2.0    | App Router with Route Handlers for BFF proxy | Already installed and used for all existing BFF routes |
| next/server | (bundled) | `NextResponse` for structured JSON responses | Used in every existing route handler                   |

### Supporting
No additional libraries needed. The native `fetch` API (available in Node.js 18+, which Next.js 16 requires) is used by the existing `backendFetch()` and should be used for `imageBackendFetch()` as well.

**Installation:**
```bash
# No new packages needed
```

## Architecture Patterns

### Recommended Project Structure
```
frontend/admin/src/
  lib/
    api-client.js          # Existing: backendFetch() -> BACKEND_URL with JWT
    image-api-client.js    # NEW: imageBackendFetch() -> IMAGE_BACKEND_URL with X-API-Key
    auth.js                # Existing: cookie-based token helpers
    ...
  app/
    api/
      media/               # Phase 4+5 will create routes here (NOT this phase)
      catalog/
        products/
          [productId]/
            media/          # Existing broken routes (Phase 4+5 will fix)
```

### Pattern 1: Server-Only Fetch Client
**What:** A utility function that wraps `fetch()` for a specific backend service, handling base URL, auth headers, and error normalization.
**When to use:** When the BFF needs to proxy requests to a backend service with specific auth requirements.
**Example:**
```javascript
// Source: existing backendFetch() in frontend/admin/src/lib/api-client.js
const BACKEND_URL = process.env.BACKEND_URL;

export async function backendFetch(path, options = {}) {
  const { headers = {}, ...rest } = options;

  const res = await fetch(`${BACKEND_URL}${path}`, {
    ...rest,
    headers: {
      'Content-Type': 'application/json',
      ...headers,
    },
  });

  const data = await res.json().catch(() => null);

  return { ok: res.ok, status: res.status, data };
}
```

### Pattern 2: imageBackendFetch() (New Utility)
**What:** Parallel fetch utility targeting image_backend with X-API-Key auth baked in.
**When to use:** When any BFF route handler needs to proxy a request to image_backend.
**Key differences from backendFetch():**
1. Targets `IMAGE_BACKEND_URL` instead of `BACKEND_URL`
2. Sends `X-API-Key` header (from `IMAGE_BACKEND_API_KEY` env var) instead of caller-provided `Authorization: Bearer`
3. Returns structured 502 error when image_backend is unreachable (fetch throws / non-JSON response)

**Example:**
```javascript
// NEW: frontend/admin/src/lib/image-api-client.js
const IMAGE_BACKEND_URL = process.env.IMAGE_BACKEND_URL;
const IMAGE_BACKEND_API_KEY = process.env.IMAGE_BACKEND_API_KEY;

export async function imageBackendFetch(path, options = {}) {
  const { headers = {}, ...rest } = options;

  let res;
  try {
    res = await fetch(`${IMAGE_BACKEND_URL}${path}`, {
      ...rest,
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': IMAGE_BACKEND_API_KEY,
        ...headers,
      },
    });
  } catch {
    // Network error — image_backend unreachable
    return {
      ok: false,
      status: 502,
      data: { error: { code: 'IMAGE_BACKEND_UNAVAILABLE', message: 'Image service unreachable', details: {} } },
    };
  }

  const data = await res.json().catch(() => null);

  return { ok: res.ok, status: res.status, data };
}
```

### Pattern 3: Environment Variable Convention
**What:** Server-only env vars (no `NEXT_PUBLIC_` prefix) read at module scope.
**When to use:** For secrets and service URLs that must never reach the browser.
**Example from existing code:**
```javascript
// Source: frontend/admin/src/lib/api-client.js line 1
const BACKEND_URL = process.env.BACKEND_URL;
```
This pattern reads the env var at module load time (top-level const). It works because these files are only imported in Route Handlers (server-side). The same pattern applies to `IMAGE_BACKEND_URL` and `IMAGE_BACKEND_API_KEY`.

### Anti-Patterns to Avoid
- **Prefixing with NEXT_PUBLIC_:** `IMAGE_BACKEND_API_KEY` is a secret. Using `NEXT_PUBLIC_` would expose it to the browser bundle. Never do this.
- **Merging into backendFetch():** Do not add image_backend logic to the existing `backendFetch()`. Keep them as separate utilities -- they target different services with different auth mechanisms.
- **Passing API key from route handler:** The API key should be baked into `imageBackendFetch()` itself, not passed by each caller. This matches how `backendFetch()` bakes in the base URL.
- **Creating route handlers in this phase:** Phase 3 is infrastructure only. The actual `/api/media/*` routes are Phase 4 and 5.

## Don't Hand-Roll

| Problem        | Don't Build                                | Use Instead                                          | Why                                                                             |
| -------------- | ------------------------------------------ | ---------------------------------------------------- | ------------------------------------------------------------------------------- |
| HTTP client    | Custom retry/timeout/connection-pool logic | Native `fetch()` with simple try/catch               | Matches existing `backendFetch()` pattern; no need for axios/got/undici wrapper |
| Error envelope | Custom error class hierarchy               | Plain object `{ error: { code, message, details } }` | Matches the uniform backend error envelope used throughout all BFF routes       |

**Key insight:** The existing `backendFetch()` is 17 lines of code. `imageBackendFetch()` should be similarly concise. The value is in correctness (right URL, right auth header, right error handling), not in sophistication.

## Common Pitfalls

### Pitfall 1: Forgetting try/catch on fetch()
**What goes wrong:** If `IMAGE_BACKEND_URL` is unreachable (network error, DNS failure, service down), `fetch()` throws an exception. Without try/catch, the Route Handler returns a 500 instead of a structured 502.
**Why it happens:** The existing `backendFetch()` does NOT have try/catch -- it lets the error bubble up. But `backendFetch()` targets a co-located backend on Railway, while image_backend may be a separate service.
**How to avoid:** Wrap the `fetch()` call in try/catch. On catch, return `{ ok: false, status: 502, data: { error: { ... } } }`.
**Warning signs:** During testing, if image_backend is not running locally, the route handler returns 500 with no body instead of 502 with structured error.

### Pitfall 2: Env var not available at runtime
**What goes wrong:** `IMAGE_BACKEND_URL` or `IMAGE_BACKEND_API_KEY` is `undefined` at runtime, causing requests to `undefined/api/v1/media/...`.
**Why it happens:** Env vars were added to `.env.local.example` but not to the actual `.env.local` file, or Railway deployment config was not updated.
**How to avoid:** Add the env vars to `.env.local.example` with clear comments. Optionally add a startup guard (console.warn if missing).
**Warning signs:** Requests to image_backend fail with `TypeError: Failed to parse URL`.

### Pitfall 3: Content-Type header for non-JSON requests
**What goes wrong:** `imageBackendFetch()` sets `Content-Type: application/json` by default, but in Phase 4 the upload route may need to forward without this header (or with a different one).
**Why it happens:** The default Content-Type is useful for JSON-bodied requests (upload, confirm, external all accept JSON), but future callers might pass non-JSON bodies.
**How to avoid:** Allow callers to override `Content-Type` via the `headers` option (the spread `...headers` pattern already supports this). If a caller passes `headers: { 'Content-Type': 'something-else' }`, it overrides the default.
**Warning signs:** 422 from image_backend because body parsing fails.

### Pitfall 4: image_backend auth mechanism mismatch
**What goes wrong:** Using `Authorization: Bearer <api_key>` instead of `X-API-Key: <api_key>`.
**Why it happens:** Confusion between JWT Bearer auth (main backend) and API key auth (image_backend).
**How to avoid:** The image_backend auth dependency explicitly checks `Header(None, alias="X-API-Key")`. The header name must be exactly `X-API-Key`.
**Warning signs:** 401 `INVALID_API_KEY` response from image_backend despite correct key value.

## Code Examples

Verified patterns from the actual codebase:

### Existing backendFetch() (reference for pattern)
```javascript
// Source: frontend/admin/src/lib/api-client.js (full file, 17 lines)
const BACKEND_URL = process.env.BACKEND_URL;

export async function backendFetch(path, options = {}) {
  const { headers = {}, ...rest } = options;

  const res = await fetch(`${BACKEND_URL}${path}`, {
    ...rest,
    headers: {
      'Content-Type': 'application/json',
      ...headers,
    },
  });

  const data = await res.json().catch(() => null);

  return { ok: res.ok, status: res.status, data };
}
```

### image_backend auth verification (what we must match)
```python
# Source: image_backend/src/api/dependencies/auth.py
async def verify_api_key(
    x_api_key: str | None = Header(None, alias="X-API-Key"),
    api_key: str | None = Query(None),
) -> None:
    key = x_api_key or api_key
    internal_key = settings.INTERNAL_API_KEY.get_secret_value()
    if not internal_key:
        return  # auth disabled in dev
    if not key or not hmac.compare_digest(key, internal_key):
        raise UnauthorizedError(
            message="Invalid API key.",
            error_code="INVALID_API_KEY",
        )
```

### image_backend API prefix (URL path to use)
```python
# Source: image_backend/src/api/router.py
router = APIRouter(dependencies=[Depends(verify_api_key)])
router.include_router(media_router, prefix="/media", tags=["Media"])

# Source: image_backend/src/bootstrap/config.py
API_V1_STR: str = "/api/v1"

# Full URL pattern: {IMAGE_BACKEND_URL}/api/v1/media/{endpoint}
```

### Existing .env.local.example
```
# Source: frontend/admin/.env.local.example
BACKEND_URL=http://127.0.0.1:8000
```

### How BFF route handlers consume the fetch utility
```javascript
// Source: frontend/admin/src/app/api/catalog/products/[productId]/media/upload/route.js
// Currently BROKEN: uses backendFetch() targeting main backend
// Phase 4 will change this to use imageBackendFetch() from the new module
import { backendFetch } from '@/lib/api-client';

const { ok, status, data } = await backendFetch(
  `/api/v1/catalog/products/${productId}/media/upload`,
  { method: 'POST', headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify(body) },
);
```

## State of the Art

| Old Approach                              | Current Approach                                        | When Changed | Impact                                                     |
| ----------------------------------------- | ------------------------------------------------------- | ------------ | ---------------------------------------------------------- |
| All BFF routes proxy through main backend | Media routes should proxy directly to image_backend     | This phase   | Eliminates the 404 errors from missing main backend routes |
| Single `backendFetch()` utility           | Two utilities: `backendFetch()` + `imageBackendFetch()` | This phase   | Separate auth mechanisms for different backend services    |

**Current state of the three broken routes:**
- `POST /api/catalog/products/{id}/media/upload` -- uses `backendFetch()` which targets main backend (no such endpoint) -> 404
- `POST /api/catalog/products/{id}/media/{mid}/confirm` -- same issue -> 404
- `POST /api/catalog/products/{id}/media/external` -- same issue -> 404

## Open Questions

1. **Should imageBackendFetch() include a request timeout?**
   - What we know: The existing `backendFetch()` uses no explicit timeout (relies on Node.js/platform defaults). The image_backend `PROCESSING_TIMEOUT` is 300 seconds, but individual API responses should be much faster.
   - What's unclear: Whether Railway's proxy imposes its own timeout that makes this moot.
   - Recommendation: Do not add timeout in this phase. Match the existing `backendFetch()` pattern. Can be added later if needed.

2. **Should we validate env vars at startup?**
   - What we know: `backendFetch()` does not validate `BACKEND_URL` at startup. It silently fails with `TypeError` if undefined.
   - What's unclear: Whether adding startup validation is within phase scope.
   - Recommendation: Add a `console.warn` at module load time if `IMAGE_BACKEND_URL` is falsy. This is cheap and prevents confusing errors. But do not throw -- match existing patterns.

## Sources

### Primary (HIGH confidence)
- `frontend/admin/src/lib/api-client.js` -- existing backendFetch() pattern (17 lines, fully read)
- `image_backend/src/api/dependencies/auth.py` -- X-API-Key auth mechanism (hmac.compare_digest)
- `image_backend/src/api/router.py` -- API prefix `/api/v1` with `/media` sub-prefix
- `image_backend/src/modules/storage/presentation/schemas.py` -- all request/response schemas with CamelModel
- `image_backend/src/bootstrap/config.py` -- `INTERNAL_API_KEY: SecretStr = SecretStr("")`
- `frontend/admin/.env.local.example` -- existing env var convention
- `frontend/admin/next.config.js` -- no env var forwarding or exposure config
- `audit.md` -- documents the 3 broken media routes (audit items #1, #2, #3)

### Secondary (MEDIUM confidence)
- `frontend/admin/src/services/products.js` -- client-side service layer calling BFF routes (shows the contract Phase 4+5 must satisfy)
- `backend/src/modules/catalog/infrastructure/image_backend_client.py` -- server-to-server pattern reference (uses httpx, X-API-Key header)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new libraries, purely follows existing patterns
- Architecture: HIGH -- one new file mirroring an existing 17-line file, plus env vars
- Pitfalls: HIGH -- all verified against actual codebase code

**Research date:** 2026-03-30
**Valid until:** 2026-04-30 (stable infrastructure, no external dependency version concerns)
