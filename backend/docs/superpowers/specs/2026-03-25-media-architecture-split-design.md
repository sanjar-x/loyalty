# Media Architecture Split: Backend + ImageBackend

**Date:** 2026-03-25
**Status:** Approved
**Approach:** Fire-and-Forget URL

---

## Overview

Decouple all image/file handling from Backend into a dedicated ImageBackend microservice. Backend stores only URLs and metadata — no S3, no presigned URLs, no processing status, no FSM. ImageBackend is a generic image service with zero business-domain knowledge.

---

## Architecture

```
┌─────────────┐       ┌──────────────┐       ┌───────────┐
│  Frontend   │──JWT──│ ImageBackend │──S3───│  Bucket   │
│  (Next.js)  │       │  (FastAPI)   │       │  (MinIO)  │
│             │       │              │       │           │
│  • UI       │       │  • presigned │       │  • raw/   │
│  • preview  │       │  • process   │       │  • public/│
│  • SSE poll │       │  • SSE       │       │           │
│  • submit   │       │  • cleanup   │       │           │
└──────┬──────┘       └──────────────┘       └───────────┘
       │
       │ JWT
       │
┌──────▼──────┐
│   Backend   │
│  (FastAPI)  │
│             │
│  • products │
│  • brands   │
│  • catalog  │
│  • stores   │
│    only URL │
└─────────────┘
```

### Responsibility Matrix

| Service | Owns | Does NOT know about |
|---------|------|---------------------|
| **Frontend** | UI, local preview, orchestration between services, temporary state (storage_object_id <-> form) | S3 directly, image processing |
| **ImageBackend** | Presigned URLs, upload/confirm, processing (resize, WebP, thumbnails), SSE status, S3 lifecycle, `storage_objects` table | Products, brands, variants, catalog — any business context |
| **Backend** | Products, brands, variants, catalog, `media_assets` table (URL + metadata only) | S3, file processing, presigned URLs, processing statuses |
| **Bucket (S3)** | Physical file storage (raw + processed) | Everything else |

### Key Principle

**ImageBackend is a generic image service.** Its API operates with `storage_object_id`, `content_type`, `public_url`. It does not know the words "product", "brand", "variant". Binding an image to a business entity is the responsibility of Frontend + Backend.

---

## Upload Flow (Main Scenario)

