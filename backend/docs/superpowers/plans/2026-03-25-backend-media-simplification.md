# Backend Media Simplification Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Strip all S3/storage/FSM/processing logic from Backend. Backend stores only URLs and metadata — `MediaAsset` becomes a simple dataclass, `Brand` loses its logo FSM, and a new `ImageBackendClient` handles server-to-server DELETE calls.

**Architecture:** Backend no longer touches S3 directly. Product create/update accepts a `media[]` array of pre-processed URLs from Frontend. Brand accepts `logo_url` + `logo_storage_object_id`. Deletion triggers a best-effort HTTP DELETE to ImageBackend via `ImageBackendClient`. The entire `src/modules/storage/` module is deleted, along with all S3 interfaces, factory, env vars, media command handlers, and internal webhook router.

**Tech Stack:** FastAPI, SQLAlchemy 2.1 (async), httpx (for ImageBackendClient), Dishka DI, Alembic, pytest

**Spec:** `docs/superpowers/specs/2026-03-25-media-architecture-split-design.md`

**Working directory:** `C:\Users\Sanjar\Desktop\loyality\backend`

**Dependency:** Can be developed independently of the ImageBackend plan. The `ImageBackendClient.delete()` is best-effort and works even when ImageBackend is not yet deployed (just logs warning).

**JSON serialization:** All schemas extend `CamelModel` which auto-converts `snake_case` → `camelCase` in JSON. The spec shows snake_case for readability, but the actual API returns camelCase (e.g., `storageObjectId`, `imageVariants`). This matches existing Backend convention.

---

## File Structure

### Delete entirely
| File/Directory                                                           | Why                                                              |
| ------------------------------------------------------------------------ | ---------------------------------------------------------------- |
| `src/modules/storage/`                                                   | Entire storage module — now lives in ImageBackend                |
| `src/shared/interfaces/blob_storage.py`                                  | `IBlobStorage` — no more S3 from Backend                         |
| `src/shared/interfaces/storage.py`                                       | `IStorageFacade`, `PresignedUploadData` — no more presigned URLs |
| `src/shared/interfaces/config.py` → remove `IStorageConfig`              | S3 config protocol — no more S3                                  |
| `src/infrastructure/storage/factory.py`                                  | `S3ClientFactory` — no more S3                                   |
| `src/modules/catalog/application/commands/add_product_media.py`          | Old presigned upload flow                                        |
| `src/modules/catalog/application/commands/add_external_product_media.py` | Old external media flow                                          |
| `src/modules/catalog/application/commands/confirm_product_media.py`      | Old confirm FSM transition                                       |
| `src/modules/catalog/application/commands/complete_product_media.py`     | Old processing complete/fail                                     |
| `src/modules/catalog/application/commands/confirm_brand_logo.py`         | Old brand logo confirm                                           |
| `src/modules/catalog/application/services/media_processor.py`            | `BrandLogoProcessor` — processing moves to ImageBackend          |
| `src/modules/catalog/application/constants.py`                           | S3 key builders — no more S3                                     |
| `src/modules/catalog/application/tasks.py`                               | `process_brand_logo_task` — processing moves to ImageBackend     |
| `src/modules/catalog/presentation/router_product_media.py`               | Old media upload/confirm/delete endpoints                        |
| `src/modules/catalog/presentation/router_internal.py`                    | Internal webhook endpoints — no more processing callbacks        |

### Create
| File                                                                     | Responsibility                                                                    |
| ------------------------------------------------------------------------ | --------------------------------------------------------------------------------- |
| `src/modules/catalog/infrastructure/image_backend_client.py`             | `ImageBackendClient` — httpx HTTP client, `delete(storage_object_id)`             |
| `src/modules/catalog/presentation/schemas_media.py`                      | `MediaItemRequest`, `MediaItemResponse` — schemas for media[] in product payloads |
| `tests/unit/modules/catalog/infrastructure/test_image_backend_client.py` | Tests for ImageBackendClient                                                      |
| `tests/unit/modules/catalog/application/test_sync_product_media.py`      | Tests for media full-replace diff logic                                           |
| `alembic/versions/2026/03/25_simplify_media.py`                          | Migration: DROP columns, DROP table, ADD columns                                  |

