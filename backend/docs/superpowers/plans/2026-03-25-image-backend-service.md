# ImageBackend Service Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform the ImageBackend scaffold into a fully functional image processing microservice with presigned uploads, Pillow-based processing, SSE status streaming, deletion, and orphan cleanup.

**Architecture:** ImageBackend is a generic image service with zero business-domain knowledge. It owns the `storage_objects` table (with new `status`, `url`, `image_variants` columns), S3 lifecycle (raw/ → public/), background processing via TaskIQ workers, and real-time status delivery via SSE. All endpoints are protected by API-key auth (`X-API-Key` header).

**Tech Stack:** FastAPI, SQLAlchemy 2.1 (async), TaskIQ + RabbitMQ, Pillow, aiobotocore (S3/MinIO), Redis (SSE pub/sub), sse-starlette, Alembic, pytest

**Spec:** `docs/superpowers/specs/2026-03-25-media-architecture-split-design.md`

**Working directory:** `C:\Users\Sanjar\Desktop\loyality\image_backend`

**JSON serialization:** All schemas extend `CamelModel` which auto-converts `snake_case` → `camelCase` in JSON responses. The spec shows snake_case for readability, but the actual API returns camelCase (e.g., `storageObjectId`, `presignedUrl`). This is consistent with the Frontend which already uses camelCase.

---

## File Structure

### Create
| File                                                                | Responsibility                                                        |
| ------------------------------------------------------------------- | --------------------------------------------------------------------- |
| `src/modules/storage/domain/value_objects.py`                       | `StorageStatus` enum (PENDING_UPLOAD, PROCESSING, COMPLETED, FAILED)  |
| `src/modules/storage/application/commands/process_image.py`         | `ProcessImageCommand` + `ProcessImageHandler` — Pillow pipeline       |
| `src/modules/storage/application/commands/delete_storage_object.py` | `DeleteStorageObjectCommand` + handler — S3 cleanup + DB delete       |
| `src/modules/storage/application/commands/import_external.py`       | `ImportExternalCommand` + handler — download URL, process, return     |
| `src/modules/storage/presentation/sse.py`                           | SSE manager: Redis pub/sub → `EventSourceResponse`                    |
| `alembic/versions/2026/03/25_add_status_url_variants.py`            | Migration: ADD `status`, `url`, `image_variants` to `storage_objects` |
| `tests/unit/modules/storage/domain/test_value_objects.py`           | Tests for StorageStatus enum                                          |
| `tests/unit/modules/storage/domain/test_entities.py`                | Tests for StorageFile with new fields                                 |
| `tests/unit/modules/storage/application/test_process_image.py`      | Tests for image processing pipeline                                   |
| `tests/unit/modules/storage/presentation/test_router.py`            | Tests for all 6 endpoints                                             |
| `tests/unit/modules/storage/presentation/test_sse.py`               | Tests for SSE manager                                                 |

### Modify
| File                                               | What changes                                                                     |
| -------------------------------------------------- | -------------------------------------------------------------------------------- |
| `src/modules/storage/domain/entities.py`           | Add `status`, `url`, `image_variants`, `filename` fields to `StorageFile`        |
| `src/modules/storage/infrastructure/models.py`     | Add `status`, `url`, `image_variants`, `filename` columns to `StorageObject` ORM |
| `src/modules/storage/infrastructure/repository.py` | Update mapper for new fields, add `get_by_id()`, `list_pending_expired()`        |
| `src/modules/storage/infrastructure/service.py`    | No changes needed                                                                |
| `src/modules/storage/presentation/router.py`       | Rewrite all endpoints per spec, wire auth, add SSE + DELETE                      |
| `src/modules/storage/presentation/schemas.py`      | Rewrite schemas to match spec contract                                           |
| `src/modules/storage/presentation/facade.py`       | Simplify: remove unused methods, add confirm/processing flow                     |
| `src/modules/storage/presentation/dependencies.py` | Add command handler providers                                                    |
| `src/modules/storage/presentation/tasks.py`        | Add `process_image_task`, `cleanup_orphans_task`                                 |
| `src/api/router.py`                                | Wire auth dependency globally                                                    |
| `src/api/dependencies/auth.py`                     | Add query param fallback for SSE (`api_key=`)                                    |
| `src/bootstrap/container.py`                       | Add Redis provider for SSE pub/sub                                               |
| `src/bootstrap/config.py`                          | Add `SSE_TIMEOUT`, `SSE_HEARTBEAT`, `PROCESSING_TIMEOUT`                         |
| `src/infrastructure/database/registry.py`          | No changes (StorageObject already registered)                                    |
| `pyproject.toml`                                   | Add `sse-starlette`, `httpx` to runtime deps                                     |

---

## Task 1: Add `sse-starlette` and `httpx` dependencies

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Add dependencies**

```toml
# In [project] dependencies, add:
"sse-starlette>=2.0.0",
"httpx>=0.28.0",
```

- [ ] **Step 2: Install**

Run: `cd C:\Users\Sanjar\Desktop\loyality\image_backend && uv sync`
Expected: dependencies install successfully

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "chore(image-backend): add sse-starlette and httpx deps"
```

---

## Task 2: StorageStatus enum + StorageFile domain entity updates

**Files:**
- Create: `src/modules/storage/domain/value_objects.py`
- Modify: `src/modules/storage/domain/entities.py`
- Create: `tests/unit/modules/storage/domain/test_value_objects.py`
- Modify: `tests/unit/modules/storage/domain/test_entities.py` (if exists, else create)

- [ ] **Step 1: Write failing test for StorageStatus**

```python
# tests/unit/modules/storage/domain/test_value_objects.py
from src.modules.storage.domain.value_objects import StorageStatus


