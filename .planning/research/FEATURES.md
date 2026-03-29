# Feature Landscape: Product Creation Flow Integration Fix

**Domain:** Integration contract alignment (Backend / Admin Frontend / Image Backend)
**Researched:** 2026-03-29
**Mode:** Ecosystem (focused on Pydantic i18n aliasing, optional I18nDict, BFF transformation)

---

## Table of Contents

1. [Fix 1: I18n Field Naming (to_camel + _i18n suffix)](#fix-1-i18n-field-naming)
2. [Fix 2: Optional I18nDict Fields](#fix-2-optional-i18ndict-fields)
3. [Fix 3: Missing countryOfOrigin in ProductCreateRequest](#fix-3-missing-countryoforigin)
4. [Fix 4: BFF Request/Response Transformation for Media](#fix-4-bff-media-transformation)
5. [Fix 5: Frontend i18n Locale Enforcement](#fix-5-frontend-i18n-locale-enforcement)
6. [Feature Dependencies](#feature-dependencies)
7. [Anti-Features](#anti-features)

---

## Fix 1: I18n Field Naming

**Severity:** Critical (audit #2, #5, #14)
**Confidence:** HIGH (verified with live Pydantic code)

### Root Cause (Verified)

`pydantic.alias_generators.to_camel` uses Python's `.title()` method internally, which treats digits as word boundaries. The transformation chain for `title_i18n`:

```
title_i18n
  -> .title() -> "Title_I18N"     # .title() capitalizes after every non-alpha char
  -> regex    -> "TitleI18N"       # removes underscore before uppercase/digit
  -> lower()  -> "titleI18N"       # lowercases first char
```

The `N` at the end gets uppercased because `.title()` sees `8` (a digit) as a word boundary, so `n` becomes `N`. This produces `titleI18N`, not `titleI18n`.

**Current behavior:** Backend serializes i18n fields as `titleI18N`, `nameI18N`, `descriptionI18N` (uppercase N).

**What populate_by_name=True gives us:** The backend accepts BOTH `title_i18n` (Python name) AND `titleI18N` (generated alias) on input. But it does NOT accept `titleI18n` (lowercase n). Verified:

```python
TestSchema(titleI18N={"ru": "a"})  # OK
TestSchema(title_i18n={"ru": "a"})  # OK (populate_by_name)
TestSchema(titleI18n={"ru": "a"})   # REJECTED - field required
```

### Decision Required: Which Convention to Adopt?

**Option A: Keep `I18N` (current), update spec + frontend/main** -- RECOMMENDED

Rationale:
- Admin frontend already uses `I18N` and works
- `I18N` is what Pydantic generates; fighting the framework creates maintenance burden
- Backend API is the source of truth; consumers adapt
- Only spec doc and frontend/main types need updating (frontend/main API is not connected anyway)

Changes needed:
- Update `product-creation-flow.md` spec note: `I18n` -> `I18N`
- Update `frontend/main/lib/types/catalog.ts`: `titleI18n` -> `titleI18N`
- No backend changes

**Option B: Change to `I18n` via custom alias generator**

Would require changing `CamelModel` to use a custom generator:

```python
import re
from pydantic.alias_generators import to_camel

def to_camel_i18n(snake: str) -> str:
    """to_camel with I18N -> I18n normalization."""
    result = to_camel(snake)
    return re.sub(r'I18N\b', 'I18n', result)

class CamelModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel_i18n)
```

Verified output: `titleI18n`, `nameI18n`, `descriptionI18n`, `groupNameI18n`.

Problems:
- **Breaking change** for admin frontend (already uses `I18N`)
- Requires coordinated deploy: backend + admin frontend simultaneously
- Custom generator diverges from Pydantic standard behavior

**Option C: Accept both on input, keep `I18N` on output (AliasChoices)**

For specific schemas that need backward compatibility, add `validation_alias`:

```python
from pydantic import AliasChoices, Field

class ProductCreateRequest(CamelModel):
    title_i18n: I18nDict = Field(
        ...,
        validation_alias=AliasChoices('titleI18n', 'titleI18N', 'title_i18n'),
    )
```

Verified output: accepts all three on input, serializes as `titleI18N`.

Problems:
- Adds per-field boilerplate to every i18n field across 40+ schemas
- Inconsistency: only some schemas would have this

### Recommendation

**Go with Option A.** The `I18N` convention is a fait accompli -- the backend already produces it, admin frontend already consumes it, and `populate_by_name=True` already lets API callers send `title_i18n` if they prefer snake_case. The only change is documentation and frontend/main types (which are out of scope per PROJECT.md).

No backend code changes needed for this fix.

---

## Fix 2: Optional I18nDict Fields

**Severity:** Major (audit #7)
**Confidence:** HIGH (verified with live code)

### Root Cause (Verified)

Three schemas use `I18nDict = Field(default_factory=dict)` for optional description fields:

| Schema | Line | Field |
|--------|------|-------|
| `AttributeCreateRequest` | 335 | `description_i18n` |
| `ProductCreateRequest` | 729 | `description_i18n` |
| `AttributeTemplateCreateRequest` | 1174 | `description_i18n` |

When the frontend omits the field, Pydantic uses `default_factory=dict` to produce `{}`, then runs the `I18nDict` validator (`_validate_i18n_keys`), which requires `{"ru", "en"}` keys. Empty dict `{}` fails with:

```
ValueError: Missing required locales: en, ru
```

**Result:** You cannot create a product without a description, even though the spec says description is optional.

### The Fix

Change the type from `I18nDict` to `I18nDict | None` with `None` default:

```python
# BEFORE (broken):
description_i18n: I18nDict = Field(default_factory=dict)

# AFTER (correct):
description_i18n: I18nDict | None = None
```

**Behavior:**
- Frontend omits field -> `None` -> no validation runs -> domain receives `None`
- Frontend sends `{"ru": "...", "en": "..."}` -> `I18nDict` validator runs -> validates both locales present
- Frontend sends `{}` -> `I18nDict` validator runs -> rejects (correct! partial locales are bad data)

**Domain layer is already compatible.** `Product.create()` accepts `description_i18n: dict[str, str] | None = None` and handles it with `description_i18n or {}` (line 193 of `product.py`).

**Handler is already compatible.** `CreateProductHandler` passes `command.description_i18n if command.description_i18n else None` (lines 145-147 of `create_product.py`).

**Command dataclass needs update** -- currently uses `default_factory=dict`, should be `None`:

```python
# create_product.py - CreateProductCommand
# BEFORE:
description_i18n: dict[str, str] = field(default_factory=dict)

# AFTER:
description_i18n: dict[str, str] | None = None
```

### All Affected Locations

| File | Class | Field | Current | Fix |
|------|-------|-------|---------|-----|
| `catalog/presentation/schemas.py:335` | `AttributeCreateRequest` | `description_i18n` | `I18nDict = Field(default_factory=dict)` | `I18nDict \| None = None` |
| `catalog/presentation/schemas.py:729` | `ProductCreateRequest` | `description_i18n` | `I18nDict = Field(default_factory=dict)` | `I18nDict \| None = None` |
| `catalog/presentation/schemas.py:1174` | `AttributeTemplateCreateRequest` | `description_i18n` | `I18nDict \| None = Field(default_factory=dict)` | `I18nDict \| None = None` |
| `catalog/application/commands/create_product.py:52` | `CreateProductCommand` | `description_i18n` | `dict[str, str] = field(default_factory=dict)` | `dict[str, str] \| None = None` |
| `catalog/application/commands/create_attribute.py:63` | `CreateAttributeCommand` | `description_i18n` | `dict[str, str] = field(default_factory=dict)` | `dict[str, str] \| None = None` |
| `catalog/application/commands/bulk_create_attributes.py:51` | `BulkCreateAttributeItem` | `description_i18n` | `dict[str, str] = field(default_factory=dict)` | `dict[str, str] \| None = None` |

### Semantic: "Not provided" vs "Empty"

The fix distinguishes three states:
1. **Not provided** (`None`) -- no description yet, valid for draft products
2. **Provided with both locales** (`{"ru": "...", "en": "..."}`) -- validated, stored as-is
3. **Provided with partial locales** (`{"ru": "..."}`) -- rejected by validator (correct)

The existing `CategoryUpdateRequest` and `ProductVariantCreateRequest` already use `I18nDict | None = None` correctly. This fix aligns the create requests with the same pattern.

---

## Fix 3: Missing countryOfOrigin in ProductCreateRequest

**Severity:** Major (audit #8)
**Confidence:** HIGH (verified by reading code)

### Root Cause

The admin frontend (`useProductForm.js:340`) sends `countryOfOrigin` in the product creation payload:

```javascript
...(state.countryOfOrigin ? { countryOfOrigin: state.countryOfOrigin } : {}),
```

But `ProductCreateRequest` does not include this field. Pydantic silently discards unknown fields (default behavior -- no `model_config = ConfigDict(extra='forbid')`).

Meanwhile:
- `CreateProductCommand` already has `country_of_origin: str | None = None` (line 55)
- `Product.create()` already accepts `country_of_origin: str | None = None` (line 160)
- The router (`router_products.py:81-89`) does NOT pass it to the command
- `ProductUpdateRequest` already has `country_of_origin` (line 764)
- The DB column `products.country_of_origin VARCHAR(2)` exists

### The Fix

Two changes:

**1. Add field to `ProductCreateRequest`:**

```python
class ProductCreateRequest(CamelModel):
    # ... existing fields ...
    country_of_origin: str | None = Field(
        None, min_length=2, max_length=2, pattern=r"^[A-Z]{2}$"
    )
```

Validation pattern matches `ProductUpdateRequest` (line 764-766).

**2. Pass it in the router:**

```python
# router_products.py create_product()
command = CreateProductCommand(
    title_i18n=request.title_i18n,
    slug=request.slug,
    brand_id=request.brand_id,
    primary_category_id=request.primary_category_id,
    description_i18n=request.description_i18n,
    supplier_id=request.supplier_id,
    source_url=request.source_url,
    country_of_origin=request.country_of_origin,  # ADD THIS
    tags=request.tags,
)
```

No domain or command changes needed -- both already support it.

---

## Fix 4: BFF Request/Response Transformation for Media

**Severity:** Critical (audit #1, #2, #3)
**Confidence:** HIGH (verified by reading all three layers)

### Problem Summary

The admin frontend calls three media routes that proxy through the Next.js BFF to `BACKEND_URL`, but these routes do not exist on the main backend -- they exist on the image_backend:

| Frontend calls | BFF proxies to | Exists? |
|---|---|---|
| `POST /api/catalog/products/{id}/media/upload` | `BACKEND_URL/api/v1/catalog/products/{id}/media/upload` | NO |
| `POST /api/catalog/products/{id}/media/{mid}/confirm` | `BACKEND_URL/api/v1/catalog/products/{id}/media/{mid}/confirm` | NO |
| `POST /api/catalog/products/{id}/media/external` | `BACKEND_URL/api/v1/catalog/products/{id}/media/external` | NO |

Image backend has:
- `POST /api/v1/media/upload` -- accepts `{contentType, filename}`
- `POST /api/v1/media/{storageObjectId}/confirm` -- no body
- `POST /api/v1/media/external` -- accepts `{url}`

Additionally, there are two layers of mismatches:

**Request shape mismatch:**

```
Frontend sends:              Image backend expects:
{                            {
  mediaType: "image",          contentType: "image/jpeg",
  role: "main",                filename: "photo.jpg"   (optional)
  contentType: "image/jpeg", }
  sortOrder: 0
}
```

`mediaType`, `role`, `sortOrder` are catalog concepts that belong to the main backend's `POST /products/{id}/media` endpoint, not the image backend.

**Response shape mismatch:**

```
Frontend expects:            Image backend returns:
{                            {
  presignedUploadUrl: "...",   presignedUrl: "...",       (different name)
  id: "uuid"                   storageObjectId: "uuid"    (different name)
}                              expiresIn: 300
                             }
```

### The Fix: BFF as Shape-Shifting Proxy

The BFF routes must:
1. Route to `IMAGE_BACKEND_URL` (not `BACKEND_URL`)
2. Transform the request shape (extract what image_backend needs, preserve what catalog needs)
3. Transform the response shape (map image_backend fields to what frontend expects)
4. Use `X-API-Key` auth (not JWT Bearer) for image_backend calls

**Pattern: `imageBackendFetch()` utility**

Create a new fetch utility alongside the existing `backendFetch()`:

```javascript
// frontend/admin/src/lib/image-api-client.js
const IMAGE_BACKEND_URL = process.env.IMAGE_BACKEND_URL;
const IMAGE_BACKEND_API_KEY = process.env.IMAGE_BACKEND_API_KEY;

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
```

**Upload route transformation:**

```javascript
// frontend/admin/src/app/api/catalog/products/[productId]/media/upload/route.js
export async function POST(request, { params }) {
  const token = await getAccessToken();
  if (!token) return NextResponse.json({ error: { code: 'UNAUTHORIZED' } }, { status: 401 });

  const body = await request.json();

  // 1. Call image_backend with only what it needs
  const { ok, status, data } = await imageBackendFetch(
    '/api/v1/media/upload',
    {
      method: 'POST',
      body: JSON.stringify({
        contentType: body.contentType,
        filename: body.filename || null,
      }),
    },
  );

  if (!ok) return NextResponse.json(data, { status });

  // 2. Transform response to what frontend expects
  return NextResponse.json({
    id: data.storageObjectId,              // map storageObjectId -> id
    presignedUploadUrl: data.presignedUrl, // map presignedUrl -> presignedUploadUrl
    expiresIn: data.expiresIn,
  }, { status: 201 });
}
```

**Confirm route transformation:**

```javascript
// The confirm route: frontend passes storageObjectId as mediaId in the URL
// POST /api/catalog/products/{productId}/media/{mediaId}/confirm
export async function POST(request, { params }) {
  const token = await getAccessToken();
  if (!token) return NextResponse.json({ error: { code: 'UNAUTHORIZED' } }, { status: 401 });

  const { mediaId } = await params;

  const { ok, status, data } = await imageBackendFetch(
    `/api/v1/media/${mediaId}/confirm`,
    { method: 'POST' },
  );

  if (!ok) return NextResponse.json(data, { status });
  return NextResponse.json(data, { status: 202 });
}
```

**External import route transformation:**

```javascript
// Frontend sends: { externalUrl, mediaType, role, sortOrder }
// Image backend expects: { url }
export async function POST(request, { params }) {
  const token = await getAccessToken();
  if (!token) return NextResponse.json({ error: { code: 'UNAUTHORIZED' } }, { status: 401 });

  const body = await request.json();

  const { ok, status, data } = await imageBackendFetch(
    '/api/v1/media/external',
    {
      method: 'POST',
      body: JSON.stringify({ url: body.externalUrl }),
    },
  );

  if (!ok) return NextResponse.json(data, { status });

  // Transform response
  return NextResponse.json({
    id: data.storageObjectId,
    url: data.url,
    variants: data.variants,
  }, { status: 201 });
}
```

### Post-Upload Flow: Linking to Product

After the BFF returns `storageObjectId` (as `id`) to the frontend, the submit flow must call the main backend's existing `POST /products/{id}/media` to create the `MediaAsset` record. This endpoint already exists and works.

The current `useSubmitProduct.js` does NOT do this linking step -- it only calls upload/confirm but never creates the `MediaAsset` catalog record. This is a separate fix needed in the submit hook:

```javascript
// After confirmMedia, add:
await addMediaToProduct(productId, {
  storageObjectId: slot.id,
  variantId: variantId,
  mediaType: 'image',
  role: role,
  sortOrder: sortOrder,
});
```

### Environment Variables Needed

The admin frontend `.env` needs:
```
IMAGE_BACKEND_URL=http://localhost:8001
IMAGE_BACKEND_API_KEY=<internal-api-key>
```

---

## Fix 5: Frontend i18n Locale Enforcement

**Severity:** Critical (audit #4)
**Confidence:** HIGH (verified by reading frontend code)

### Root Cause

`useProductForm.js` conditionally includes the `en` locale:

```javascript
titleI18N: {
  ru: state.titleRu,
  ...(state.titleEn ? { en: state.titleEn } : {}),  // en omitted if empty!
},
```

Backend `I18nDict` validator requires both `ru` and `en` keys. If user leaves English title empty, backend returns 422.

### The Fix

Always include both locales. Use the Russian value as fallback for empty English:

```javascript
titleI18N: {
  ru: state.titleRu,
  en: state.titleEn || state.titleRu,  // fallback to Russian
},
```

**Note:** The `I18nDict` validator (`_validate_i18n_keys`) checks key presence but does NOT check for empty string values. So `{"ru": "test", "en": ""}` would pass validation. However, an empty `en` value is semantically dubious -- the Russian fallback approach is better UX.

Same fix needed for `descriptionI18N` (lines 332-334):

```javascript
descriptionI18N: {
  ru: state.descriptionRu,
  en: state.descriptionEn || state.descriptionRu,
},
```

And the conditional wrapping around `descriptionI18N` (lines 330-337) must also always include both locales when the field is sent.

---

## Feature Dependencies

```
Fix 2 (optional I18nDict) ---- independent ---- backend only
Fix 3 (countryOfOrigin)   ---- independent ---- backend only
Fix 5 (locale enforcement) --- independent ---- frontend only

Fix 4 (BFF media proxy) depends on:
  1. imageBackendFetch() utility (new file)
  2. Rewrite 3 BFF route handlers
  3. IMAGE_BACKEND_URL + IMAGE_BACKEND_API_KEY in admin .env
  4. Add product media linking step in useSubmitProduct.js
```

**Deployment order:**
1. **Fix 2 + Fix 3** first (backend-only, non-breaking, additive changes)
2. **Fix 5** second (frontend-only, independent of backend changes)
3. **Fix 4** last (requires BFF rewrite + frontend submit hook changes)
4. **Fix 1** is documentation-only (update spec, track for frontend/main later)

---

## Anti-Features

| Anti-Feature | Why Avoid | What to Do Instead |
|---|---|---|
| Custom alias generator changing `I18N` -> `I18n` | Breaking change to admin frontend, diverges from Pydantic standard behavior | Keep `I18N`, update spec and frontend/main types |
| Proxying media binary uploads through main backend | Main backend should not handle binary streams; adds latency and memory pressure | BFF proxies directly to image_backend for presigned URL only |
| Making `en` locale optional in I18nDict validator | Weakens data quality; translations become unreliable across the platform | Frontend always sends both locales (fallback to `ru` value) |
| Adding `AliasChoices` to every i18n field | Per-field boilerplate on 40+ fields across schemas; maintenance burden | Standardize on one convention (`I18N`) and have consumers adapt |
| Adding media upload/confirm/external routes to main backend | Violates SRP; main backend is catalog business logic, not file storage | BFF routes directly to image_backend for media ops |
| Direct browser-to-image_backend calls | Exposes internal API key to browser, bypasses auth | Always proxy through BFF (server-side only) |

---

## MVP Recommendation

**Minimum to unblock product creation E2E:**

1. Fix 2: `description_i18n` optional (backend, 6 locations, ~10 lines changed)
2. Fix 3: `country_of_origin` in create request (backend, 2 files, ~5 lines changed)
3. Fix 5: Always send both locales (frontend, 1 file, ~4 lines changed)
4. Fix 4: BFF media proxy rewrite (frontend, 4 files: 1 new utility + 3 route rewrites + submit hook update)

**Defer:**
- Fix 1 (spec doc update): cosmetic, no functional impact on working code
- Media status polling (audit #9): UX improvement, not a blocker (images process in <2s)
- Completeness endpoint UI (audit #11): nice-to-have, not blocking creation
- Full FSM UI (audit #12): only DRAFT->ENRICHING is needed for initial creation
- Version in PATCH (audit #13): no edit page exists yet

---

## Sources

- `backend/src/shared/schemas.py` -- CamelModel with `alias_generator=to_camel`
- `backend/src/modules/catalog/presentation/schemas.py` -- ProductCreateRequest, I18nDict validator
- `backend/src/modules/catalog/application/commands/create_product.py` -- CreateProductCommand
- `backend/src/modules/catalog/presentation/router_products.py` -- create_product endpoint
- `backend/src/modules/catalog/domain/entities/product.py` -- Product.create() factory
- `image_backend/src/modules/storage/presentation/schemas.py` -- UploadRequest/Response
- `image_backend/src/modules/storage/presentation/router.py` -- Actual image_backend endpoints
- `frontend/admin/src/hooks/useProductForm.js` -- Form state and payload construction
- `frontend/admin/src/hooks/useSubmitProduct.js` -- Submit orchestration
- `frontend/admin/src/services/products.js` -- API client functions
- `frontend/admin/src/app/api/catalog/products/[productId]/media/upload/route.js` -- Current BFF proxy (broken)
- `frontend/admin/src/app/api/catalog/products/[productId]/media/[mediaId]/confirm/route.js` -- Current BFF confirm (broken)
- `frontend/admin/src/app/api/catalog/products/[productId]/media/external/route.js` -- Current BFF external (broken)
- `frontend/admin/src/lib/api-client.js` -- backendFetch utility
- Pydantic `to_camel` source code (verified via `inspect.getsource` -- uses `.title()` then regex)
- Live verification: `to_camel("title_i18n")` -> `"titleI18N"` (uppercase N confirmed)
- Live verification: `populate_by_name=True` accepts `title_i18n` and `titleI18N` but rejects `titleI18n`
- Live verification: `AliasChoices('titleI18n', 'titleI18N', 'title_i18n')` accepts all three forms
- Live verification: `I18nDict` validator rejects empty dict `{}` with "Missing required locales: en, ru"
- `audit.md` -- Full integration audit (14 issues catalogued)
- `product-creation-flow.md` -- Product creation spec with media flow architecture