### Modify
| File                                                               | What changes                                                                                                                                                                    |
| ------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/modules/catalog/domain/entities.py`                           | Simplify `MediaAsset` (remove AggregateRoot, FSM, events). Simplify `Brand` (remove logo FSM)                                                                                   |
| `src/modules/catalog/domain/value_objects.py`                      | Remove `MediaProcessingStatus` enum                                                                                                                                             |
| `src/modules/catalog/domain/events.py`                             | Remove 5 media/logo events                                                                                                                                                      |
| `src/modules/catalog/domain/interfaces.py`                         | Simplify `IMediaAssetRepository` (remove `count_pending_uploads`, simplify `has_main_for_variant`)                                                                              |
| `src/modules/catalog/infrastructure/models.py`                     | Simplify `MediaAsset` ORM (remove 4 columns, add `image_variants`, fix partial index). Simplify `Brand` ORM (remove `logo_status`/`logo_file_id`, add `logo_storage_object_id`) |
| `src/modules/catalog/infrastructure/repositories/media_asset.py`   | Simplify mapper, remove `count_pending_uploads`, simplify `has_main_for_variant`                                                                                                |
| `src/modules/catalog/application/commands/create_product.py`       | Accept `media[]` in command, create MediaAssets                                                                                                                                 |
| `src/modules/catalog/application/commands/update_product.py`       | Accept `media[]` in command, full-replace diff                                                                                                                                  |
| `src/modules/catalog/application/commands/create_brand.py`         | Accept `logo_url` + `logo_storage_object_id` instead of `LogoMetadata`                                                                                                          |
| `src/modules/catalog/application/commands/delete_product_media.py` | Simplify — delete record + call `ImageBackendClient.delete()`                                                                                                                   |
| `src/modules/catalog/presentation/schemas.py`                      | Remove old media schemas, update `BrandCreateRequest`                                                                                                                           |
| `src/modules/catalog/presentation/dependencies.py`                 | Remove `MediaAssetProvider`, add `ImageBackendClient` to DI                                                                                                                     |
| `src/modules/catalog/presentation/router_brands.py`                | Remove `/logo/confirm`, update create to accept `logo_url`                                                                                                                      |
| `src/bootstrap/config.py`                                          | Remove S3 vars, add `IMAGE_BACKEND_URL`, `IMAGE_BACKEND_API_KEY`                                                                                                                |
| `src/bootstrap/container.py`                                       | Remove `StorageProvider`, `MediaAssetProvider`. Add `ImageBackendClient`                                                                                                        |

---

## Task 1: Add `IMAGE_BACKEND_URL` / `IMAGE_BACKEND_API_KEY` to config, remove S3 vars

**Files:**
- Modify: `src/bootstrap/config.py`

- [ ] **Step 1: Read current config**

Read `src/bootstrap/config.py` to see exact line numbers for S3 vars (lines 98-104).

- [ ] **Step 2: Remove S3 vars, add ImageBackend vars**

Remove lines 98-104 (`S3_ENDPOINT_URL`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_REGION`, `S3_BUCKET_NAME`, `S3_PUBLIC_BASE_URL`).

Add:
```python
    # ImageBackend (server-to-server)
    IMAGE_BACKEND_URL: str = "http://localhost:8001"
    IMAGE_BACKEND_API_KEY: SecretStr = SecretStr("")
```

Keep `INTERNAL_WEBHOOK_SECRET` for now (will be removed with router_internal.py later).

- [ ] **Step 3: Update `.env.example` if it exists**

Replace S3 vars with `IMAGE_BACKEND_URL` and `IMAGE_BACKEND_API_KEY`.

- [ ] **Step 4: Commit**

```bash
git add src/bootstrap/config.py
git commit -m "chore(backend): replace S3 config with IMAGE_BACKEND_URL/API_KEY"
```

---

## Task 2: Create `ImageBackendClient`

**Files:**
- Create: `src/modules/catalog/infrastructure/image_backend_client.py`
- Create: `tests/unit/modules/catalog/infrastructure/test_image_backend_client.py`

- [ ] **Step 1: Write failing test**

```python
# tests/unit/modules/catalog/infrastructure/test_image_backend_client.py
import uuid
import pytest
from unittest.mock import AsyncMock, patch

from src.modules.catalog.infrastructure.image_backend_client import ImageBackendClient


@pytest.mark.anyio
async def test_delete_sends_request():
    client = ImageBackendClient(
        base_url="http://image-backend:8001",
        api_key="test-key",
    )
    sid = uuid.uuid4()

    with patch("httpx.AsyncClient.delete", new_callable=AsyncMock) as mock_delete:
        mock_delete.return_value = AsyncMock(status_code=200)
        await client.delete(sid)

    mock_delete.assert_called_once()
    call_url = mock_delete.call_args[0][0]
    assert str(sid) in call_url


@pytest.mark.anyio
async def test_delete_best_effort_on_error():
    """delete() should not raise even if ImageBackend is unavailable."""
    client = ImageBackendClient(
        base_url="http://unreachable:9999",
        api_key="test-key",
    )
    sid = uuid.uuid4()

    with patch("httpx.AsyncClient.delete", new_callable=AsyncMock, side_effect=Exception("connection refused")):
        # Should NOT raise
        await client.delete(sid)
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/unit/modules/catalog/infrastructure/test_image_backend_client.py -v`
Expected: FAIL — ImportError

- [ ] **Step 3: Implement ImageBackendClient**