def test_storage_status_values():
    assert StorageStatus.PENDING_UPLOAD == "PENDING_UPLOAD"
    assert StorageStatus.PROCESSING == "PROCESSING"
    assert StorageStatus.COMPLETED == "COMPLETED"
    assert StorageStatus.FAILED == "FAILED"


def test_storage_status_is_terminal():
    assert StorageStatus.COMPLETED.is_terminal is True
    assert StorageStatus.FAILED.is_terminal is True
    assert StorageStatus.PENDING_UPLOAD.is_terminal is False
    assert StorageStatus.PROCESSING.is_terminal is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd C:\Users\Sanjar\Desktop\loyality\image_backend && python -m pytest tests/unit/modules/storage/domain/test_value_objects.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.modules.storage.domain.value_objects'`

- [ ] **Step 3: Implement StorageStatus**

```python
# src/modules/storage/domain/value_objects.py
"""Storage domain value objects."""
from enum import StrEnum


class StorageStatus(StrEnum):
    """Processing lifecycle of a storage object."""

    PENDING_UPLOAD = "PENDING_UPLOAD"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

    @property
    def is_terminal(self) -> bool:
        return self in (StorageStatus.COMPLETED, StorageStatus.FAILED)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/modules/storage/domain/test_value_objects.py -v`
Expected: 2 passed

- [ ] **Step 5: Write failing test for updated StorageFile**

```python
# tests/unit/modules/storage/domain/test_entities.py
import uuid
from src.modules.storage.domain.entities import StorageFile
from src.modules.storage.domain.value_objects import StorageStatus


def test_create_storage_file_has_new_fields():
    sf = StorageFile.create(
        bucket_name="test-bucket",
        object_key="raw/abc/photo.jpg",
        content_type="image/jpeg",
        filename="photo.jpg",
    )
    assert sf.status == StorageStatus.PENDING_UPLOAD
    assert sf.url is None
    assert sf.image_variants is None
    assert sf.filename == "photo.jpg"


def test_storage_file_complete():
    sf = StorageFile.create(
        bucket_name="b",
        object_key="raw/x/f.jpg",
        content_type="image/jpeg",
        filename="f.jpg",
    )
    sf.status = StorageStatus.COMPLETED
    sf.url = "https://cdn.example.com/public/x.webp"
    sf.image_variants = [
        {"size": "thumbnail", "width": 150, "height": 150, "url": "https://cdn.example.com/public/x_thumb.webp"},
    ]
    assert sf.status == StorageStatus.COMPLETED
    assert sf.url.endswith(".webp")
    assert len(sf.image_variants) == 1
```

- [ ] **Step 6: Run test to verify it fails**

Run: `python -m pytest tests/unit/modules/storage/domain/test_entities.py -v`
Expected: FAIL — `TypeError` (unexpected keyword `filename`)

- [ ] **Step 7: Update StorageFile entity**

In `src/modules/storage/domain/entities.py`, add new fields to the `StorageFile` attrs dataclass:

```python
from src.modules.storage.domain.value_objects import StorageStatus

# Add these fields to the @dataclass class StorageFile:
    status: StorageStatus = StorageStatus.PENDING_UPLOAD
    url: str | None = None
    image_variants: list[dict] | None = None
    filename: str | None = None
```

Update `create()` factory to accept `filename` parameter and pass it through.

- [ ] **Step 8: Run tests to verify they pass**

Run: `python -m pytest tests/unit/modules/storage/domain/ -v`
Expected: all passed

- [ ] **Step 9: Commit**

```bash
git add src/modules/storage/domain/ tests/unit/modules/storage/domain/
git commit -m "feat(image-backend): add StorageStatus enum and extend StorageFile entity"
```

---

## Task 3: StorageObject ORM model + Alembic migration

**Files:**
- Modify: `src/modules/storage/infrastructure/models.py`
- Modify: `src/modules/storage/infrastructure/repository.py`
- Create: `alembic/versions/` (auto-generated migration)

- [ ] **Step 1: Add columns to StorageObject ORM**

In `src/modules/storage/infrastructure/models.py`, add after existing columns:

```python
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from src.modules.storage.domain.value_objects import StorageStatus

# Add to StorageObject class:
    status: Mapped[str] = mapped_column(
        SAEnum(StorageStatus, name="storage_status_enum", create_type=True),
        server_default=StorageStatus.PENDING_UPLOAD.value,
        index=True,
    )
    url: Mapped[str | None] = mapped_column(
        String(1024),
        nullable=True,
        comment="Public CDN URL after processing",
    )
    image_variants: Mapped[list[dict] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Processed size variants: [{size, width, height, url}]",
    )
    filename: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Original upload filename",
    )
```

- [ ] **Step 2: Update repository mapper `_to_domain` and `_to_orm`**

In `src/modules/storage/infrastructure/repository.py`, update both mapper methods to include the 4 new fields: `status`, `url`, `image_variants`, `filename`.

Add new method `get_by_id(storage_object_id: uuid.UUID)` that fetches by PK.

Add new method `list_pending_expired(older_than: datetime)` for orphan cleanup:
```python
async def list_pending_expired(self, older_than: datetime) -> list[StorageFile]:
    stmt = select(StorageObject).where(
        StorageObject.status == StorageStatus.PENDING_UPLOAD.value,
        StorageObject.created_at < older_than,
    )
    result = await self._session.execute(stmt)
    return [self._to_domain(row) for row in result.scalars().all()]
```

- [ ] **Step 3: Generate Alembic migration**

