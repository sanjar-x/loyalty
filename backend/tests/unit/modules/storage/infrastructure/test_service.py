# tests/unit/modules/storage/infrastructure/test_service.py
"""Tests for S3StorageService."""

from unittest.mock import AsyncMock

import pytest
from _pytest.mark.structures import MarkDecorator
from botocore.exceptions import ClientError

from src.modules.storage.infrastructure.service import S3StorageService
from src.shared.exceptions import NotFoundError, ServiceUnavailableError

pytestmark: MarkDecorator = pytest.mark.asyncio


def _make_client_error(code: str, operation: str = "HeadObject") -> ClientError:
    return ClientError(
        {"Error": {"Code": code, "Message": "test error"}},
        operation,
    )


def _make_service(
    client: AsyncMock | None = None,
) -> tuple[S3StorageService, AsyncMock]:
    client: AsyncMock = client or AsyncMock()
    service = S3StorageService(s3_client=client, bucket_name="test-bucket")
    return service, client


class TestGetPresignedUrl:
    async def test_get_presigned_url_success(self):
        service, client = _make_service()
        client.generate_presigned_url = AsyncMock(
            return_value="https://s3.example.com/presigned-url"
        )

        url = await service.get_presigned_url("my-object.png", expiration=600)

        assert url == "https://s3.example.com/presigned-url"
        client.generate_presigned_url.assert_awaited_once_with(
            "get_object",
            Params={"Bucket": "test-bucket", "Key": "my-object.png"},
            ExpiresIn=600,
        )


class TestGeneratePresignedPutUrl:
    async def test_generate_presigned_put_url_success(self):
        service, client = _make_service()
        client.generate_presigned_url = AsyncMock(
            return_value="https://s3.example.com/put-url"
        )

        url = await service.generate_presigned_put_url(
            "uploads/file.jpg", content_type="image/jpeg", expiration=300
        )

        assert url == "https://s3.example.com/put-url"
        client.generate_presigned_url.assert_awaited_once_with(
            "put_object",
            Params={
                "Bucket": "test-bucket",
                "Key": "uploads/file.jpg",
                "ContentType": "image/jpeg",
            },
            ExpiresIn=300,
        )


class TestObjectExists:
    async def test_object_exists_true(self):
        service, client = _make_service()
        client.head_object = AsyncMock(return_value={"ContentLength": 100})

        result = await service.object_exists("my-object.png")

        assert result is True
        client.head_object.assert_awaited_once_with(
            Bucket="test-bucket", Key="my-object.png"
        )

    async def test_object_exists_false_on_404(self):
        service, client = _make_service()
        client.head_object = AsyncMock(side_effect=_make_client_error("404"))

        result = await service.object_exists("missing.png")

        assert result is False

    async def test_object_exists_raises_on_other_error(self):
        service, client = _make_service()
        client.head_object = AsyncMock(side_effect=_make_client_error("500"))

        with pytest.raises(ServiceUnavailableError):
            await service.object_exists("broken.png")


class TestGetObjectMetadata:
    async def test_get_object_metadata_success(self):
        service, client = _make_service()
        client.head_object = AsyncMock(
            return_value={
                "ContentLength": 12345,
                "ContentType": "image/png",
                "ETag": '"abc123"',
                "LastModified": "2025-01-01T00:00:00Z",
                "Metadata": {"owner": "test"},
            }
        )

        metadata = await service.get_object_metadata("my-object.png")

        assert metadata["content_length"] == 12345
        assert metadata["content_type"] == "image/png"
        assert metadata["etag"] == "abc123"
        assert metadata["last_modified"] == "2025-01-01T00:00:00Z"
        assert metadata["metadata"] == {"owner": "test"}

    async def test_get_object_metadata_not_found(self):
        service, client = _make_service()
        client.head_object = AsyncMock(side_effect=_make_client_error("404"))

        with pytest.raises(NotFoundError):
            await service.get_object_metadata("missing.png")


class TestDeleteObject:
    async def test_delete_object_success(self):
        service, client = _make_service()
        client.delete_object = AsyncMock(return_value={})

        await service.delete_object("my-object.png")

        client.delete_object.assert_awaited_once_with(
            Bucket="test-bucket", Key="my-object.png"
        )


class TestDeleteObjects:
    async def test_delete_objects_batch(self):
        service, client = _make_service()
        client.delete_objects = AsyncMock(
            return_value={"Errors": [{"Key": "fail.png"}]}
        )

        failed = await service.delete_objects(["a.png", "b.png", "fail.png"])

        assert failed == ["fail.png"]
        client.delete_objects.assert_awaited_once()

    async def test_delete_objects_batch_no_errors(self):
        service, client = _make_service()
        client.delete_objects = AsyncMock(return_value={})

        failed = await service.delete_objects(["a.png", "b.png"])

        assert failed == []


class TestCopyObject:
    async def test_copy_object_success(self):
        service, client = _make_service()
        client.copy_object = AsyncMock(return_value={})

        await service.copy_object("source.png", "dest.png")

        client.copy_object.assert_awaited_once_with(
            Bucket="test-bucket",
            CopySource={"Bucket": "test-bucket", "Key": "source.png"},
            Key="dest.png",
        )


class TestListObjects:
    async def test_list_objects_success(self):
        service, client = _make_service()
        client.list_objects_v2 = AsyncMock(
            return_value={
                "Contents": [
                    {
                        "Key": "file1.png",
                        "Size": 100,
                        "LastModified": "2025-01-01",
                        "ETag": '"etag1"',
                    },
                    {
                        "Key": "file2.png",
                        "Size": 200,
                        "LastModified": "2025-01-02",
                        "ETag": '"etag2"',
                    },
                ],
                "IsTruncated": False,
                "KeyCount": 2,
            }
        )

        result = await service.list_objects(prefix="uploads/", limit=50)

        assert len(result["objects"]) == 2
        assert result["objects"][0]["key"] == "file1.png"
        assert result["objects"][0]["size"] == 100
        assert result["objects"][1]["key"] == "file2.png"
        assert result["is_truncated"] is False
        assert result["key_count"] == 2
        assert result["next_continuation_token"] is None
