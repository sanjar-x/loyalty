# Product Media Upload — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement Direct-to-S3 media upload for product variants (same pattern as Brand Logo) with webhook endpoint for AI-service (BRIA RMBG-2.0) callback.

**Architecture:** Replicates the Brand Logo flow: presigned PUT URL → client uploads to S3 → confirm → publish task to RabbitMQ → AI-service processes → webhook callback → finalize MediaAsset. MediaAsset has per-variant FSM (PENDING_UPLOAD → PROCESSING → COMPLETED | FAILED). Each media tied to `attribute_value_id` (color variant) or null (shared).

**Tech Stack:** FastAPI, SQLAlchemy 2.x async, Dishka DI, TaskIQ + RabbitMQ, aiobotocore (S3), Alembic

---

## File Structure

```
src/modules/catalog/
├── domain/
│   ├── entities.py                          # MODIFY: add MediaAsset entity
│   ├── value_objects.py                     # EXISTS: MediaProcessingStatus (reuse)
│   ├── events.py                            # MODIFY: add media events
│   └── interfaces.py                        # MODIFY: add IMediaAssetRepository
├── infrastructure/
│   ├── models.py                            # EXISTS: MediaAsset ORM (no changes)
│   └── repositories/
│       └── media_asset.py                   # CREATE: MediaAssetRepository
├── application/
│   ├── constants.py                         # MODIFY: add media S3 key builders
│   ├── commands/
│   │   ├── add_product_media.py             # CREATE: reserve slot + presigned URL
│   │   ├── confirm_product_media.py         # CREATE: verify S3 + FSM → PROCESSING
│   │   ├── complete_product_media.py        # CREATE: webhook callback handler
│   │   └── delete_product_media.py          # CREATE: soft-delete media
│   └── queries/
│       └── list_product_media.py            # CREATE: get media for product
├── presentation/
│   ├── schemas.py                           # MODIFY: add media schemas
│   ├── dependencies.py                      # MODIFY: add MediaAssetProvider
│   ├── router_product_media.py              # CREATE: media CRUD endpoints
│   └── router_internal.py                   # CREATE: webhook callback endpoint
└── ...

src/api/router.py                            # MODIFY: include new routers
alembic/versions/...                         # CREATE: migration (no schema changes, just seed)
```

---

### Task 1: S3 Key Constants

**Files:**

- Modify: `src/modules/catalog/application/constants.py`

- [ ] **Step 1: Add media key builders**

```python
# After existing public_logo_key():

def raw_media_key(product_id: uuid.UUID, media_id: uuid.UUID) -> str:
    return f"raw_uploads/catalog/products/{product_id}/media/{media_id}"


def public_media_key(product_id: uuid.UUID, media_id: uuid.UUID, ext: str = "webp") -> str:
    return f"public/products/{product_id}/media/{media_id}.{ext}"
```

- [ ] **Step 2: Commit**

```bash
git add src/modules/catalog/application/constants.py
git commit -m "feat(catalog): add product media S3 key builders"
```

---

### Task 2: Domain Events

**Files:**

- Modify: `src/modules/catalog/domain/events.py`

- [ ] **Step 1: Add media events at end of file**

```python
# ---------------------------------------------------------------------------
# ProductMedia events
# ---------------------------------------------------------------------------

@dataclass
class ProductMediaConfirmedEvent(DomainEvent):
    """Emitted when a media upload is confirmed — triggers AI processing."""

    media_id: uuid.UUID | None = None
    product_id: uuid.UUID | None = None
    object_key: str = ""
    content_type: str = ""
    aggregate_type: str = "MediaAsset"
    event_type: str = "ProductMediaConfirmedEvent"

    def __post_init__(self) -> None:
        if self.media_id is None:
            raise ValueError("media_id is required")
        if not self.aggregate_id:
            self.aggregate_id = str(self.media_id)


@dataclass
class ProductMediaProcessedEvent(DomainEvent):
    """Emitted when AI processing completes for a media asset."""

    media_id: uuid.UUID | None = None
    product_id: uuid.UUID | None = None
    object_key: str = ""
    content_type: str = ""
    size_bytes: int = 0
    aggregate_type: str = "MediaAsset"
    event_type: str = "ProductMediaProcessedEvent"

    def __post_init__(self) -> None:
        if self.media_id is None:
            raise ValueError("media_id is required")
        if not self.aggregate_id:
            self.aggregate_id = str(self.media_id)
```