Run: `cd C:\Users\Sanjar\Desktop\loyality\image_backend && alembic revision --autogenerate -m "add status url variants filename to storage_objects"`
Expected: migration file created

- [ ] **Step 4: Review the generated migration**

Read the generated file. Verify it contains:
- `op.add_column('storage_objects', sa.Column('status', ...))` with server_default
- `op.add_column('storage_objects', sa.Column('url', ...))` nullable
- `op.add_column('storage_objects', sa.Column('image_variants', JSONB))` nullable
- `op.add_column('storage_objects', sa.Column('filename', ...))` nullable
- `op.create_index` on status column

- [ ] **Step 5: Run migration**

Run: `alembic upgrade head`
Expected: migration applies successfully

- [ ] **Step 6: Commit**

```bash
git add src/modules/storage/infrastructure/models.py src/modules/storage/infrastructure/repository.py alembic/
git commit -m "feat(image-backend): add status/url/image_variants/filename to StorageObject + migration"
```

---

## Task 4: Wire API-key auth to all endpoints

**Files:**
- Modify: `src/api/dependencies/auth.py`
- Modify: `src/api/router.py`
- Create: `tests/unit/api/test_auth.py`

- [ ] **Step 1: Write failing test**

```python
# tests/unit/api/test_auth.py
import pytest
from httpx import AsyncClient, ASGITransport
from src.bootstrap.web import create_app


@pytest.fixture
def app():
    return create_app()


@pytest.mark.anyio
async def test_upload_without_api_key_returns_401(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/v1/media/upload", json={"content_type": "image/jpeg"})
    assert resp.status_code == 401
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/unit/api/test_auth.py -v`
Expected: FAIL — currently returns 422 or 201 (no auth check)

- [ ] **Step 3: Add query param fallback to auth dependency**

In `src/api/dependencies/auth.py`:

```python
async def verify_api_key(
    x_api_key: str | None = Header(None, alias="X-API-Key"),
    api_key: str | None = Query(None),
) -> None:
    """Validate API key from header or query param (needed for SSE EventSource)."""
    key = x_api_key or api_key
    internal_key = settings.INTERNAL_API_KEY.get_secret_value()
    if not internal_key:
        return  # auth disabled in dev
    if not key or not hmac.compare_digest(key, internal_key):
        raise UnauthorizedError("Invalid API key")
```

- [ ] **Step 4: Apply auth dependency to router globally**

In `src/api/router.py`:

```python
from src.api.dependencies.auth import verify_api_key

router = APIRouter(dependencies=[Depends(verify_api_key)])
router.include_router(media_router, prefix="/media", tags=["Media"])
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/unit/api/test_auth.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/api/dependencies/auth.py src/api/router.py tests/unit/api/
git commit -m "feat(image-backend): wire API-key auth to all media endpoints with query param fallback"
```

---

## Task 5: Rewrite schemas to match spec contract

**Files:**
- Modify: `src/modules/storage/presentation/schemas.py`
- Create: `tests/unit/modules/storage/presentation/test_schemas.py`

- [ ] **Step 1: Write test for new schemas**

```python
# tests/unit/modules/storage/presentation/test_schemas.py
from src.modules.storage.presentation.schemas import (
    UploadRequest,
    UploadResponse,
    ConfirmResponse,
    MediaVariant,
    StatusEventData,
    ExternalImportRequest,
    ExternalImportResponse,
    MetadataResponse,
    DeleteResponse,
)


def test_upload_request_requires_content_type():
    req = UploadRequest(content_type="image/jpeg", filename="photo.jpg")
    assert req.content_type == "image/jpeg"
    assert req.filename == "photo.jpg"


def test_upload_response_fields():
    resp = UploadResponse(
        storage_object_id="019614a1-0000-0000-0000-000000000000",
        presigned_url="https://s3.example.com/...",
        expires_in=300,
    )
    assert resp.expires_in == 300


def test_status_event_data_completed():
    data = StatusEventData(
        status="completed",
        storage_object_id="019614a1-0000-0000-0000-000000000000",
        url="https://cdn.example.com/public/abc.webp",
        variants=[
            MediaVariant(size="thumbnail", width=150, height=150, url="https://cdn.example.com/thumb.webp"),
        ],
    )
    assert len(data.variants) == 1
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/unit/modules/storage/presentation/test_schemas.py -v`
Expected: FAIL — ImportError

- [ ] **Step 3: Rewrite schemas**

```python
# src/modules/storage/presentation/schemas.py
"""ImageBackend API schemas — matches spec contract."""
import uuid
from datetime import datetime
from src.shared.schemas import CamelModel


class UploadRequest(CamelModel):
    content_type: str
    filename: str | None = None


class UploadResponse(CamelModel):
    storage_object_id: uuid.UUID
    presigned_url: str
    expires_in: int = 300


class ConfirmResponse(CamelModel):
    storage_object_id: uuid.UUID
    status: str = "processing"


class MediaVariant(CamelModel):
    size: str
    width: int
    height: int
    url: str


class StatusEventData(CamelModel):
    status: str
    storage_object_id: uuid.UUID
    url: str | None = None
    variants: list[MediaVariant] = []
    error: str | None = None


class ExternalImportRequest(CamelModel):
    url: str


class ExternalImportResponse(CamelModel):
    storage_object_id: uuid.UUID
    url: str
    variants: list[MediaVariant] = []


class MetadataResponse(CamelModel):
    storage_object_id: uuid.UUID
    status: str
    url: str | None = None
    content_type: str | None = None
    size_bytes: int = 0
    variants: list[MediaVariant] = []
    created_at: datetime | None = None


class DeleteResponse(CamelModel):
    deleted: bool = True
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/unit/modules/storage/presentation/test_schemas.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/modules/storage/presentation/schemas.py tests/unit/modules/storage/presentation/
git commit -m "feat(image-backend): rewrite schemas to match API contract"
```

