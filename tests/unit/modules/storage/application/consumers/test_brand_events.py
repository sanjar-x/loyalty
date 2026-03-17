# tests/unit/modules/storage/application/consumers/test_brand_events.py
"""Tests for Storage module brand event consumers."""

from collections.abc import Callable
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.modules.storage.application.consumers.brand_events import (
    handle_brand_created_event as _handle_brand_created_task,
)
from src.modules.storage.application.consumers.brand_events import (
    handle_brand_logo_processed_event as _handle_brand_logo_processed_task,
)
from src.modules.storage.domain.entities import StorageFile


def _unwrap_dishka_task(task: Any) -> Callable[..., Any]:
    return cast(Callable[..., Any], getattr(task.original_func, "__dishka_orig_func__"))


handle_brand_created_event = _unwrap_dishka_task(_handle_brand_created_task)
handle_brand_logo_processed_event = _unwrap_dishka_task(_handle_brand_logo_processed_task)

pytestmark = pytest.mark.asyncio


def _make_deps():
    """Create common mock dependencies for brand event consumers."""
    storage_repo = AsyncMock()
    uow = AsyncMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=False)

    settings = MagicMock()
    settings.S3_BUCKET_NAME = "test-bucket"

    logger = MagicMock()
    logger.bind = MagicMock(return_value=logger)

    return storage_repo, uow, settings, logger


class TestHandleBrandCreatedEvent:
    async def test_brand_created_creates_storage_file(self):
        storage_repo, uow, settings, logger = _make_deps()
        storage_repo.get_active_by_key = AsyncMock(return_value=None)
        storage_repo.add = AsyncMock()

        result = await handle_brand_created_event(
            brand_id="brand-123",
            object_key="logos/brand-123/logo.png",
            content_type="image/png",
            storage_repo=storage_repo,
            uow=uow,
            settings=settings,
            logger=logger,
        )

        assert result["status"] == "created"
        assert "file_id" in result
        storage_repo.get_active_by_key.assert_awaited_once_with(
            bucket_name="test-bucket",
            object_key="logos/brand-123/logo.png",
        )
        storage_repo.add.assert_awaited_once()
        uow.commit.assert_awaited_once()

        # Verify the StorageFile passed to add
        added_file = storage_repo.add.call_args[0][0]
        assert isinstance(added_file, StorageFile)
        assert added_file.bucket_name == "test-bucket"
        assert added_file.object_key == "logos/brand-123/logo.png"
        assert added_file.content_type == "image/png"
        assert added_file.owner_module == "catalog"

    async def test_brand_created_skips_duplicate(self):
        storage_repo, uow, settings, logger = _make_deps()
        existing_file = StorageFile.create(
            bucket_name="test-bucket",
            object_key="logos/brand-123/logo.png",
            content_type="image/png",
            owner_module="catalog",
        )
        storage_repo.get_active_by_key = AsyncMock(return_value=existing_file)

        result = await handle_brand_created_event(  # noqa: F841
            brand_id="brand-123",
            object_key="logos/brand-123/logo.png",
            content_type="image/png",
            storage_repo=storage_repo,
            uow=uow,
            settings=settings,
            logger=logger,
        )

        assert result["status"] == "skipped"
        assert result["reason"] == "already_exists"
        storage_repo.add.assert_not_awaited()
        uow.commit.assert_not_awaited()


class TestHandleBrandLogoProcessedEvent:
    async def test_logo_processed_updates_existing(self):
        storage_repo, uow, settings, logger = _make_deps()
        existing_file = StorageFile.create(
            bucket_name="test-bucket",
            object_key="logos/brand-123/logo.png",
            content_type="image/png",
            size_bytes=100,
            owner_module="catalog",
        )
        storage_repo.get_active_by_key = AsyncMock(return_value=existing_file)
        storage_repo.update = AsyncMock()

        result = await handle_brand_logo_processed_event(
            brand_id="brand-123",
            object_key="logos/brand-123/logo.png",
            content_type="image/webp",
            size_bytes=2048,
            storage_repo=storage_repo,
            uow=uow,
            settings=settings,
            logger=logger,
        )

        assert result["status"] == "updated"
        assert "file_id" in result
        # Verify the file was updated with new metadata
        assert existing_file.size_bytes == 2048
        assert existing_file.content_type == "image/webp"
        storage_repo.update.assert_awaited_once_with(existing_file)
        uow.commit.assert_awaited_once()
        storage_repo.add.assert_not_awaited()

    async def test_logo_processed_creates_new(self):
        storage_repo, uow, settings, logger = _make_deps()
        storage_repo.get_active_by_key = AsyncMock(return_value=None)
        storage_repo.add = AsyncMock()

        result = await handle_brand_logo_processed_event(
            brand_id="brand-123",
            object_key="logos/brand-123/logo.png",
            content_type="image/webp",
            size_bytes=4096,
            storage_repo=storage_repo,
            uow=uow,
            settings=settings,
            logger=logger,
        )

        assert result["status"] == "created"
        assert "file_id" in result
        storage_repo.add.assert_awaited_once()
        uow.commit.assert_awaited_once()

        added_file = storage_repo.add.call_args[0][0]
        assert isinstance(added_file, StorageFile)
        assert added_file.bucket_name == "test-bucket"
        assert added_file.object_key == "logos/brand-123/logo.png"
        assert added_file.content_type == "image/webp"
        assert added_file.size_bytes == 4096
        assert added_file.owner_module == "catalog"