```
Frontend              ImageBackend                S3                 Backend
   │                       │                      │                     │
   │  ① POST /api/v1/media/upload                 │                     │
   │  {content_type, filename}                    │                     │
   │  Authorization: Bearer <JWT>                  │                     │
   │──────────────────────>│                      │                     │
   │                       │  validate JWT         │                     │
   │                       │  create StorageObject │                     │
   │                       │  generate S3 key:     │                     │
   │                       │  raw/{storage_object_id}/{fn}              │
   │                       │  gen presigned PUT ──>│                     │
   │                       │<─────────────────────│                     │
   │<──────────────────────│                      │                     │
   │  201 {                │                      │                     │
   │    storage_object_id, │                      │                     │
   │    presigned_url,     │                      │                     │
   │    expires_in: 300    │                      │                     │
   │  }                    │                      │                     │
   │                       │                      │                     │
   │  ② PUT presigned_url  │                      │                     │
   │  Content-Type: image/jpeg                    │                     │
   │  <binary blob>        │                      │                     │
   │─────────────────────────────────────────────>│                     │
   │<─────────────────────────────────────────────│                     │
   │  200 OK               │                      │                     │
   │                       │                      │                     │
   │  ③ POST /api/v1/media/{storage_object_id}/confirm                 │
   │  Authorization: Bearer <JWT>                  │                     │
   │──────────────────────>│                      │                     │
   │                       │  HEAD raw/{id}/{fn} ─>│                     │
   │                       │<──── 200 (exists) ───│                     │
   │                       │  status → PROCESSING  │                     │
   │                       │  dispatch bg task     │                     │
   │<──────────────────────│                      │                     │
   │  202 {status:         │                      │                     │
   │    "processing"}      │                      │                     │
   │                       │                      │                     │
   │  ③b GET /api/v1/media/{storage_object_id}/status (SSE)            │
   │  Authorization: Bearer <JWT>                  │                     │
   │──────────────────────>│                      │                     │
   │<──── SSE stream ─────│                      │                     │
   │  event: status        │                      │                     │
   │  data: {status:       │                      │                     │
   │    "processing"}      │                      │                     │
   │                       │  ④ Background worker: │                     │
   │                       │  • download raw       │                     │
   │                       │  • resize/webp/thumb  │                     │
   │                       │  • PUT processed ────>│                     │
   │                       │  • delete raw ───────>│                     │
   │                       │  • status → COMPLETED │                     │
   │                       │  • build public_url   │                     │
   │  event: status        │                      │                     │
   │  data: {status:       │                      │                     │
   │    "completed",       │                      │                     │
   │    storage_object_id, │                      │                     │
   │    public_url,        │                      │                     │
   │    variants: [        │                      │                     │
   │      {size, url}...   │                      │                     │
   │    ]                  │                      │                     │
   │  }                    │                      │                     │
   │                       │                      │                     │
   │  ⑤ User finishes form, clicks "Create"       │                     │
   │                       │                      │                     │
   │  POST /api/v1/catalog/products               │                     │
   │  {                    │                      │                     │
   │    name, brand_id, ...,                      │                     │
   │    media: [           │                      │                     │
   │      {                │                      │                     │
   │        public_url,    │                      │                     │
   │        storage_object_id,                    │                     │
   │        media_type: "IMAGE",                  │                     │
   │        role: "MAIN",  │                      │                     │
   │        variant_id: null,                     │                     │
   │        sort_order: 0  │                      │                     │
   │      }                │                      │                     │
   │    ]                  │                      │                     │
   │  }                    │                      │                     │
   │──────────────────────────────────────────────────────────────────>│
   │                       │                      │  create Product     │
   │                       │                      │  create MediaAsset  │
   │                       │                      │  records (URL only) │
   │<──────────────────────────────────────────────────────────────────│
   │  201 {product}        │                      │                     │
```

### Steps

| Step | Who -> Who | What happens |
|------|-----------|--------------|
| 1 | Frontend -> ImageBackend | Request presigned URL. ImageBackend creates `StorageObject` (status: `PENDING_UPLOAD`), returns `storage_object_id` |
| 2 | Frontend -> S3 | Direct file upload via presigned PUT URL |
| 3 | Frontend -> ImageBackend | Confirm upload. ImageBackend verifies file in S3, starts processing. Returns `202 Accepted`. |
| 3b | Frontend -> ImageBackend | Open SSE stream via `GET /status` to receive processing updates |
| 4 | ImageBackend worker | Background processing: resize, WebP, thumbnails. On completion — push `completed` + `public_url` via SSE |
| 5 | Frontend -> Backend | Create product with media links array. Backend saves `MediaAsset` records (URL + metadata only) |

---

## Deletion Flow

```
Frontend                        Backend                ImageBackend         S3
   │                               │                        │                │
   │  DELETE /api/v1/catalog/      │                        │                │
   │  products/{id}/media/{media_id}                        │                │
   │  Authorization: Bearer <JWT>   │                        │                │
   │──────────────────────────────>│                        │                │
   │                               │  ① delete MediaAsset   │                │
   │                               │     from DB            │                │
   │                               │                        │                │
   │                               │  ② DELETE /api/v1/media/{storage_object_id}
   │                               │  Authorization: API-key│                │
   │                               │───────────────────────>│                │
   │                               │                        │  delete files >│
   │                               │                        │  delete record │
   │                               │<───────────────────────│                │
   │                               │  200 OK                │                │
   │<──────────────────────────────│                        │                │
   │  200 {deleted}                │                        │                │
```

### Steps