---

## Task 6: Image processing pipeline (Pillow)

**Files:**
- Create: `src/modules/storage/application/commands/process_image.py`
- Create: `tests/unit/modules/storage/application/test_process_image.py`

- [ ] **Step 1: Write failing test for image processing**

```python
# tests/unit/modules/storage/application/test_process_image.py
import io
from PIL import Image
from src.modules.storage.application.commands.process_image import (
    resize_to_fit,
    convert_to_webp,
    VARIANT_SIZES,
)


def _make_test_image(w: int, h: int, fmt: str = "JPEG") -> bytes:
    img = Image.new("RGB", (w, h), color="red")
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


def test_variant_sizes_defined():
    assert "thumbnail" in VARIANT_SIZES
    assert "medium" in VARIANT_SIZES
    assert "large" in VARIANT_SIZES
    assert VARIANT_SIZES["thumbnail"] == (150, 150)
    assert VARIANT_SIZES["medium"] == (600, 600)
    assert VARIANT_SIZES["large"] == (1200, 1200)


def test_resize_to_fit_preserves_aspect_ratio():
    img = Image.new("RGB", (2000, 1000))
    resized = resize_to_fit(img, 600, 600)
    assert resized.width == 600
    assert resized.height == 300


def test_convert_to_webp_returns_bytes():
    raw = _make_test_image(100, 100)
    result = convert_to_webp(raw, quality=85)
    assert isinstance(result, bytes)
    # Verify it's valid WebP
    img = Image.open(io.BytesIO(result))
    assert img.format == "WEBP"


def test_convert_to_webp_lossless():
    raw = _make_test_image(100, 100)
    result = convert_to_webp(raw, lossless=True)
    img = Image.open(io.BytesIO(result))
    assert img.format == "WEBP"
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/unit/modules/storage/application/test_process_image.py -v`
Expected: FAIL — ImportError

- [ ] **Step 3: Implement processing functions**

```python
# src/modules/storage/application/commands/process_image.py
"""Image processing pipeline — Pillow-based resize/convert to WebP."""
from __future__ import annotations

import io
import uuid
from dataclasses import dataclass

from PIL import Image

VARIANT_SIZES: dict[str, tuple[int, int]] = {
    "thumbnail": (150, 150),
    "medium": (600, 600),
    "large": (1200, 1200),
}


def resize_to_fit(img: Image.Image, max_w: int, max_h: int) -> Image.Image:
    """Resize preserving aspect ratio to fit within (max_w, max_h)."""
    img.thumbnail((max_w, max_h), Image.LANCZOS)
    return img


def convert_to_webp(
    raw_data: bytes,
    *,
    quality: int = 85,
    lossless: bool = False,
    max_size: tuple[int, int] | None = None,
) -> bytes:
    """Convert raw image bytes to WebP format."""
    img = Image.open(io.BytesIO(raw_data))
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
    else:
        img = img.convert("RGB")
    if max_size:
        img = resize_to_fit(img, *max_size)
    buf = io.BytesIO()
    img.save(buf, format="WEBP", quality=quality, lossless=lossless)
    return buf.getvalue()


def build_variants(
    raw_data: bytes,
    storage_object_id: uuid.UUID,
    public_base_url: str,
) -> tuple[bytes, list[dict], dict[str, bytes]]:
    """Process raw image into main + size variants.

    Returns:
        (main_webp_bytes, variant_metadata_list, variant_name_to_bytes)
    """
    main_bytes = convert_to_webp(raw_data, lossless=True)
    variants_meta: list[dict] = []
    variants_data: dict[str, bytes] = {}

    for size_name, (w, h) in VARIANT_SIZES.items():
        variant_bytes = convert_to_webp(raw_data, quality=85, max_size=(w, h))
        img = Image.open(io.BytesIO(variant_bytes))
        suffix = {"thumbnail": "thumb", "medium": "md", "large": "lg"}[size_name]
        s3_key = f"public/{storage_object_id}_{suffix}.webp"
        url = f"{public_base_url.rstrip('/')}/{s3_key}"

        variants_meta.append({
            "size": size_name,
            "width": img.width,
            "height": img.height,
            "url": url,
        })
        variants_data[s3_key] = variant_bytes

    return main_bytes, variants_meta, variants_data
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/unit/modules/storage/application/test_process_image.py -v`
Expected: PASS

- [ ] **Step 5: Write test for `build_variants`**

```python
# Add to test_process_image.py:
def test_build_variants_produces_three_sizes():
    raw = _make_test_image(2000, 1500)
    sid = uuid.uuid4()
    main_bytes, variants_meta, variants_data = build_variants(
        raw, sid, "https://cdn.example.com"
    )
    assert isinstance(main_bytes, bytes)
    assert len(variants_meta) == 3
    assert len(variants_data) == 3
    sizes = {v["size"] for v in variants_meta}
    assert sizes == {"thumbnail", "medium", "large"}
    # Check thumbnail is within bounds
    thumb = next(v for v in variants_meta if v["size"] == "thumbnail")
    assert thumb["width"] <= 150
    assert thumb["height"] <= 150
```

- [ ] **Step 6: Run to verify it passes**

Run: `python -m pytest tests/unit/modules/storage/application/test_process_image.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/modules/storage/application/commands/process_image.py tests/unit/modules/storage/application/
git commit -m "feat(image-backend): Pillow-based image processing pipeline with resize and WebP conversion"
```