```python
# src/modules/catalog/infrastructure/image_backend_client.py
"""HTTP client for server-to-server calls to ImageBackend."""
from __future__ import annotations

import uuid

import httpx
import structlog

logger = structlog.get_logger()


class ImageBackendClient:
    """Best-effort DELETE calls to ImageBackend.

    Does NOT raise on failure — orphan cleanup on ImageBackend side
    handles files that fail to delete.
    """

    def __init__(self, base_url: str, api_key: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key

    async def delete(self, storage_object_id: uuid.UUID) -> None:
        """DELETE /api/v1/media/{storage_object_id}. Best-effort."""
        url = f"{self._base_url}/api/v1/media/{storage_object_id}"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.delete(
                    url,
                    headers={"X-API-Key": self._api_key},
                )
                if resp.status_code not in (200, 404):
                    logger.warning(
                        "ImageBackend delete non-OK",
                        status=resp.status_code,
                        storage_object_id=str(storage_object_id),
                    )
        except Exception:
            logger.warning(
                "ImageBackend delete failed (best-effort)",
                storage_object_id=str(storage_object_id),
                exc_info=True,
            )
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/unit/modules/catalog/infrastructure/test_image_backend_client.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/modules/catalog/infrastructure/image_backend_client.py tests/unit/modules/catalog/infrastructure/
git commit -m "feat(backend): add ImageBackendClient for server-to-server DELETE"
```

---

## Task 3: Simplify `MediaAsset` domain entity

**Files:**
- Modify: `src/modules/catalog/domain/entities.py` (lines 1610-1831)
- Modify: `src/modules/catalog/domain/value_objects.py` (remove `MediaProcessingStatus`)

- [ ] **Step 1: Read current MediaAsset entity**

Read `src/modules/catalog/domain/entities.py` lines 1610-1831.

- [ ] **Step 2: Replace MediaAsset class**

Remove the entire `MediaAsset` class (lines 1610-1831) and replace with:

Use attrs `@define` to match codebase convention (other domain entities like `StorageFile`, `Brand`, `Product` all use attrs):

```python
from attrs import define

@define
class MediaAsset:
    """Simple data record for a product media asset.

    No AggregateRoot, no FSM, no domain events.
    Binding to a product/variant is the responsibility of the catalog layer.
    Physical files live in ImageBackend (referenced by storage_object_id).
    """

    id: uuid.UUID
    product_id: uuid.UUID
    variant_id: uuid.UUID | None

    media_type: str          # IMAGE, VIDEO, MODEL_3D, DOCUMENT
    role: str                # MAIN, HOVER, GALLERY, HERO_VIDEO, SIZE_GUIDE, PACKAGING
    sort_order: int
    is_external: bool = False

    storage_object_id: uuid.UUID | None = None
    url: str | None = None
    image_variants: list[dict] | None = None

    created_at: datetime | None = None
    updated_at: datetime | None = None
```

- [ ] **Step 3: Remove `MediaProcessingStatus` from value_objects.py**

Read `src/modules/catalog/domain/value_objects.py` and remove the `MediaProcessingStatus` enum (lines 111-127).

- [ ] **Step 4: Remove media domain events from events.py**

Read `src/modules/catalog/domain/events.py` and remove:
- `BrandLogoUploadInitiatedEvent` (lines 94-116)
- `BrandLogoConfirmedEvent` (lines 118-135)
- `BrandLogoProcessedEvent` (lines 138-161)
- `ProductMediaConfirmedEvent` (lines 520-533)
- `ProductMediaProcessedEvent` (lines 536-550)

- [ ] **Step 5: Verify imports don't break**

Run: `python -c "from src.modules.catalog.domain.entities import MediaAsset; print(MediaAsset.__dataclass_fields__.keys())"`
Expected: prints field names

- [ ] **Step 6: Commit**

```bash
git add src/modules/catalog/domain/entities.py src/modules/catalog/domain/value_objects.py src/modules/catalog/domain/events.py
git commit -m "refactor(backend): simplify MediaAsset to plain dataclass, remove FSM/events"
```

---

## Task 4: Simplify `Brand` entity — remove logo FSM

**Files:**
- Modify: `src/modules/catalog/domain/entities.py` (lines 142-367)

- [ ] **Step 1: Read current Brand entity**

Read `src/modules/catalog/domain/entities.py` lines 142-367.

- [ ] **Step 2: Simplify Brand**

Replace logo-related fields and remove all 5 logo FSM methods. The Brand class should have:

```python
# Replace these fields:
#   logo_status: MediaProcessingStatus | None = None
#   logo_file_id: uuid.UUID | None = None
#   logo_url: str | None = None
# With:
    logo_url: str | None = None
    logo_storage_object_id: uuid.UUID | None = None
```

Remove methods: `init_logo_upload()`, `confirm_logo_upload()`, `complete_logo_processing()`, `fail_logo_processing()`, `retry_logo_upload()`.