- [ ] **Step 2: Commit**

```bash
git add src/modules/catalog/domain/events.py
git commit -m "feat(catalog): add product media domain events"
```

---

### Task 3: MediaAsset Domain Entity

**Files:**

- Modify: `src/modules/catalog/domain/entities.py`

- [ ] **Step 1: Add MediaAsset entity** (after existing entities, before Product)

```python
@define
class MediaAsset:
    """Media file attached to a product, optionally tied to a variant (color)."""

    id: uuid.UUID
    product_id: uuid.UUID
    attribute_value_id: uuid.UUID | None  # NULL = shared, UUID = variant-specific
    media_type: str  # IMAGE, VIDEO, MODEL_3D, DOCUMENT
    role: str  # MAIN, HOVER, GALLERY, HERO_VIDEO, SIZE_GUIDE, PACKAGING
    sort_order: int
    processing_status: str | None  # PENDING_UPLOAD, PROCESSING, COMPLETED, FAILED
    storage_object_id: uuid.UUID | None
    is_external: bool
    external_url: str | None
    raw_object_key: str | None  # S3 key for raw upload (before processing)
    public_url: str | None  # Final public URL after processing

    @classmethod
    def create_upload(
        cls,
        *,
        product_id: uuid.UUID,
        attribute_value_id: uuid.UUID | None,
        media_type: str,
        role: str,
        sort_order: int = 0,
        raw_object_key: str,
        media_id: uuid.UUID | None = None,
    ) -> MediaAsset:
        return cls(
            id=media_id or uuid.uuid4(),
            product_id=product_id,
            attribute_value_id=attribute_value_id,
            media_type=media_type,
            role=role,
            sort_order=sort_order,
            processing_status=MediaProcessingStatus.PENDING_UPLOAD,
            storage_object_id=None,
            is_external=False,
            external_url=None,
            raw_object_key=raw_object_key,
            public_url=None,
        )

    @classmethod
    def create_external(
        cls,
        *,
        product_id: uuid.UUID,
        attribute_value_id: uuid.UUID | None,
        media_type: str,
        role: str,
        external_url: str,
        sort_order: int = 0,
    ) -> MediaAsset:
        return cls(
            id=uuid.uuid4(),
            product_id=product_id,
            attribute_value_id=attribute_value_id,
            media_type=media_type,
            role=role,
            sort_order=sort_order,
            processing_status=MediaProcessingStatus.COMPLETED,
            storage_object_id=None,
            is_external=True,
            external_url=external_url,
            raw_object_key=None,
            public_url=external_url,
        )

    def confirm_upload(self) -> None:
        if self.processing_status != MediaProcessingStatus.PENDING_UPLOAD:
            raise InvalidMediaStateError(self.id, self.processing_status, "PENDING_UPLOAD")
        self.processing_status = MediaProcessingStatus.PROCESSING

    def complete_processing(self, *, public_url: str, object_key: str, storage_object_id: uuid.UUID | None = None) -> None:
        if self.processing_status != MediaProcessingStatus.PROCESSING:
            raise InvalidMediaStateError(self.id, self.processing_status, "PROCESSING")
        self.processing_status = MediaProcessingStatus.COMPLETED
        self.public_url = public_url
        self.storage_object_id = storage_object_id

    def fail_processing(self) -> None:
        if self.processing_status != MediaProcessingStatus.PROCESSING:
            raise InvalidMediaStateError(self.id, self.processing_status, "PROCESSING")
        self.processing_status = MediaProcessingStatus.FAILED
```

- [ ] **Step 2: Add exception to `domain/exceptions.py`**

```python
class InvalidMediaStateError(DomainException):
    def __init__(self, media_id: uuid.UUID, current: str | None, expected: str) -> None:
        super().__init__(f"Media {media_id} is in state {current}, expected {expected}")
```

- [ ] **Step 3: Commit**

```bash
git add src/modules/catalog/domain/entities.py src/modules/catalog/domain/exceptions.py
git commit -m "feat(catalog): add MediaAsset domain entity with FSM"
```

---

### Task 4: Repository Interface + Implementation

**Files:**

- Modify: `src/modules/catalog/domain/interfaces.py`
- Create: `src/modules/catalog/infrastructure/repositories/media_asset.py`