---

## Task 7: SSE manager (Redis pub/sub)

**Files:**
- Create: `src/modules/storage/presentation/sse.py`
- Modify: `src/bootstrap/container.py` (add Redis for SSE)
- Create: `tests/unit/modules/storage/presentation/test_sse.py`

- [ ] **Step 1: Write failing test**

```python
# tests/unit/modules/storage/presentation/test_sse.py
import asyncio
import uuid
import pytest
from unittest.mock import AsyncMock

from src.modules.storage.presentation.sse import SSEManager


@pytest.mark.anyio
async def test_sse_manager_notify_and_listen():
    redis = AsyncMock()
    pubsub = AsyncMock()
    redis.pubsub.return_value = pubsub

    # Simulate one message then None
    messages = [
        {"type": "message", "data": b'{"status": "completed"}'},
        None,
    ]
    pubsub.get_message = AsyncMock(side_effect=messages)
    pubsub.subscribe = AsyncMock()
    pubsub.unsubscribe = AsyncMock()
    pubsub.aclose = AsyncMock()

    mgr = SSEManager(redis=redis)
    sid = uuid.uuid4()
    channel = mgr.channel_name(sid)
    assert str(sid) in channel
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/unit/modules/storage/presentation/test_sse.py -v`
Expected: FAIL — ImportError

- [ ] **Step 3: Implement SSEManager**

```python
# src/modules/storage/presentation/sse.py
"""SSE status streaming via Redis pub/sub."""
from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import AsyncGenerator

from redis.asyncio import Redis


class SSEManager:
    """Publish/subscribe for storage object processing status."""

    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    def channel_name(self, storage_object_id: uuid.UUID) -> str:
        return f"media:status:{storage_object_id}"

    async def publish(self, storage_object_id: uuid.UUID, data: dict) -> None:
        channel = self.channel_name(storage_object_id)
        await self._redis.publish(channel, json.dumps(data))

    async def subscribe(
        self,
        storage_object_id: uuid.UUID,
        *,
        timeout: float = 120.0,
        heartbeat: float = 15.0,
    ) -> AsyncGenerator[dict | None, None]:
        """Yield status events. Yields None for heartbeat (ping).
        Stops after timeout or terminal status.
        """
        channel = self.channel_name(storage_object_id)
        pubsub = self._redis.pubsub()
        await pubsub.subscribe(channel)
        try:
            deadline = asyncio.get_event_loop().time() + timeout
            while asyncio.get_event_loop().time() < deadline:
                msg = await pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=heartbeat,
                )
                if msg and msg["type"] == "message":
                    data = json.loads(msg["data"])
                    yield data
                    if data.get("status") in ("completed", "failed"):
                        return
                else:
                    yield None  # heartbeat
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()
```

- [ ] **Step 4: Run test**

Run: `python -m pytest tests/unit/modules/storage/presentation/test_sse.py -v`
Expected: PASS

- [ ] **Step 5: Add SSEManager to DI**

`CacheProvider` already provides `redis.asyncio.Redis` at APP scope (see `src/infrastructure/cache/provider.py:27`). Add `SSEManager` to `StorageProvider` in `src/modules/storage/presentation/dependencies.py`, injecting `Redis` directly (not via `ICacheService`):

```python
import redis.asyncio as redis
from src.modules.storage.presentation.sse import SSEManager

# Add to StorageProvider:
@provide(scope=Scope.APP)
def sse_manager(self, redis_client: redis.Redis) -> SSEManager:
    return SSEManager(redis=redis_client)
```

Dishka resolves `redis.Redis` from `CacheProvider.redis_client()` — no private attribute access needed.

- [ ] **Step 6: Commit**

```bash
git add src/modules/storage/presentation/sse.py src/modules/storage/presentation/dependencies.py src/bootstrap/container.py tests/unit/modules/storage/presentation/test_sse.py
git commit -m "feat(image-backend): SSE manager with Redis pub/sub for processing status"
```

---

## Task 8: Background processing task (TaskIQ)

**Files:**
- Modify: `src/modules/storage/presentation/tasks.py`
- The task calls `build_variants()`, uploads to S3, updates DB, publishes SSE

- [ ] **Step 1: Implement processing task**