Update `create()` factory to accept `logo_url` and `logo_storage_object_id` instead of `logo_file_id` and `logo_status`.

Update `update()` to allow updating `logo_url` and `logo_storage_object_id`.

- [ ] **Step 3: Verify**

Run: `python -c "from src.modules.catalog.domain.entities import Brand; b = Brand.__dataclass_fields__; print([k for k in b if 'logo' in k])"`
Expected: `['logo_url', 'logo_storage_object_id']`

- [ ] **Step 4: Commit**

```bash
git add src/modules/catalog/domain/entities.py
git commit -m "refactor(backend): simplify Brand entity — remove logo FSM, keep logo_url + logo_storage_object_id"
```

---

## Task 5: Simplify `IMediaAssetRepository` interface

**Files:**
- Modify: `src/modules/catalog/domain/interfaces.py` (lines 382-435)

- [ ] **Step 1: Read current interface**

Read `src/modules/catalog/domain/interfaces.py` lines 382-435.

- [ ] **Step 2: Simplify interface**

Remove:
- `count_pending_uploads(product_id)` — no more pending state
- Simplify `has_main_for_variant(product_id, variant_id)` — remove processing_status check

Add:
- `list_by_storage_ids(storage_object_ids: list[uuid.UUID]) -> list[DomainMediaAsset]` — needed for full-replace diff
- `delete_by_product(product_id) -> list[uuid.UUID]` — bulk delete, returns storage_object_ids for ImageBackend cleanup

- [ ] **Step 3: Commit**

```bash
git add src/modules/catalog/domain/interfaces.py
git commit -m "refactor(backend): simplify IMediaAssetRepository — remove status-aware methods"
```

---

## Task 6: Simplify ORM models + Alembic migration

**Files:**
- Modify: `src/modules/catalog/infrastructure/models.py`
- Create: Alembic migration

- [ ] **Step 1: Simplify MediaAsset ORM** (lines 687-786)

Remove columns: `processing_status`, `raw_object_key`, `processed_object_key`, `external_url`.
Rename `public_url` → `url` (if not already).
Add column: `image_variants` (JSONB, nullable).
Fix partial index: remove `AND processing_status != 'FAILED'` condition.

- [ ] **Step 2: Simplify Brand ORM** (lines 55-107)

Remove columns: `logo_status`, `logo_file_id`.
Add column: `logo_storage_object_id` (UUID, nullable, indexed).

- [ ] **Step 3: Remove StorageObject ORM from model registry BEFORE generating migration**

Alembic autogenerate won't detect DROP TABLE if the ORM model still exists. Remove the import from the registry file so autogenerate sees the table is "extra":

In `src/infrastructure/database/registry.py` (or wherever Backend imports `StorageObject` for Alembic), remove/comment out the `StorageObject` import. Also delete `src/modules/storage/infrastructure/models.py` now (the full storage module deletion happens in Task 12, but the ORM model must go before autogenerate).

```bash
rm src/modules/storage/infrastructure/models.py
```

Edit the registry to remove `from src.modules.storage.infrastructure.models import StorageObject`.

- [ ] **Step 4: Generate migration**

Run: `alembic revision --autogenerate -m "simplify media_assets and brands for image backend split"`

- [ ] **Step 5: Review migration**

Verify it contains:
- DROP COLUMN `processing_status`, `raw_object_key`, `processed_object_key`, `external_url` from `media_assets`
- ADD COLUMN `image_variants` JSONB to `media_assets`
- DROP INDEX `uix_media_single_main_per_variant`, recreate without processing_status condition
- DROP COLUMN `logo_status`, `logo_file_id` from `brands`
- ADD COLUMN `logo_storage_object_id` UUID to `brands`
- DROP TABLE `storage_objects`

**Important:** If autogenerate misses the DROP TABLE, manually add `op.drop_table('storage_objects')` and corresponding enum drops to the migration.

- [ ] **Step 5: Run migration**

Run: `alembic upgrade head`

- [ ] **Step 6: Commit**

```bash
git add src/modules/catalog/infrastructure/models.py alembic/
git commit -m "refactor(backend): simplify MediaAsset/Brand ORM, drop storage_objects table"
```

---

## Task 7: Simplify `MediaAssetRepository`

**Files:**
- Modify: `src/modules/catalog/infrastructure/repositories/media_asset.py`

- [ ] **Step 1: Read current repo**

Read `src/modules/catalog/infrastructure/repositories/media_asset.py`.

- [ ] **Step 2: Update mapper `_to_domain`**

Remove `processing_status`, `raw_object_key`, `processed_object_key`, `external_url` mappings.
Add `image_variants` mapping.
Rename `public_url` → `url`.

- [ ] **Step 3: Update mapper `_to_orm`**

Same field changes as domain mapper.

- [ ] **Step 4: Remove `count_pending_uploads`**