- [ ] **Step 1: Add interface to `interfaces.py`**

```python
class IMediaAssetRepository(ABC):
    @abstractmethod
    async def add(self, media: DomainMediaAsset) -> None: ...

    @abstractmethod
    async def get(self, media_id: uuid.UUID) -> DomainMediaAsset | None: ...

    @abstractmethod
    async def get_for_update(self, media_id: uuid.UUID) -> DomainMediaAsset | None: ...

    @abstractmethod
    async def update(self, media: DomainMediaAsset) -> None: ...

    @abstractmethod
    async def delete(self, media_id: uuid.UUID) -> None: ...

    @abstractmethod
    async def list_by_product(self, product_id: uuid.UUID) -> list[DomainMediaAsset]: ...

    @abstractmethod
    async def has_main_for_variant(self, product_id: uuid.UUID, attribute_value_id: uuid.UUID | None) -> bool: ...
```

- [ ] **Step 2: Create repository implementation** (`infrastructure/repositories/media_asset.py`)

Follow the Data Mapper pattern from `brand.py`: ORM ↔ Domain via `_to_domain()` / `_to_orm()`. Use `selectinload` for eager loading. `get_for_update` uses `with_for_update()`.

- [ ] **Step 3: Commit**

```bash
git add src/modules/catalog/domain/interfaces.py src/modules/catalog/infrastructure/repositories/media_asset.py
git commit -m "feat(catalog): add MediaAssetRepository with Data Mapper"
```

---

### Task 5: Commands — Add Media (Presigned Upload)

**Files:**

- Create: `src/modules/catalog/application/commands/add_product_media.py`

- [ ] **Step 1: Write the command + handler**

Pattern: same as `create_brand.py` — generate presigned URL, create entity in PENDING_UPLOAD.

```python
@dataclass(frozen=True)
class AddProductMediaCommand:
    product_id: uuid.UUID
    attribute_value_id: uuid.UUID | None
    media_type: str  # IMAGE, VIDEO, MODEL_3D, DOCUMENT
    role: str  # MAIN, HOVER, GALLERY, ...
    content_type: str  # image/jpeg, image/png, ...
    sort_order: int = 0

@dataclass(frozen=True)
class AddProductMediaResult:
    media_id: uuid.UUID
    presigned_upload_url: str
    object_key: str

class AddProductMediaHandler:
    def __init__(self, product_repo, media_repo, blob_storage, uow, config): ...

    async def handle(self, cmd) -> AddProductMediaResult:
        # 1. Verify product exists
        # 2. If role=MAIN, check no existing MAIN for this variant
        # 3. Create MediaAsset.create_upload(...)
        # 4. Generate presigned PUT URL via blob_storage
        # 5. Persist media entity
        # 6. Commit
        # 7. Return media_id + presigned URL + object_key
```

- [ ] **Step 2: Commit**

```bash
git add src/modules/catalog/application/commands/add_product_media.py
git commit -m "feat(catalog): add presigned media upload command"
```

---

### Task 6: Commands — Confirm Upload

**Files:**

- Create: `src/modules/catalog/application/commands/confirm_product_media.py`

- [ ] **Step 1: Write the command + handler**

Pattern: same as `confirm_brand_logo.py` — verify S3 file exists, transition FSM, emit event.

```python
class ConfirmProductMediaHandler:
    async def handle(self, cmd) -> None:
        # 1. Load media entity
        # 2. blob_storage.object_exists(raw_key) — verify file uploaded
        # 3. media.confirm_upload() — FSM: PENDING → PROCESSING
        # 4. Emit ProductMediaConfirmedEvent (→ Outbox → RabbitMQ → AI service)
        # 5. Persist + commit
```

- [ ] **Step 2: Commit**

```bash
git add src/modules/catalog/application/commands/confirm_product_media.py
git commit -m "feat(catalog): add media upload confirmation command"
```

---

### Task 7: Commands — Complete Processing (Webhook)

**Files:**

- Create: `src/modules/catalog/application/commands/complete_product_media.py`

- [ ] **Step 1: Write the command + handler**

Called by the internal webhook when AI-service finishes.