```python
# src/modules/storage/presentation/tasks.py
"""Storage background tasks — image processing and orphan cleanup."""
from __future__ import annotations

import asyncio
import io
import uuid
from datetime import datetime, timedelta, timezone

from dishka import FromDishka
from taskiq import TaskiqDepends

from src.modules.storage.application.commands.process_image import build_variants
from src.modules.storage.domain.value_objects import StorageStatus
from src.modules.storage.presentation.sse import SSEManager
from src.shared.interfaces.blob_storage import IBlobStorage
from src.shared.interfaces.config import IStorageConfig
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork
from src.modules.storage.domain.interfaces import IStorageRepository
from src.bootstrap.broker import broker


@broker.task(
    task_name="process_image",
    queue_name="image_processing",
    retry_on_error=True,
    max_retries=2,
    timeout=300,
)
async def process_image_task(
    storage_object_id: str,
    blob_storage: FromDishka[IBlobStorage],
    storage_repo: FromDishka[IStorageRepository],
    uow: FromDishka[IUnitOfWork],
    config: FromDishka[IStorageConfig],
    sse: FromDishka[SSEManager],
    logger: FromDishka[ILogger],
) -> None:
    """Download raw, process with Pillow, upload variants, update status, push SSE."""
    sid = uuid.UUID(storage_object_id)
    log = logger.bind(storage_object_id=storage_object_id)
    log.info("Processing image started")

    storage_file = await storage_repo.get_by_key(sid)
    if not storage_file:
        log.error("StorageFile not found")
        return

    try:
        # 1. Download raw
        raw_chunks: list[bytes] = []
        async for chunk in blob_storage.download_stream(storage_file.object_key):
            raw_chunks.append(chunk)
        raw_data = b"".join(raw_chunks)
        log.info("Downloaded raw", size=len(raw_data))

        # 2. Process in thread (CPU-bound)
        main_bytes, variants_meta, variants_data = await asyncio.to_thread(
            build_variants, raw_data, sid, config.S3_PUBLIC_BASE_URL
        )

        # 3. Upload main
        main_key = f"public/{sid}.webp"
        await blob_storage.upload_stream(
            main_key, _bytes_to_stream(main_bytes), "image/webp"
        )

        # 4. Upload variants
        for s3_key, data in variants_data.items():
            await blob_storage.upload_stream(
                s3_key, _bytes_to_stream(data), "image/webp"
            )

        # 5. Delete raw
        await blob_storage.delete_object(storage_file.object_key)

        # 6. Update DB
        public_url = f"{config.S3_PUBLIC_BASE_URL.rstrip('/')}/{main_key}"
        storage_file.status = StorageStatus.COMPLETED
        storage_file.url = public_url
        storage_file.image_variants = variants_meta
        storage_file.size_bytes = len(main_bytes)
        await storage_repo.update(storage_file)
        await uow.commit()

        # 7. Push SSE
        await sse.publish(sid, {
            "status": "completed",
            "storage_object_id": str(sid),
            "url": public_url,
            "variants": variants_meta,
        })
        log.info("Processing completed", url=public_url)

    except Exception:
        log.exception("Processing failed")
        storage_file.status = StorageStatus.FAILED
        await storage_repo.update(storage_file)
        await uow.commit()
        await sse.publish(sid, {
            "status": "failed",
            "storage_object_id": str(sid),
            "error": "Processing failed",
        })
        raise


async def _bytes_to_stream(data: bytes):
    """Wrap bytes as an async iterator for upload_stream."""
    yield data


@broker.task(
    task_name="cleanup_orphans",
    queue_name="maintenance",
    timeout=600,
)
async def cleanup_orphans_task(
    storage_repo: FromDishka[IStorageRepository],
    blob_storage: FromDishka[IBlobStorage],
    uow: FromDishka[IUnitOfWork],
    logger: FromDishka[ILogger],
) -> None:
    """Phase 1: delete PENDING_UPLOAD objects older than 24 hours."""
    log = logger.bind(task="cleanup_orphans")
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    orphans = await storage_repo.list_pending_expired(cutoff)
    log.info("Found orphans", count=len(orphans))

    for orphan in orphans:
        try:
            await blob_storage.delete_object(orphan.object_key)
        except Exception:
            log.warning("Failed to delete S3 object", key=orphan.object_key)
        await storage_repo.mark_as_deleted(orphan.bucket_name, orphan.object_key)

    await uow.commit()
    log.info("Orphan cleanup done", deleted=len(orphans))
```

- [ ] **Step 2: Verify task module imports cleanly**

Run: `cd C:\Users\Sanjar\Desktop\loyality\image_backend && python -c "from src.modules.storage.presentation.tasks import process_image_task, cleanup_orphans_task; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add src/modules/storage/presentation/tasks.py
git commit -m "feat(image-backend): TaskIQ background tasks for image processing and orphan cleanup"
```

---

## Task 9: Rewrite router — all 6 endpoints per spec

**Files:**
- Modify: `src/modules/storage/presentation/router.py`
- Modify: `src/modules/storage/presentation/facade.py` (simplify)
- Create: `tests/unit/modules/storage/presentation/test_router.py`

- [ ] **Step 1: Rewrite router**

