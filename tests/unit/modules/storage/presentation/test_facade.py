# tests/unit/modules/storage/presentation/test_facade.py
"""Tests for StorageFacade."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from _pytest.mark.structures import MarkDecorator

from src.modules.storage.domain.entities import StorageFile
from src.modules.storage.presentation.facade import StorageFacade
from src.shared.exceptions import ValidationError

pytestmark: MarkDecorator = pytest.mark.asyncio


def _make_facade():
    """Create a StorageFacade with all dependencies mocked."""
    blob_storage = AsyncMock()
    storage_repo = AsyncMock()

    uow = AsyncMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=False)

    settings = MagicMock()
    settings.S3_BUCKET_NAME = "test-bucket"

    logger = MagicMock()
    logger.bind = MagicMock(return_value=logger)

    facade = StorageFacade(
        blob_storage=blob_storage,
        storage_repo=storage_repo,
        uow=uow,
        settings=settings,
        logger=logger,
    )

    return facade, blob_storage, storage_repo, uow, settings, logger


class TestRequestUpload:
    async def test_request_upload_returns_presigned_data(self):
        facade, blob_storage, *_ = _make_facade()
        blob_storage.get_presigned_upload_url = AsyncMock(
            return_value={"url": "https://s3.example.com/upload", "fields": {}}
        )

        result = await facade.request_upload(
            module="catalog",
            entity_id="entity-123",
            filename="logo.png",
        )

        assert result.object_key == "temp/catalog/entity-123/upload.png"
        assert result.url_data == {"url": "https://s3.example.com/upload", "fields": {}}
        blob_storage.get_presigned_upload_url.assert_awaited_once()


class TestRequestDirectUpload:
    async def test_request_direct_upload_returns_put_url(self):
        facade, blob_storage, *_ = _make_facade()
        blob_storage.generate_presigned_put_url = AsyncMock(
            return_value="https://s3.example.com/put-url"
        )

        result = await facade.request_direct_upload(
            module="catalog",
            entity_id="entity-456",
            filename="photo.jpg",
            content_type="image/jpeg",
            expire_in=300,
        )

        assert result.object_key == "raw_uploads/catalog/entity-456/upload_raw.jpg"
        assert result.url_data == "https://s3.example.com/put-url"
        blob_storage.generate_presigned_put_url.assert_awaited_once_with(
            object_name="raw_uploads/catalog/entity-456/upload_raw.jpg",
            content_type="image/jpeg",
            expiration=300,
        )


class TestRegisterProcessedMedia:
    async def test_register_processed_media_creates_file(self):
        facade, blob_storage, storage_repo, uow, settings, logger = _make_facade()

        file_id = await facade.register_processed_media(
            module="catalog",
            entity_id="entity-789",
            object_key="processed/catalog/entity-789/logo.webp",
            content_type="image/webp",
            size=4096,
        )

        assert isinstance(file_id, uuid.UUID)
        storage_repo.add.assert_awaited_once()
        uow.commit.assert_awaited_once()

        added_file = storage_repo.add.call_args[0][0]
        assert isinstance(added_file, StorageFile)
        assert added_file.bucket_name == "test-bucket"
        assert added_file.object_key == "processed/catalog/entity-789/logo.webp"
        assert added_file.content_type == "image/webp"
        assert added_file.size_bytes == 4096
        assert added_file.owner_module == "catalog"


class TestVerifyUpload:
    async def test_verify_upload_file_not_found(self):
        facade, blob_storage, storage_repo, uow, *_ = _make_facade()
        storage_repo.get_by_key = AsyncMock(return_value=None)

        with pytest.raises(ValidationError, match="Запись о файле не найдена"):
            await facade.verify_upload(file_id=uuid.uuid4())


class TestUpdateObjectMetadata:
    async def test_update_object_metadata_success(self):
        facade, blob_storage, storage_repo, uow, *_ = _make_facade()
        file_id = uuid.uuid4()
        existing_file = StorageFile.create(
            bucket_name="test-bucket",
            object_key="old-key.png",
            content_type="image/png",
            size_bytes=100,
            owner_module="catalog",
        )
        storage_repo.get_by_key = AsyncMock(return_value=existing_file)
        storage_repo.update = AsyncMock()

        await facade.update_object_metadata(
            file_id=file_id,
            object_key="new-key.webp",
            size_bytes=2048,
            content_type="image/webp",
        )

        storage_repo.get_by_key.assert_awaited_once_with(file_id)
        storage_repo.update.assert_awaited_once_with(existing_file)
        uow.commit.assert_awaited_once()
        assert existing_file.object_key == "new-key.webp"
        assert existing_file.size_bytes == 2048
        assert existing_file.content_type == "image/webp"

    async def test_update_object_metadata_not_found(self):
        facade, blob_storage, storage_repo, uow, *_ = _make_facade()
        storage_repo.get_by_key = AsyncMock(return_value=None)

        with pytest.raises(ValidationError, match="Запись о файле не найдена"):
            await facade.update_object_metadata(
                file_id=uuid.uuid4(),
                object_key="some-key.png",
                size_bytes=100,
                content_type="image/png",
            )