Delete the method (lines 182-189).

- [ ] **Step 5: Simplify `has_main_for_variant`**

Remove the `processing_status != FAILED` condition from the query (lines 162-180).

- [ ] **Step 6: Add `list_by_storage_ids` and `delete_by_product`**

```python
async def list_by_storage_ids(
    self, storage_object_ids: list[uuid.UUID],
) -> list[DomainMediaAsset]:
    stmt = select(MediaAsset).where(
        MediaAsset.storage_object_id.in_(storage_object_ids)
    )
    result = await self._session.execute(stmt)
    return [self._to_domain(row) for row in result.scalars().all()]

async def delete_by_product(self, product_id: uuid.UUID) -> list[uuid.UUID]:
    """Delete all media for product, return storage_object_ids for cleanup."""
    stmt = select(MediaAsset).where(MediaAsset.product_id == product_id)
    result = await self._session.execute(stmt)
    orms = result.scalars().all()
    sids = [orm.storage_object_id for orm in orms if orm.storage_object_id]
    for orm in orms:
        await self._session.delete(orm)
    return sids
```

- [ ] **Step 7: Commit**

```bash
git add src/modules/catalog/infrastructure/repositories/media_asset.py
git commit -m "refactor(backend): simplify MediaAssetRepository — remove FSM queries, add bulk ops"
```

---

## Task 8: Media schemas for product create/update

**Files:**
- Create: `src/modules/catalog/presentation/schemas_media.py`

- [ ] **Step 1: Create media item schemas**

```python
# src/modules/catalog/presentation/schemas_media.py
"""Schemas for media[] array in product create/update payloads."""
from __future__ import annotations

import uuid

from pydantic import field_validator

from src.shared.schemas import CamelModel


class ImageVariantItem(CamelModel):
    size: str
    width: int
    height: int
    url: str


class MediaItemRequest(CamelModel):
    url: str
    storage_object_id: uuid.UUID | None = None
    media_type: str = "IMAGE"
    role: str = "GALLERY"
    variant_id: uuid.UUID | None = None
    sort_order: int = 0
    is_external: bool = False
    image_variants: list[ImageVariantItem] | None = None

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if len(v) > 1024:
            msg = "URL must be <= 1024 characters"
            raise ValueError(msg)
        return v

    @field_validator("storage_object_id")
    @classmethod
    def require_storage_id_for_internal(cls, v, info):
        if not info.data.get("is_external") and v is None:
            msg = "storage_object_id required when is_external=false"
            raise ValueError(msg)
        return v


class MediaItemResponse(CamelModel):
    id: uuid.UUID
    product_id: uuid.UUID
    variant_id: uuid.UUID | None = None
    media_type: str
    role: str
    sort_order: int
    is_external: bool
    storage_object_id: uuid.UUID | None = None
    url: str | None = None
    image_variants: list[ImageVariantItem] | None = None
```

- [ ] **Step 2: Commit**

```bash
git add src/modules/catalog/presentation/schemas_media.py
git commit -m "feat(backend): add media item schemas for product create/update payloads"
```

---

## Task 9: Update product create/update to accept `media[]`

**Files:**
- Modify: `src/modules/catalog/application/commands/create_product.py`
- Modify: `src/modules/catalog/application/commands/update_product.py`
- Create: `tests/unit/modules/catalog/application/test_sync_product_media.py`

- [ ] **Step 1: Write failing test for media sync logic**

```python
# tests/unit/modules/catalog/application/test_sync_product_media.py
from src.modules.catalog.application.commands.update_product import compute_media_diff


def test_compute_diff_new_items():
    current = []
    incoming = [{"storage_object_id": "aaa", "url": "https://cdn/a.webp", "role": "MAIN"}]
    to_add, to_update, to_delete = compute_media_diff(current, incoming)
    assert len(to_add) == 1
    assert len(to_update) == 0
    assert len(to_delete) == 0


def test_compute_diff_delete_removed():
    current = [{"storage_object_id": "aaa", "id": "m1"}]
    incoming = []
    to_add, to_update, to_delete = compute_media_diff(current, incoming)
    assert len(to_delete) == 1
    assert to_delete[0]["storage_object_id"] == "aaa"


def test_compute_diff_update_changed_role():
    current = [{"storage_object_id": "aaa", "id": "m1", "role": "GALLERY"}]
    incoming = [{"storage_object_id": "aaa", "role": "MAIN"}]
    to_add, to_update, to_delete = compute_media_diff(current, incoming)
    assert len(to_update) == 1
    assert to_update[0]["role"] == "MAIN"
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/unit/modules/catalog/application/test_sync_product_media.py -v`
Expected: FAIL — ImportError

- [ ] **Step 3: Add `media` field to `CreateProductCommand`**

```python
# In create_product.py, add to CreateProductCommand:
    media: list[dict] | None = None  # [{url, storage_object_id, media_type, role, ...}]
```