| Step | Who -> Who | What happens |
|------|-----------|--------------|
| 1 | Backend | Deletes `MediaAsset` record from DB, extracts `storage_object_id` |
| 2 | Backend -> ImageBackend | HTTP call `DELETE /api/v1/media/{storage_object_id}`. ImageBackend deletes files from S3 + `StorageObject` record |

### Fault Tolerance

- If step 2 fails (ImageBackend unavailable) — `MediaAsset` already deleted from catalog. Orphan file in S3 will be cleaned by ImageBackend cron.
- Backend logs warning but does NOT rollback `MediaAsset` deletion.

### Authentication: Backend -> ImageBackend

Server-to-server via **internal API-key** (HMAC), not user JWT.

---

## Brand Logo Flow

Unified flow through ImageBackend. Brand stores only `logo_url` + `logo_storage_object_id`.

```
Frontend              ImageBackend                S3                 Backend
   │                       │                      │                     │
   │  ① Upload via shared flow:                   │                     │
   │  POST /api/v1/media/upload                   │                     │
   │  {content_type: "image/png", filename}       │                     │
   │──────────────────────>│                      │                     │
   │<── {storage_object_id, presigned_url} ───────│                     │
   │                       │                      │                     │
   │  ② PUT presigned_url ───────────────────────>│                     │
   │                       │                      │                     │
   │  ③ POST /api/v1/media/{storage_object_id}/confirm                 │
   │──────────────────────>│                      │                     │
   │<── SSE: completed     │                      │                     │
   │  {storage_object_id, public_url}             │                     │
   │                       │                      │                     │
   │  ④ POST /api/v1/catalog/brands               │                     │
   │  {name: "Nike",       │                      │                     │
   │   logo_url: "https://cdn.../abc.webp",       │                     │
   │   logo_storage_object_id: "..."}             │                     │
   │──────────────────────────────────────────────────────────────────>│
   │                       │                      │  create Brand       │
   │<──────────────────────────────────────────────────────────────────│
   │  201 {brand}          │                      │                     │
```

### Brand Model Changes

**Before (complex FSM):**
```python
logo_status: MediaProcessingStatus  # PENDING -> PROCESSING -> COMPLETED -> FAILED
logo_file_id: uuid.UUID
logo_url: str
# + 5 FSM methods + 3 domain events
```

**After (two fields):**
```python
logo_url: str | None
logo_storage_object_id: uuid.UUID | None
```

Logo deletion: same pattern — Backend clears `logo_url`, calls `DELETE` in ImageBackend for old `logo_storage_object_id`.

---

## Simplified Backend Models

### MediaAsset (Domain Entity)

Simple dataclass — data without behavior. No AggregateRoot, no FSM, no domain events.

```python
@define
class MediaAsset:
    id: uuid.UUID
    product_id: uuid.UUID
    variant_id: uuid.UUID | None

    media_type: str          # IMAGE, VIDEO, MODEL_3D, DOCUMENT
    role: str                # MAIN, HOVER, GALLERY, HERO_VIDEO, SIZE_GUIDE, PACKAGING
    sort_order: int
    is_external: bool        # True = external URL, not our S3

    storage_object_id: uuid.UUID | None   # reference to StorageObject in ImageBackend
    public_url: str | None                # CDN URL

    created_at: datetime
    updated_at: datetime
```

### MediaAsset (ORM)