```python
@dataclass(frozen=True)
class CompleteProductMediaCommand:
    media_id: uuid.UUID
    object_key: str  # S3 key of processed file
    content_type: str
    size_bytes: int

class CompleteProductMediaHandler:
    async def handle(self, cmd) -> None:
        # 1. Load media with get_for_update (row lock)
        # 2. Build public_url = f"{S3_PUBLIC_BASE_URL}/{cmd.object_key}"
        # 3. media.complete_processing(public_url=..., object_key=...)
        # 4. Emit ProductMediaProcessedEvent
        # 5. Persist + commit
        # 6. Optionally: delete raw file from S3
```

- [ ] **Step 2: Write fail command** (same file or separate `fail_product_media.py`)

```python
class FailProductMediaHandler:
    async def handle(self, cmd) -> None:
        # 1. Load media with get_for_update
        # 2. media.fail_processing()
        # 3. Persist + commit
```

- [ ] **Step 3: Commit**

```bash
git add src/modules/catalog/application/commands/complete_product_media.py
git commit -m "feat(catalog): add media processing webhook commands"
```

---

### Task 8: Commands — Delete Media

**Files:**

- Create: `src/modules/catalog/application/commands/delete_product_media.py`

- [ ] **Step 1: Write delete handler**

```python
class DeleteProductMediaHandler:
    async def handle(self, cmd) -> None:
        # 1. Load media
        # 2. Delete S3 objects (raw + processed) if exist
        # 3. Delete DB record
        # 4. Commit
```

- [ ] **Step 2: Commit**

```bash
git add src/modules/catalog/application/commands/delete_product_media.py
git commit -m "feat(catalog): add media deletion command"
```

---

### Task 9: Query — List Product Media

**Files:**

- Create: `src/modules/catalog/application/queries/list_product_media.py`

- [ ] **Step 1: Write query handler**

```python
class ListProductMediaHandler:
    async def handle(self, product_id: uuid.UUID) -> list[MediaAssetReadModel]:
        # Load all media for product, ordered by (attribute_value_id, sort_order)
```

- [ ] **Step 2: Commit**

```bash
git add src/modules/catalog/application/queries/list_product_media.py
git commit -m "feat(catalog): add list product media query"
```

---

### Task 10: Presentation — Schemas

**Files:**

- Modify: `src/modules/catalog/presentation/schemas.py`

- [ ] **Step 1: Add media schemas at end of file**

```python
class ProductMediaUploadRequest(CamelModel):
    attribute_value_id: uuid.UUID | None = None
    media_type: str = Field(..., pattern=r"^(image|video|model_3d|document)$")
    role: str = Field(..., pattern=r"^(main|hover|gallery|hero_video|size_guide|packaging)$")
    content_type: str = Field(..., pattern=r"^(image|video)/")
    sort_order: int = Field(0, ge=0)

class ProductMediaUploadResponse(CamelModel):
    id: uuid.UUID
    presigned_upload_url: str
    object_key: str

class ProductMediaExternalRequest(CamelModel):
    attribute_value_id: uuid.UUID | None = None
    media_type: str
    role: str
    external_url: str = Field(..., min_length=1)
    sort_order: int = Field(0, ge=0)

class ProductMediaResponse(CamelModel):
    id: uuid.UUID
    product_id: uuid.UUID
    attribute_value_id: uuid.UUID | None
    media_type: str
    role: str
    sort_order: int
    processing_status: str | None
    public_url: str | None
    is_external: bool
    external_url: str | None

class MediaProcessingWebhookRequest(CamelModel):
    """Internal webhook from AI-service."""
    object_key: str
    content_type: str
    size_bytes: int

class MediaProcessingFailedRequest(CamelModel):
    """Internal webhook: AI processing failed."""
    error: str
```

- [ ] **Step 2: Commit**

```bash
git add src/modules/catalog/presentation/schemas.py
git commit -m "feat(catalog): add product media schemas"
```

---

### Task 11: Router — Product Media CRUD

**Files:**

- Create: `src/modules/catalog/presentation/router_product_media.py`

- [ ] **Step 1: Write the router**

| Method   | Path                                      | Permission       | Handler                    |
| -------- | ----------------------------------------- | ---------------- | -------------------------- |
| `POST`   | `/products/{id}/media/upload`             | `catalog:manage` | AddProductMediaHandler     |
| `POST`   | `/products/{id}/media/external`           | `catalog:manage` | (inline — create_external) |
| `POST`   | `/products/{id}/media/{media_id}/confirm` | `catalog:manage` | ConfirmProductMediaHandler |
| `GET`    | `/products/{id}/media`                    | Public           | ListProductMediaHandler    |
| `DELETE` | `/products/{id}/media/{media_id}`         | `catalog:manage` | DeleteProductMediaHandler  |