In `CreateProductHandler.handle()`, after creating the product and committing, create `MediaAsset` records from the `media` array:

```python
if command.media:
    for item in command.media:
        media_asset = MediaAsset(
            id=uuid.uuid7(),
            product_id=product.id,
            variant_id=item.get("variant_id"),
            media_type=item.get("media_type", "IMAGE"),
            role=item.get("role", "GALLERY"),
            sort_order=item.get("sort_order", 0),
            is_external=item.get("is_external", False),
            storage_object_id=item.get("storage_object_id"),
            url=item.get("url"),
            image_variants=item.get("image_variants"),
        )
        await self._media_repo.add(media_asset)
```

- [ ] **Step 4: Add `media` field to `UpdateProductCommand` with diff logic**

In `UpdateProductHandler.handle()`, convert existing domain entities to dicts before calling `compute_media_diff`:

```python
# In the handler, after locking the product:
if command.media is not None:
    existing = await self._media_repo.list_by_product(command.product_id)
    current_dicts = [
        {
            "id": str(m.id),
            "storage_object_id": str(m.storage_object_id) if m.storage_object_id else None,
            "url": m.url,
            "role": m.role,
            "sort_order": m.sort_order,
            "variant_id": str(m.variant_id) if m.variant_id else None,
            "is_external": m.is_external,
        }
        for m in existing
    ]
    to_add, to_update, to_delete = compute_media_diff(current_dicts, command.media)

    for item in to_delete:
        sid = item.get("storage_object_id")
        mid = uuid.UUID(item["id"])
        await self._media_repo.delete(mid)
        if sid:
            await self._image_backend.delete(uuid.UUID(sid))

    for item in to_update:
        media = await self._media_repo.get(uuid.UUID(item["id"]))
        media.role = item["role"]
        media.sort_order = item["sort_order"]
        media.variant_id = uuid.UUID(item["variant_id"]) if item.get("variant_id") else None
        await self._media_repo.update(media)

    for item in to_add:
        media_asset = MediaAsset(
            id=uuid.uuid7(), product_id=command.product_id,
            variant_id=uuid.UUID(item["variant_id"]) if item.get("variant_id") else None,
            media_type=item.get("media_type", "IMAGE"),
            role=item.get("role", "GALLERY"),
            sort_order=item.get("sort_order", 0),
            is_external=item.get("is_external", False),
            storage_object_id=uuid.UUID(item["storage_object_id"]) if item.get("storage_object_id") else None,
            url=item.get("url"),
            image_variants=item.get("image_variants"),
        )
        await self._media_repo.add(media_asset)
```

The `compute_media_diff` helper works with dicts (serialized form from both DB entities and incoming request):

```python
# In update_product.py, add helper function:
def compute_media_diff(
    current: list[dict],
    incoming: list[dict],
) -> tuple[list[dict], list[dict], list[dict]]:
    """Full-replace diff for media arrays.

    Returns: (to_add, to_update, to_delete)
    """
    current_by_sid = {
        c["storage_object_id"]: c for c in current if c.get("storage_object_id")
    }
    incoming_by_sid = {
        i["storage_object_id"]: i for i in incoming if i.get("storage_object_id")
    }

    to_add = [i for sid, i in incoming_by_sid.items() if sid not in current_by_sid]
    to_delete = [c for sid, c in current_by_sid.items() if sid not in incoming_by_sid]
    to_update = []
    for sid in incoming_by_sid:
        if sid in current_by_sid:
            inc = incoming_by_sid[sid]
            cur = current_by_sid[sid]
            if any(inc.get(k) != cur.get(k) for k in ("role", "sort_order", "variant_id")):
                to_update.append({**cur, **inc, "id": cur.get("id")})

    # Handle external URLs (no storage_object_id)
    current_external = {c["url"]: c for c in current if c.get("is_external") and not c.get("storage_object_id")}
    incoming_external = {i["url"]: i for i in incoming if i.get("is_external") and not i.get("storage_object_id")}
    to_add.extend(i for url, i in incoming_external.items() if url not in current_external)
    to_delete.extend(c for url, c in current_external.items() if url not in incoming_external)

    return to_add, to_update, to_delete
```

- [ ] **Step 5: Run diff tests**

Run: `python -m pytest tests/unit/modules/catalog/application/test_sync_product_media.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/modules/catalog/application/commands/create_product.py src/modules/catalog/application/commands/update_product.py tests/unit/modules/catalog/application/
git commit -m "feat(backend): product create/update accept media[] array with full-replace diff"
```

---

## Task 10: Update Brand create/update to accept `logo_url`

**Files:**
- Modify: `src/modules/catalog/application/commands/create_brand.py`
- Modify: `src/modules/catalog/application/commands/update_brand.py`
- Modify: `src/modules/catalog/presentation/schemas.py`
- Modify: `src/modules/catalog/presentation/router_brands.py`