```python
class MediaAssetModel(Base):
    __tablename__ = "media_assets"

    id            = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid7)
    product_id    = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    variant_id    = mapped_column(ForeignKey("product_variants.id", ondelete="CASCADE"), nullable=True, index=True)

    media_type    = mapped_column(Enum(MediaType, name="media_type_enum"), server_default=MediaType.IMAGE.name, index=True)
    role          = mapped_column(Enum(MediaRole, name="media_role_enum"), server_default=MediaRole.GALLERY.name)
    sort_order    = mapped_column(Integer, server_default=text("0"))
    is_external   = mapped_column(Boolean, server_default=text("false"))

    storage_object_id = mapped_column(UUID(as_uuid=True), nullable=True, unique=True, index=True,
                                      comment="Unique ref to StorageObject in ImageBackend. NULL for external media. "
                                              "PostgreSQL default: NULLs are distinct, so multiple is_external rows with NULL are allowed.")
    public_url        = mapped_column(String(1024), nullable=True)

    created_at    = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at    = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    product       = relationship("Product", back_populates="media_assets")
    variant       = relationship("ProductVariant", back_populates="media_assets")

    __table_args__ = (
        Index(
            "uix_media_single_main_per_variant",
            "product_id", "variant_id",
            unique=True,
            postgresql_where=text(f"role = '{MediaRole.MAIN.name}'"),
            postgresql_nulls_not_distinct=True,
        ),
    )
```

---

## ImageBackend API Contract

### Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/api/v1/media/upload` | JWT | Reserve upload slot, return presigned PUT URL |
| `POST` | `/api/v1/media/{storage_object_id}/confirm` | JWT | Confirm upload, start processing. Returns `202 {status: "processing"}` |
| `GET` | `/api/v1/media/{storage_object_id}/status` | JWT | SSE stream for processing status (primary status channel) |
| `POST` | `/api/v1/media/external` | JWT | Import image from external URL |
| `DELETE` | `/api/v1/media/{storage_object_id}` | API-key | Delete files from S3 + record. Server-to-server only |
| `GET` | `/api/v1/media/{storage_object_id}` | JWT | Get metadata (public_url, variants, status) |

### Request / Response Schemas

**POST /upload**
```json
// Request
{"content_type": "image/jpeg", "filename": "photo.jpg"}

// Response 201
{
  "storage_object_id": "019614a1-...",
  "presigned_url": "https://s3.../raw/019614a1-.../photo.jpg?X-Amz-...",
  "expires_in": 300
}
```

**POST /{storage_object_id}/confirm**
```json
// Response 202
{"storage_object_id": "019614a1-...", "status": "processing"}
```

Frontend then opens SSE stream via `GET /status`:

**GET /{storage_object_id}/status — SSE Stream**

> **SSE Auth Note:** Browser `EventSource` API does not support custom headers.
> Frontend must use `fetch()`-based SSE (e.g. `@microsoft/fetch-event-source`) to pass
> `Authorization: Bearer <JWT>` header. Alternatively, pass a short-lived token as query
> parameter: `GET /status?token=<jwt>` (ImageBackend validates both header and query).

```
event: status
data: {"status": "processing", "storage_object_id": "019614a1-..."}

event: ping
data: {}

event: status
data: {"status": "completed", "storage_object_id": "019614a1-...",
       "public_url": "https://cdn.example.com/public/019614a1.webp",
       "variants": [
         {"size": "thumbnail", "width": 150, "height": 150, "url": "https://cdn.example.com/public/019614a1_thumb.webp"},
         {"size": "medium", "width": 600, "height": 600, "url": "https://cdn.example.com/public/019614a1_md.webp"},
         {"size": "large", "width": 1200, "height": 1200, "url": "https://cdn.example.com/public/019614a1_lg.webp"}
       ]}

event: status
data: {"status": "failed", "storage_object_id": "019614a1-...", "error": "Unsupported format"}
```

**POST /external**

> Synchronous endpoint: downloads, processes, and returns result inline.
> Max input file size: 10 MB. Timeout: 30 seconds.
> For larger files, Frontend should use the presigned upload flow instead.

```json
// Request
{"url": "https://example.com/image.jpg"}

// Response 201
{
  "storage_object_id": "019614a1-...",
  "public_url": "https://cdn.example.com/public/019614a1.webp",
  "variants": [...]
}
```

**DELETE /{storage_object_id}**
```json
// Response 200
{"deleted": true}
```

**GET /{storage_object_id}**
```json
{
  "storage_object_id": "019614a1-...",
  "status": "completed",
  "public_url": "https://cdn.example.com/public/019614a1.webp",
  "content_type": "image/webp",
  "size_bytes": 145320,
  "variants": [...],
  "created_at": "2026-03-25T10:00:00Z"
}
```