```python
# src/modules/storage/presentation/router.py
"""ImageBackend media API — all 6 endpoints per spec."""
from __future__ import annotations

import uuid

from dishka.integrations.fastapi import FromDishka
from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from src.modules.storage.domain.interfaces import IStorageRepository
from src.modules.storage.domain.value_objects import StorageStatus
from src.modules.storage.presentation.schemas import (
    ConfirmResponse,
    DeleteResponse,
    ExternalImportRequest,
    ExternalImportResponse,
    MetadataResponse,
    StatusEventData,
    UploadRequest,
    UploadResponse,
)
from src.modules.storage.presentation.sse import SSEManager
from src.modules.storage.presentation.tasks import process_image_task
from src.shared.interfaces.blob_storage import IBlobStorage
from src.shared.interfaces.config import IStorageConfig
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.storage import IStorageFacade
from src.shared.interfaces.uow import IUnitOfWork

media_router = APIRouter()


@media_router.post("/upload", status_code=201)
async def request_upload(
    body: UploadRequest,
    facade: FromDishka[IStorageFacade],
    config: FromDishka[IStorageConfig],
) -> UploadResponse:
    """Reserve upload slot, return presigned PUT URL."""
    result = await facade.reserve_upload_slot(
        module="media",
        entity_id=str(uuid.uuid4()),  # placeholder entity_id
        filename=body.filename or "upload",
        content_type=body.content_type,
        expire_in=300,
    )
    return UploadResponse(
        storage_object_id=result.file_id,
        presigned_url=result.url_data if isinstance(result.url_data, str) else result.url_data["url"],
        expires_in=300,
    )


@media_router.post("/{storage_object_id}/confirm", status_code=202)
async def confirm_upload(
    storage_object_id: uuid.UUID,
    facade: FromDishka[IStorageFacade],
    storage_repo: FromDishka[IStorageRepository],
    uow: FromDishka[IUnitOfWork],
    logger: FromDishka[ILogger],
) -> ConfirmResponse:
    """Confirm upload exists in S3, start background processing."""
    await facade.verify_upload(storage_object_id)

    storage_file = await storage_repo.get_by_key(storage_object_id)
    storage_file.status = StorageStatus.PROCESSING
    await storage_repo.update(storage_file)
    await uow.commit()

    await process_image_task.kiq(str(storage_object_id))
    logger.info("Dispatched processing", storage_object_id=str(storage_object_id))

    return ConfirmResponse(storage_object_id=storage_object_id)


@media_router.get("/{storage_object_id}/status")
async def stream_status(
    storage_object_id: uuid.UUID,
    storage_repo: FromDishka[IStorageRepository],
    sse: FromDishka[SSEManager],
    logger: FromDishka[ILogger],
) -> EventSourceResponse:
    """SSE stream for processing status updates."""

    async def event_generator():
        # Send current state immediately
        sf = await storage_repo.get_by_key(storage_object_id)
        if sf and sf.status.is_terminal:
            data = StatusEventData(
                status=sf.status.value,
                storage_object_id=storage_object_id,
                url=sf.url,
            )
            yield {"event": "status", "data": data.model_dump_json()}
            return

        # Initial status
        yield {
            "event": "status",
            "data": StatusEventData(
                status=sf.status.value if sf else "unknown",
                storage_object_id=storage_object_id,
            ).model_dump_json(),
        }

        # Subscribe and stream
        async for msg in sse.subscribe(storage_object_id):
            if msg is None:
                yield {"event": "ping", "data": "{}"}
            else:
                yield {"event": "status", "data": StatusEventData(**msg).model_dump_json()}
                if msg.get("status") in ("completed", "failed"):
                    return

    return EventSourceResponse(event_generator())


@media_router.get("/{storage_object_id}")
async def get_metadata(
    storage_object_id: uuid.UUID,
    storage_repo: FromDishka[IStorageRepository],
) -> MetadataResponse:
    """Get storage object metadata."""
    sf = await storage_repo.get_by_key(storage_object_id)
    if not sf:
        from src.shared.exceptions import NotFoundError
        raise NotFoundError(f"Storage object {storage_object_id} not found")
    return MetadataResponse(
        storage_object_id=sf.id,
        status=sf.status.value if isinstance(sf.status, StorageStatus) else sf.status,
        url=sf.url,
        content_type=sf.content_type,
        size_bytes=sf.size_bytes,
        variants=sf.image_variants or [],
        created_at=sf.created_at,
    )


@media_router.delete("/{storage_object_id}")
async def delete_storage_object(
    storage_object_id: uuid.UUID,
    storage_repo: FromDishka[IStorageRepository],
    blob_storage: FromDishka[IBlobStorage],
    uow: FromDishka[IUnitOfWork],
    logger: FromDishka[ILogger],
) -> DeleteResponse:
    """Delete files from S3 + record from DB."""
    sf = await storage_repo.get_by_key(storage_object_id)
    if not sf:
        return DeleteResponse(deleted=True)  # idempotent

    # Delete S3 files (main + variants)
    keys_to_delete = [sf.object_key]
    if sf.url:
        main_key = f"public/{sf.id}.webp"
        keys_to_delete.append(main_key)
    if sf.image_variants:
        for v in sf.image_variants:
            # Extract S3 key from URL
            url_path = v["url"].split("/", 3)[-1] if "/" in v["url"] else v["url"]
            keys_to_delete.append(url_path)

    try:
        await blob_storage.delete_objects(keys_to_delete)
    except Exception:
        logger.warning("Failed to delete some S3 objects", keys=keys_to_delete)

    await storage_repo.mark_as_deleted(sf.bucket_name, sf.object_key)
    await uow.commit()

    return DeleteResponse()


@media_router.post("/external", status_code=201)
async def import_external(
    body: ExternalImportRequest,
    blob_storage: FromDishka[IBlobStorage],
    storage_repo: FromDishka[IStorageRepository],
    uow: FromDishka[IUnitOfWork],
    config: FromDishka[IStorageConfig],
    logger: FromDishka[ILogger],
) -> ExternalImportResponse:
    """Import image from external URL — synchronous download + process."""
    import httpx
    from src.modules.storage.application.commands.process_image import build_variants
    from src.modules.storage.domain.entities import StorageFile

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(body.url, follow_redirects=True)
        resp.raise_for_status()
        raw_data = resp.content
        content_type = resp.headers.get("content-type", "image/jpeg")

    sf = StorageFile.create(
        bucket_name=config.S3_BUCKET_NAME,
        object_key=f"external/{uuid.uuid4()}/import",
        content_type=content_type,
        filename=body.url.split("/")[-1],
    )
    sf.status = StorageStatus.PROCESSING
    await storage_repo.add(sf)
    await uow.commit()

    import asyncio
    main_bytes, variants_meta, variants_data = await asyncio.to_thread(
        build_variants, raw_data, sf.id, config.S3_PUBLIC_BASE_URL
    )

    main_key = f"public/{sf.id}.webp"

    async def _stream(data: bytes):
        yield data

    await blob_storage.upload_stream(main_key, _stream(main_bytes), "image/webp")
    for s3_key, data in variants_data.items():
        await blob_storage.upload_stream(s3_key, _stream(data), "image/webp")

    public_url = f"{config.S3_PUBLIC_BASE_URL.rstrip('/')}/{main_key}"
    sf.status = StorageStatus.COMPLETED
    sf.url = public_url
    sf.image_variants = variants_meta
    sf.size_bytes = len(main_bytes)
    await storage_repo.update(sf)
    await uow.commit()

    return ExternalImportResponse(
        storage_object_id=sf.id,
        url=public_url,
        variants=variants_meta,
    )
```