- [ ] **Step 1: Simplify CreateBrandCommand**

Remove `LogoMetadata` dataclass. Replace `logo: LogoMetadata | None` with:
```python
    logo_url: str | None = None
    logo_storage_object_id: uuid.UUID | None = None
```

In handler, remove presigned URL generation. Simply pass `logo_url` and `logo_storage_object_id` to `Brand.create()`.

- [ ] **Step 2: Update UpdateBrandCommand for logo change with old logo cleanup**

Read `src/modules/catalog/application/commands/update_brand.py`. Add logo fields:

```python
# Add to UpdateBrandCommand:
    logo_url: str | None = None
    logo_storage_object_id: uuid.UUID | None = None
```

In `UpdateBrandHandler.handle()`, implement old logo cleanup per spec ("Backend saves new logo first, then calls DELETE for old logo_storage_object_id"):

```python
# In handle(), after locking the brand:
if command.logo_url is not None or command.logo_storage_object_id is not None:
    old_logo_sid = brand.logo_storage_object_id
    brand.logo_url = command.logo_url
    brand.logo_storage_object_id = command.logo_storage_object_id
    await self._brand_repo.update(brand)
    await self._uow.commit()

    # Best-effort cleanup of old logo in ImageBackend
    if old_logo_sid and old_logo_sid != command.logo_storage_object_id:
        await self._image_backend.delete(old_logo_sid)
```

The handler needs `ImageBackendClient` injected as a dependency.

- [ ] **Step 3: Update BrandCreateRequest and BrandUpdateRequest schemas**

Replace `logo: LogoMetadataRequest | None` with:
```python
    logo_url: str | None = None
    logo_storage_object_id: uuid.UUID | None = None
```

- [ ] **Step 4: Update router_brands.py**

Remove `POST /{brand_id}/logo/confirm` endpoint entirely.
Update `POST /` to map new fields from schema to command.
Update `PATCH /{brand_id}` to pass logo fields to command.

- [ ] **Step 5: Commit**

```bash
git add src/modules/catalog/application/commands/create_brand.py src/modules/catalog/application/commands/update_brand.py src/modules/catalog/presentation/schemas.py src/modules/catalog/presentation/router_brands.py
git commit -m "refactor(backend): Brand accepts logo_url directly — remove logo upload/confirm flow, add old logo cleanup"
```

---

## Task 11: Simplify `DeleteProductMediaHandler` with `ImageBackendClient`

**Files:**
- Modify: `src/modules/catalog/application/commands/delete_product_media.py`

- [ ] **Step 1: Read current handler**

Read `src/modules/catalog/application/commands/delete_product_media.py`.

- [ ] **Step 2: Simplify handler**

Remove all S3 cleanup (`IBlobStorage` calls). Replace with `ImageBackendClient.delete()`:

```python
class DeleteProductMediaHandler:
    def __init__(
        self,
        media_repo: IMediaAssetRepository,
        uow: IUnitOfWork,
        image_backend: ImageBackendClient,
        logger: ILogger,
    ) -> None:
        self._media_repo = media_repo
        self._uow = uow
        self._image_backend = image_backend
        self._logger = logger

    async def handle(self, command: DeleteProductMediaCommand) -> None:
        media = await self._media_repo.get(command.media_id)
        if not media:
            raise NotFoundError(f"Media {command.media_id} not found")
        if media.product_id != command.product_id:
            raise NotFoundError(f"Media {command.media_id} not found for product {command.product_id}")

        storage_object_id = media.storage_object_id
        await self._media_repo.delete(command.media_id)
        await self._uow.commit()

        # Best-effort cleanup in ImageBackend
        if storage_object_id:
            await self._image_backend.delete(storage_object_id)
```

- [ ] **Step 3: Commit**

```bash
git add src/modules/catalog/application/commands/delete_product_media.py
git commit -m "refactor(backend): DeleteProductMediaHandler uses ImageBackendClient instead of S3"
```

---

## Task 12: Delete old files + clean up DI

**Files:**
- Delete: All files listed in "Delete entirely" section above
- Modify: `src/bootstrap/container.py`
- Modify: `src/modules/catalog/presentation/dependencies.py`

- [ ] **Step 1: Delete storage module**

```bash
rm -rf src/modules/storage/
```

- [ ] **Step 2: Delete S3 interfaces**

```bash
rm src/shared/interfaces/blob_storage.py
rm src/shared/interfaces/storage.py
rm src/infrastructure/storage/factory.py
```

Remove `IStorageConfig` from `src/shared/interfaces/config.py` (keep the file if other interfaces exist).

- [ ] **Step 3: Delete old media command handlers**