### Image Processing Pipeline (Background Worker)

```
Input:  raw/{storage_object_id}/{filename}    (from S3)
Output: public/{storage_object_id}.webp       (main)
        public/{storage_object_id}_thumb.webp (150x150)
        public/{storage_object_id}_md.webp    (600x600)
        public/{storage_object_id}_lg.webp    (1200x1200)
```

Pipeline steps:
1. Download raw from S3
2. Validate (format, size, not corrupted)
3. Convert to WebP (lossless for main, lossy quality=85 for variants)
4. Resize to thumbnail, medium, large (preserving aspect ratio, fit within bounds)
5. Upload processed + variants to S3
6. Delete raw from S3
7. Update `StorageObject` status -> `COMPLETED`, set `public_url`
8. Push SSE event

### SSE Mechanics

- `POST /confirm` returns `202` immediately. Frontend then opens `GET /status` SSE stream.
- `GET /status` sends current state on connect (if already completed — sends completed event immediately and closes)
- On reconnect: same `GET /status` — idempotent, always returns latest state
- Timeout: 120 seconds. If processing not done — SSE closes, Frontend reconnects via `GET /status`
- Heartbeat: `event: ping` every 15 seconds to keep connection alive
- **Auth for SSE:** Frontend uses `fetch()`-based SSE client (e.g. `@microsoft/fetch-event-source`) to pass JWT header. Native `EventSource` does not support custom headers.

---

## Backend API — Accepting Media in Product Create/Update

### Create Product with Media

**POST /api/v1/catalog/products**
```json
{
  "name": "Nike Air Max 90",
  "brand_id": "...",
  "category_id": "...",
  "description": "...",
  "media": [
    {
      "public_url": "https://cdn.example.com/public/aaa.webp",
      "storage_object_id": "aaa-...",
      "media_type": "IMAGE",
      "role": "MAIN",
      "variant_id": null,
      "sort_order": 0,
      "is_external": false
    },
    {
      "public_url": "https://cdn.example.com/public/bbb.webp",
      "storage_object_id": "bbb-...",
      "media_type": "IMAGE",
      "role": "GALLERY",
      "variant_id": null,
      "sort_order": 1,
      "is_external": false
    }
  ]
}
```

### Update Media — Full Replace Strategy

**PATCH /api/v1/catalog/products/{product_id}** with `media[]` array.

Backend compares current `MediaAsset` records with incoming array:

| Situation | Action |
|-----------|--------|
| `storage_object_id` in request but not in DB | Create new `MediaAsset` |
| `storage_object_id` in DB but not in request | Delete `MediaAsset` + call `DELETE` in ImageBackend |
| `storage_object_id` matches | Update `role`, `sort_order`, `variant_id` if changed |
| `is_external: true` (no `storage_object_id`) | Compare by `public_url` |

### Backend Validation

```
- public_url: required, max 1024 chars, valid URL format
- storage_object_id: required if is_external=false, UUID format
- media_type: one of IMAGE, VIDEO, MODEL_3D, DOCUMENT
- role: one of MAIN, HOVER, GALLERY, HERO_VIDEO, SIZE_GUIDE, PACKAGING
- sort_order: int >= 0
- is_external: bool, default false
- variant_id: optional UUID, must reference existing variant of this product
- Max 1 MAIN role per variant_id (unique constraint)
- Max 50 media items per product (application-level validation)
```

### Brand with Logo

**POST /api/v1/catalog/brands**
```json
{"name": "Nike", "logo_url": "https://cdn.../xyz.webp", "logo_storage_object_id": "xyz-..."}
```

On logo change — Backend saves new logo first, then calls `DELETE` in ImageBackend for old `logo_storage_object_id` (best-effort). If Backend crashes between save and delete, old image becomes orphan — acceptable, handled by orphan cleanup.

### ImageBackendClient