- [ ] **Step 2: Commit**

```bash
git add src/modules/catalog/presentation/router_product_media.py
git commit -m "feat(catalog): add product media router"
```

---

### Task 12: Router — Internal Webhook

**Files:**

- Create: `src/modules/catalog/presentation/router_internal.py`

- [ ] **Step 1: Write internal webhook router**

```python
internal_router = APIRouter(prefix="/internal/media", tags=["Internal"])

@internal_router.post("/{media_id}/processed")
async def media_processed_webhook(media_id: uuid.UUID, body: MediaProcessingWebhookRequest, handler):
    """Callback from AI-service after processing."""
    # → CompleteProductMediaHandler

@internal_router.post("/{media_id}/failed")
async def media_failed_webhook(media_id: uuid.UUID, body: MediaProcessingFailedRequest, handler):
    """Callback from AI-service on failure."""
    # → FailProductMediaHandler
```

Note: internal endpoints — no Bearer auth, secured by network policy (internal VPC only).

- [ ] **Step 2: Commit**

```bash
git add src/modules/catalog/presentation/router_internal.py
git commit -m "feat(catalog): add internal webhook for AI-service callback"
```

---

### Task 13: DI Wiring

**Files:**

- Modify: `src/modules/catalog/presentation/dependencies.py`
- Modify: `src/bootstrap/container.py`
- Modify: `src/api/router.py`

- [ ] **Step 1: Add MediaAssetProvider to `dependencies.py`**

```python
class MediaAssetProvider(Provider):
    @provide(scope=Scope.REQUEST)
    def media_repo(self, session: AsyncSession) -> IMediaAssetRepository:
        return MediaAssetRepository(session)

    @provide(scope=Scope.REQUEST)
    def add_media_handler(self, ...) -> AddProductMediaHandler:
        return AddProductMediaHandler(...)
    # ... other handlers
```

- [ ] **Step 2: Register in `container.py`**

Add `MediaAssetProvider()` to `create_container()`.

- [ ] **Step 3: Include routers in `api/router.py`**

```python
from src.modules.catalog.presentation.router_product_media import product_media_router
from src.modules.catalog.presentation.router_internal import internal_router

router.include_router(product_media_router, prefix="/catalog")
router.include_router(internal_router)
```

- [ ] **Step 4: Commit**

```bash
git add src/modules/catalog/presentation/dependencies.py src/bootstrap/container.py src/api/router.py
git commit -m "feat(catalog): wire media asset DI and routers"
```

---

### Task 14: Verification

- [ ] **Step 1: Start services**

```bash
docker compose up -d
uv run alembic upgrade head
```

- [ ] **Step 2: Test the full flow**

```bash
# 1. Create a product
curl -X POST http://localhost:8000/api/v1/catalog/products \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"titleI18n":{"ru":"Test"},"slug":"test-media","brandId":"...","primaryCategoryId":"...","supplierId":"..."}'

# 2. Request presigned upload for a media
curl -X POST http://localhost:8000/api/v1/catalog/products/$PID/media/upload \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"mediaType":"image","role":"main","contentType":"image/jpeg"}'
# → 201 { id, presignedUploadUrl, objectKey }

# 3. Upload file to S3
curl -X PUT "$PRESIGNED_URL" -H "Content-Type: image/jpeg" --data-binary @test.jpg

# 4. Confirm upload
curl -X POST http://localhost:8000/api/v1/catalog/products/$PID/media/$MID/confirm \
  -H "Authorization: Bearer $TOKEN"
# → 204 (status = PROCESSING, event in outbox)

# 5. Simulate AI-service webhook
curl -X POST http://localhost:8000/api/v1/internal/media/$MID/processed \
  -d '{"objectKey":"public/products/.../media/....webp","contentType":"image/webp","sizeBytes":12345}'
# → 200 (status = COMPLETED)

# 6. Verify media list
curl http://localhost:8000/api/v1/catalog/products/$PID/media
# → 200 [{ id, publicUrl, processingStatus: "completed", ... }]
```

- [ ] **Step 3: Run existing tests**

```bash
uv run pytest tests/unit/ tests/architecture/ -v
```