```bash
rm src/modules/catalog/application/commands/add_product_media.py
rm src/modules/catalog/application/commands/add_external_product_media.py
rm src/modules/catalog/application/commands/confirm_product_media.py
rm src/modules/catalog/application/commands/complete_product_media.py
rm src/modules/catalog/application/commands/confirm_brand_logo.py
rm src/modules/catalog/application/services/media_processor.py
rm src/modules/catalog/application/constants.py
rm src/modules/catalog/application/tasks.py
```

- [ ] **Step 4: Delete old routers**

```bash
rm src/modules/catalog/presentation/router_product_media.py
rm src/modules/catalog/presentation/router_internal.py
```

- [ ] **Step 5: Update DI container**

In `src/bootstrap/container.py`:
- Remove `StorageProvider()` import and registration
- Remove `MediaAssetProvider()` if it only contained old handlers
- Add `ImageBackendClient` provider:

```python
from src.modules.catalog.infrastructure.image_backend_client import ImageBackendClient

# In ConfigProvider or a new provider:
@provide(scope=Scope.APP)
def image_backend_client(self, settings: Settings) -> ImageBackendClient:
    return ImageBackendClient(
        base_url=settings.IMAGE_BACKEND_URL,
        api_key=settings.IMAGE_BACKEND_API_KEY.get_secret_value(),
    )
```

- [ ] **Step 6: Update dependencies.py**

In `src/modules/catalog/presentation/dependencies.py`:
- Remove `MediaAssetProvider` class entirely
- Keep `IMediaAssetRepository` registration (move to `CatalogProvider` or `BrandProvider` as appropriate)
- Add `DeleteProductMediaHandler` registration with `ImageBackendClient` dependency

- [ ] **Step 7: Remove old router includes**

In the main catalog router file, remove includes for `router_product_media` and `router_internal`.

- [ ] **Step 8: Verify app starts**

Run: `python -c "from src.bootstrap.container import create_container; print('OK')"`
Expected: `OK`

Run: `python -c "from src.bootstrap.web import create_app; app = create_app(); print(f'{len(app.routes)} routes')"`
Expected: prints route count (should be lower than before)

- [ ] **Step 9: Commit**

```bash
git add -A
git commit -m "refactor(backend): delete storage module, S3 interfaces, old media handlers, internal router"
```

---

## Task 13: Clean up media-related schemas

**Files:**
- Modify: `src/modules/catalog/presentation/schemas.py`

- [ ] **Step 1: Remove dead schemas**

Remove from `schemas.py`:
- `ProductMediaUploadRequest`
- `ProductMediaUploadResponse`
- `ProductMediaExternalRequest`
- `ProductMediaResponse`
- `ProductMediaListResponse`
- `MediaConfirmResponse`
- `MediaProcessingWebhookRequest`
- `MediaProcessingFailedRequest`
- `WebhookAckResponse`
- `LogoMetadataRequest`

- [ ] **Step 2: Verify no broken imports**

Run: `python -c "from src.modules.catalog.presentation.schemas import BrandCreateRequest; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add src/modules/catalog/presentation/schemas.py
git commit -m "chore(backend): remove dead media schemas"
```

---

## Task 14: Run full test suite + fix breakage

**Files:**
- Various test files that reference deleted code

- [ ] **Step 1: Run all tests**

Run: `python -m pytest tests/ -v --tb=short 2>&1 | head -100`
Expected: Some failures due to import changes

- [ ] **Step 2: Fix test imports and mocks**

Update any tests that import deleted modules/classes:
- Replace `MediaProcessingStatus` references
- Replace `IBlobStorage` / `IStorageFacade` references
- Update Brand-related tests (remove logo FSM assertions)
- Update factory fixtures

- [ ] **Step 3: Run tests again**

Run: `python -m pytest tests/ -v`
Expected: All pass

- [ ] **Step 4: Commit**

```bash
git add tests/
git commit -m "test(backend): fix tests after media architecture simplification"
```

---

## Summary

| Task | What                                     | Key Change             |
| ---- | ---------------------------------------- | ---------------------- |
| 1    | Config: remove S3, add ImageBackend vars | `config.py`            |
| 2    | Create `ImageBackendClient`              | New httpx client       |
| 3    | Simplify `MediaAsset` entity             | Plain dataclass        |
| 4    | Simplify `Brand` entity                  | Remove logo FSM        |
| 5    | Simplify `IMediaAssetRepository`         | Remove status methods  |
| 6    | Simplify ORM + migration                 | DROP columns/table     |
| 7    | Simplify repository impl                 | Match new interface    |
| 8    | Media schemas for product payloads       | `schemas_media.py`     |
| 9    | Product create/update with `media[]`     | Full-replace diff      |
| 10   | Brand with `logo_url`                    | Remove upload/confirm  |
| 11   | Simplify delete handler                  | Use ImageBackendClient |
| 12   | Delete old files + clean DI              | Big cleanup            |
| 13   | Remove dead schemas                      | Schema cleanup         |
| 14   | Fix test suite                           | Green tests            |