```python
class ImageBackendClient:
    """HTTP client for server-to-server calls to ImageBackend."""

    async def delete(self, storage_object_id: uuid.UUID) -> None:
        """DELETE /api/v1/media/{storage_object_id}
        Best-effort: logs error, does not raise.
        Orphan cleanup on ImageBackend side.
        """
```

---

## Error Handling and Edge Cases

| Scenario | What happens | Consequence |
|----------|-------------|-------------|
| Frontend closed tab after upload, before submit | File processed in ImageBackend, Backend never got URL | Orphan in S3. ImageBackend cron cleans up. |
| ImageBackend unavailable during upload | Frontend gets error from ImageBackend | Frontend shows "Upload service unavailable". Backend unaffected. |
| Processing failed | SSE sends `status: failed` | Frontend shows error near preview. User can delete and re-upload. Image never reaches Backend. |
| Backend unavailable during submit | Files already in S3, but MediaAsset not created | Frontend retry. Files safe in ImageBackend. |
| ImageBackend unavailable during DELETE | Backend deleted MediaAsset, file remains | Backend logs warning. Orphan cleanup handles it. |
| Duplicate storage_object_id | Frontend sends same `storage_object_id` twice | Backend rejects — unique constraint on `storage_object_id` in `media_assets` |
| SSE disconnect during processing | Connection dropped | Frontend reconnects via `GET /status`. If already completed — gets result immediately. |
| Presigned URL expired | Frontend didn't upload within 300 sec | Frontend requests new `POST /upload`. Old `StorageObject` is orphan, cleanup handles it. |

### Orphan Cleanup (ImageBackend Cron)

```
Frequency: once daily (or every 6 hours)

Phase 1 — Abandoned uploads (safe, no cross-service check needed):
  1. SELECT FROM storage_objects WHERE status = 'PENDING_UPLOAD' AND created_at < NOW() - INTERVAL '24 hours'
  2. DELETE raw files from S3
  3. DELETE records from storage_objects

Phase 2 — Abandoned completed files (optional, requires cross-service check):
  ImageBackend has no business context, so it cannot know if a COMPLETED file is
  still referenced by Backend. Options (choose one at implementation time):
  a) Backend exposes a bulk endpoint: POST /internal/media/check-referenced
     Body: [storage_object_id, ...] -> Response: [referenced_ids]
     ImageBackend calls this to find unreferenced completed files older than 7 days.
  b) Skip Phase 2 entirely — accept that completed-but-abandoned images remain
     in S3 indefinitely. Storage cost is low; simplicity is high.
  c) Backend periodically pushes a "still-alive" list to ImageBackend via cron.

  Recommendation: start with (b), add (a) later if orphan volume becomes a concern.
```

### Timeouts and Limits

| Parameter | Value | Where |
|-----------|-------|-------|
| Presigned URL TTL | 300 sec (5 min) | ImageBackend |
| Max file size | 50 MB | S3 presigned policy |
| SSE timeout | 120 sec | ImageBackend |
| SSE heartbeat | 15 sec | ImageBackend |
| Processing timeout | 300 sec (5 min) | ImageBackend TaskIQ worker |
| Backend -> ImageBackend HTTP timeout | 10 sec | Backend ImageBackendClient |
| Orphan cleanup age | 24h (pending), 7d (unreferenced) | ImageBackend cron |

---

## Full Change Map

### Backend — Delete

