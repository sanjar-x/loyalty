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

---

# Architecture Research: Backend Schema Fixes

**Domain:** ProductCreateRequest Pydantic schema issues
**Researched:** 2026-03-29

## Data Flow: description_i18n

### Layer-by-layer trace (HTTP request to DB)

1. **Presentation Layer** -- `schemas.py` line 729:
   ```python
   description_i18n: I18nDict = Field(default_factory=dict)
   ```
   `I18nDict` = `Annotated[dict[str, str], AfterValidator(_validate_i18n_keys)]`.
   The validator (`_validate_i18n_keys`) **requires** both `ru` and `en` keys.
   But `default_factory=dict` produces `{}`, which would **fail validation** if the field is omitted.
   **BUG:** The type says "validated i18n dict with required locales" but the default says "empty dict is fine". In practice, Pydantic runs the `AfterValidator` on the default, so submitting `{}` or omitting the field causes a 422 error: `"Missing required locales: en, ru"`. This means `description_i18n` is effectively **required** (must send both locales) despite the intent being optional.

2. **Presentation Layer** -- `router_products.py` lines 81-90:
   ```python
   command = CreateProductCommand(
       ...
       description_i18n=request.description_i18n,
       ...
   )
   ```
   Passes `request.description_i18n` directly (always a `dict[str, str]`).

3. **Application Layer** -- `create_product.py` line 52:
   ```python
   description_i18n: dict[str, str] = field(default_factory=dict)
   ```
   Command accepts `dict[str, str]`, defaults to `{}`. No validation here.

4. **Application Layer** -- `create_product.py` lines 145-147:
   ```python
   description_i18n=command.description_i18n if command.description_i18n else None,
   ```
   Handler passes it to entity, converting falsy `{}` to `None`.

5. **Domain Layer** -- `product.py` line 157 (`Product.create()`):
   ```python
   description_i18n: dict[str, str] | None = None,
   ```
   Accepts `None`. Line 193: `description_i18n=description_i18n or {},` -- stores `{}` if None.

6. **Infrastructure Layer** -- `repositories/product.py` line 293:
   ```python
   orm.description_i18n = entity.description_i18n
   ```
   Maps directly to ORM.

7. **Infrastructure Layer** -- `models.py` line 514-515:
   ```python
   description_i18n: Mapped[dict[str, Any]] = mapped_column(
       MutableDict.as_mutable(JSONB), server_default=text("'{}'::jsonb")
   )
   ```
   Stored as JSONB with `{}` default.

### The Problem

`description_i18n` SHOULD be optional on product creation. The downstream layers (command, entity, ORM) all handle `{}` gracefully. But the Pydantic schema uses `I18nDict` which mandates `ru` + `en` locales, making it effectively required. The fix is to either:
- **(A)** Change to `I18nDict | None = None` -- description is truly optional, not validated when absent.
- **(B)** Change to `dict[str, str] = Field(default_factory=dict)` -- drop validation, accept any dict.

**Recommended: Option (A)** -- This matches the `ProductUpdateRequest` pattern (line 760: `description_i18n: I18nDict | None = None`) and preserves i18n validation when a description IS provided.

## Data Flow: country_of_origin

### What exists at each layer

| Layer | File | Has `country_of_origin`? | Details |
|-------|------|--------------------------|---------|
| Presentation (create request) | `schemas.py` L717-735 `ProductCreateRequest` | **NO** | Field is completely absent |
| Presentation (update request) | `schemas.py` L764-765 `ProductUpdateRequest` | YES | `str \| None`, ISO 3166-1 alpha-2 pattern |
| Presentation (response) | `schemas.py` L913 `ProductResponse` | YES | `str \| None = None` |
| Presentation (router create) | `router_products.py` L81-90 | **NO** | Not passed to command |
| Application (create command) | `create_product.py` L55 | YES | `str \| None = None` |
| Application (create handler) | `create_product.py` L150 | YES | `country_of_origin=command.country_of_origin` |
| Domain (entity create) | `product.py` L160 | YES | `country_of_origin: str \| None = None` |
| Domain (entity attrs) | `product.py` L116 | YES | `country_of_origin: str \| None = None` |
| Domain (updatable fields) | `product.py` L219-228 | YES | In `_UPDATABLE_FIELDS` frozenset |
| Infrastructure (ORM) | `models.py` L518 | YES | `String(2)`, nullable |
| Infrastructure (repo to_orm) | `repositories/product.py` L282 | YES | `orm.country_of_origin = entity.country_of_origin` |
| Infrastructure (repo to_domain) | `repositories/product.py` L231 | YES | `"country_of_origin": orm.country_of_origin` |