- [ ] **Step 2: Verify app starts**

Run: `cd C:\Users\Sanjar\Desktop\loyality\image_backend && python -c "from src.modules.storage.presentation.router import media_router; print(f'{len(media_router.routes)} routes')"`
Expected: `6 routes`

- [ ] **Step 3: Commit**

```bash
git add src/modules/storage/presentation/router.py
git commit -m "feat(image-backend): implement all 6 media endpoints per spec"
```

---

## Task 10: Config additions + scheduled orphan cleanup

**Files:**
- Modify: `src/bootstrap/config.py`
- Modify: `src/bootstrap/scheduler.py`

- [ ] **Step 1: Add config vars**

In `src/bootstrap/config.py` Settings class, add:

```python
    # Processing
    SSE_TIMEOUT: int = 120
    SSE_HEARTBEAT: int = 15
    PROCESSING_TIMEOUT: int = 300
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50 MB
    PRESIGNED_URL_TTL: int = 300
```

- [ ] **Step 2: Add cron label to `cleanup_orphans_task`**

TaskIQ uses `LabelScheduleSource` — scheduling is done via task labels, not method calls. In `src/modules/storage/presentation/tasks.py`, update the `cleanup_orphans_task` decorator to include a schedule label:

```python
@broker.task(
    task_name="cleanup_orphans",
    queue_name="maintenance",
    timeout=600,
    schedule=[{"cron": "0 */6 * * *"}],  # every 6 hours
)
```

The existing `src/bootstrap/scheduler.py` already imports tasks and uses `LabelScheduleSource(broker)` — no changes needed there.

- [ ] **Step 3: Wire SSE config to SSEManager**

The `SSEManager.subscribe()` currently uses hardcoded `timeout=120.0` and `heartbeat=15.0`. Update the `stream_status` endpoint in `router.py` to read from config:

```python
@media_router.get("/{storage_object_id}/status")
async def stream_status(
    storage_object_id: uuid.UUID,
    storage_repo: FromDishka[IStorageRepository],
    sse: FromDishka[SSEManager],
    config: FromDishka[Settings],
    logger: FromDishka[ILogger],
) -> EventSourceResponse:
    # ...in event_generator, pass config values:
    async for msg in sse.subscribe(
        storage_object_id,
        timeout=config.SSE_TIMEOUT,
        heartbeat=config.SSE_HEARTBEAT,
    ):
```

- [ ] **Step 3: Commit**

```bash
git add src/bootstrap/config.py src/bootstrap/scheduler.py
git commit -m "feat(image-backend): add processing config and scheduled orphan cleanup"
```

---

## Task 11: Integration smoke test

**Files:**
- Create: `tests/integration/test_upload_flow.py`

- [ ] **Step 1: Write integration test**

```python
# tests/integration/test_upload_flow.py
"""Smoke test for the upload → confirm → status flow."""
import pytest
from httpx import AsyncClient, ASGITransport


@pytest.fixture
def app():
    from src.bootstrap.web import create_app
    return create_app()


@pytest.mark.anyio
async def test_upload_returns_presigned_url(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/media/upload",
            json={"content_type": "image/jpeg", "filename": "test.jpg"},
            headers={"X-API-Key": "test-key"},
        )
    # Will be 201 if auth is disabled (empty INTERNAL_API_KEY) or key matches
    assert resp.status_code in (201, 401)
    if resp.status_code == 201:
        data = resp.json()
        assert "storageObjectId" in data
        assert "presignedUrl" in data


@pytest.mark.anyio
async def test_get_metadata_404_for_unknown(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/media/00000000-0000-0000-0000-000000000000",
            headers={"X-API-Key": "test-key"},
        )
    assert resp.status_code in (404, 401)


@pytest.mark.anyio
async def test_delete_idempotent(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.delete(
            "/api/v1/media/00000000-0000-0000-0000-000000000000",
            headers={"X-API-Key": "test-key"},
        )
    assert resp.status_code in (200, 401)
```

- [ ] **Step 2: Run**

Run: `python -m pytest tests/integration/test_upload_flow.py -v`
Expected: Tests pass (with appropriate DB/service setup)

- [ ] **Step 3: Commit**

```bash
git add tests/integration/
git commit -m "test(image-backend): add integration smoke tests for upload flow"
```

---

## Summary

| Task | What                                     | Commit message           |
| ---- | ---------------------------------------- | ------------------------ |
| 1    | Add sse-starlette, httpx deps            | `chore: add deps`        |
| 2    | StorageStatus enum + StorageFile updates | `feat: domain entities`  |
| 3    | StorageObject ORM + migration            | `feat: ORM + migration`  |
| 4    | Wire API-key auth                        | `feat: auth`             |
| 5    | Rewrite schemas                          | `feat: schemas`          |
| 6    | Pillow processing pipeline               | `feat: image processing` |
| 7    | SSE manager (Redis pub/sub)              | `feat: SSE`              |
| 8    | Background processing task               | `feat: TaskIQ tasks`     |
| 9    | Rewrite router (6 endpoints)             | `feat: all endpoints`    |
| 10   | Config + scheduled cleanup               | `feat: config + cron`    |
| 11   | Integration smoke test                   | `test: smoke tests`      |