| What | File/Module |
|------|------------|
| Storage module entirely | `src/modules/storage/` |
| `IBlobStorage`, `IStorageFacade` | `src/shared/interfaces/blob_storage.py`, `storage.py` |
| `IStorageConfig` (S3 settings) | `src/shared/interfaces/config.py` |
| `S3ClientFactory` | `src/infrastructure/storage/factory.py` |
| S3 env vars | `S3_ENDPOINT_URL`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_REGION`, `S3_BUCKET_NAME`, `S3_PUBLIC_BASE_URL` |
| `MediaProcessingStatus` enum | `src/modules/catalog/domain/value_objects.py` |
| MediaAsset FSM (factory methods, transitions) | `src/modules/catalog/domain/entities.py` |
| Media domain events | `ProductMediaConfirmedEvent`, `ProductMediaProcessedEvent` in `events.py` |
| Brand logo FSM + events | `Brand.logo_status`, `logo_file_id`, 5 methods, 3 events |
| `BrandLogoProcessor` | `src/modules/catalog/application/services/media_processor.py` |
| Brand storage consumers | `src/modules/storage/application/consumers/brand_events.py` |
| Command handlers: `AddProductMedia`, `ConfirmProductMedia`, `CompleteProductMedia`, `FailProductMedia` | `src/modules/catalog/application/commands/` |
| Internal webhook router | `src/modules/catalog/presentation/router_internal.py` |
| Product media router (presigned, confirm, delete) | `src/modules/catalog/presentation/router_product_media.py` |
| Media-related schemas (upload request, confirm, webhook) | `src/modules/catalog/presentation/schemas.py` |
| `MediaAssetProvider` (old DI wiring) | `src/modules/catalog/presentation/dependencies.py` |
| S3 key constants | `src/modules/catalog/application/constants.py` |
| `storage_objects` table | Alembic migration (DROP TABLE) |
| `processing_status`, `raw_object_key`, `processed_object_key`, `external_url` columns | Alembic migration (DROP COLUMN) |

### Backend — Modify

| What | How |
|------|-----|
| `MediaAsset` entity | Simple dataclass: remove AggregateRoot, FSM, events |
| `MediaAsset` ORM | Remove `processing_status`, `raw_object_key`, `processed_object_key`, `external_url`. Simplify partial index |
| `Brand` entity | Replace logo FSM with `logo_url: str`, `logo_storage_object_id: uuid.UUID` |
| `Brand` ORM | Remove `logo_status`, `logo_file_id`. Add `logo_storage_object_id` |
| `MediaAssetRepository` | Simplify — remove `count_pending_uploads`, status-aware `has_main_for_variant` |
| Product create/update handlers | Accept `media[]` array, do full-replace diff |
| Brand create/update handlers | Accept `logo_url` + `logo_storage_object_id` |
| `DeleteProductMediaHandler` | Delete record + call `ImageBackendClient.delete()` |
| Product/Brand schemas | Add `media[]` to request, `logo_url`/`logo_storage_object_id` to brand request |
| DI container | Remove StorageProvider, MediaAssetProvider. Add `ImageBackendClient` |
| Config | Remove S3 vars. Add `IMAGE_BACKEND_URL`, `IMAGE_BACKEND_API_KEY` |

### Backend — Add

| What | Purpose |
|------|---------|
| `ImageBackendClient` | HTTP client (httpx), one method `delete(storage_object_id)` |
| `IMAGE_BACKEND_URL` env var | ImageBackend address |
| `IMAGE_BACKEND_API_KEY` env var | API-key for server-to-server |
| Alembic migration | DROP columns, DROP table, ADD `logo_storage_object_id` |

### ImageBackend — Implement (in existing scaffold)

| What | Scaffold status |
|------|----------------|
| JWT validation middleware | New (currently API-key only) |
| `POST /upload` — presigned URL | Scaffold exists, refine |
| `POST /{id}/confirm` — SSE stream | Scaffold exists, add SSE |
| `GET /{id}/status` — SSE reconnect | New |
| `POST /external` — import URL | Stub exists, implement |
| `DELETE /{id}` — deletion | New |
| `GET /{id}` — metadata | Stub exists, implement |
| Image processing worker (Pillow) | New (Pillow in deps, no code yet) |
| SSE mechanics (Redis pub/sub for push) | New |
| Orphan cleanup cron | New |

---

## Summary

```
Before: Backend = business logic + media FSM + S3 + presigned + processing + events
After:  Backend = business logic + URL as string + 1 HTTP client for DELETE

Before: ImageBackend = empty scaffold
After:  ImageBackend = full image service (upload, process, SSE, cleanup)
```