### The Problem

The field exists at EVERY layer except the HTTP create endpoint. The `ProductCreateRequest` schema and the router's command construction both omit it. This means:
- You CAN read `country_of_origin` from the API (it's in `ProductResponse`)
- You CAN update it via PATCH (it's in `ProductUpdateRequest`)
- You CANNOT set it during product creation via POST
- The `CreateProductCommand` already accepts it but the router never passes it

## Change Map

### Fix 1: description_i18n in ProductCreateRequest

**Single file change:**

| File | Change |
|------|--------|
| `backend/src/modules/catalog/presentation/schemas.py` L729 | Change `description_i18n: I18nDict = Field(default_factory=dict)` to `description_i18n: I18nDict \| None = None` |

No other files need changes. The router passes the value as-is, the command accepts `dict[str, str]` with `default_factory=dict`, and the handler already converts falsy values to `None` (line 145-147).

### Fix 2: country_of_origin in ProductCreateRequest

**Two file changes:**

| File | Change |
|------|--------|
| `backend/src/modules/catalog/presentation/schemas.py` | Add `country_of_origin: str \| None = Field(None, min_length=2, max_length=2, pattern=r"^[A-Z]{2}$")` to `ProductCreateRequest` (copy exact validation from `ProductUpdateRequest` L764-765) |
| `backend/src/modules/catalog/presentation/router_products.py` L81-90 | Add `country_of_origin=request.country_of_origin,` to the `CreateProductCommand(...)` constructor call |

No other files need changes. The command, handler, entity, repository, and ORM model already support the field end-to-end.

## Migration Impact

**No Alembic migration needed for either fix.**

- Fix 1 (description_i18n): Pure Pydantic schema change. The DB column (`description_i18n JSONB`) is unchanged -- it already stores `{}` or any JSON dict.
- Fix 2 (country_of_origin): The `country_of_origin` column already exists on the `products` table (`String(2)`, nullable). We are only wiring the existing field through to the create endpoint.

## Key Findings

1. **description_i18n has a type/default contradiction**: `I18nDict` requires `{ru, en}` but `default_factory=dict` produces `{}`. The validator rejects the default. This makes the field deceptively required when the intent is optional. Downstream layers all handle empty/None gracefully.

2. **country_of_origin is 90% wired**: Every layer from command through ORM has the field. Only the presentation layer's create schema and router are missing it. This is a 2-line fix spread across 2 files.

3. **Update endpoint already has both fields correct**: `ProductUpdateRequest` has both `description_i18n: I18nDict | None = None` (line 760) and `country_of_origin` with proper ISO validation (lines 764-765). The create request should mirror these patterns.

4. **Router is the mapping boundary**: The router function (`create_product` in `router_products.py`) manually maps `ProductCreateRequest` fields to `CreateProductCommand` kwargs. There is no automatic field forwarding -- each field must be explicitly listed. This is why `country_of_origin` was silently dropped.

5. **Total files to modify**: 2 files, 3 line-level changes:
   - `backend/src/modules/catalog/presentation/schemas.py` -- 2 changes (fix description_i18n type, add country_of_origin field)
   - `backend/src/modules/catalog/presentation/router_products.py` -- 1 change (pass country_of_origin to command)
