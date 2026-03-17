# tests/unit/modules/storage/infrastructure/test_service_extended.py
"""Extended tests for S3StorageService — covers methods and error paths
not yet exercised in test_service.py."""

from unittest.mock import AsyncMock

import pytest
from botocore.exceptions import ClientError

from src.modules.storage.infrastructure.service import S3StorageService
from src.shared.exceptions import NotFoundError, ServiceUnavailableError

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_client_error(code: str, operation: str = "HeadObject") -> ClientError:
    return ClientError(
        {"Error": {"Code": code, "Message": "test"}},
        operation,
    )


def _make_service(client=None):
    client = client or AsyncMock()
    return S3StorageService(s3_client=client, bucket_name="test-bucket"), client


async def _async_iter(chunks):
    """Turn an iterable of bytes into an async iterator."""
    for chunk in chunks:
        yield chunk


# ---------------------------------------------------------------------------
# upload_stream (multipart upload)
# ---------------------------------------------------------------------------


class TestUploadStream:
    async def test_upload_stream_success(self):
        """Small buffer that never exceeds the 5 MB part threshold —
        single trailing upload_part + complete_multipart_upload."""
        service, client = _make_service()
        client.create_multipart_upload = AsyncMock(return_value={"UploadId": "upload-123"})
        client.upload_part = AsyncMock(return_value={"ETag": '"etag-1"'})
        client.complete_multipart_upload = AsyncMock(return_value={})

        result = await service.upload_stream(
            object_name="photos/pic.jpg",
            data_stream=_async_iter([b"chunk1", b"chunk2"]),
            content_type="image/jpeg",
        )

        assert result == "photos/pic.jpg"
        client.create_multipart_upload.assert_awaited_once_with(
            Bucket="test-bucket", Key="photos/pic.jpg", ContentType="image/jpeg"
        )
        # Only one upload_part for the trailing buffer
        client.upload_part.assert_awaited_once()
        client.complete_multipart_upload.assert_awaited_once()

    async def test_upload_stream_aborts_on_error(self):
        """When create_multipart_upload succeeds but upload_part fails,
        the multipart upload must be aborted and ServiceUnavailableError raised."""
        service, client = _make_service()
        client.create_multipart_upload = AsyncMock(return_value={"UploadId": "upload-456"})
        client.upload_part = AsyncMock(side_effect=RuntimeError("upload broke"))
        client.abort_multipart_upload = AsyncMock(return_value={})

        with pytest.raises(ServiceUnavailableError):
            await service.upload_stream(
                object_name="photos/broken.jpg",
                data_stream=_async_iter([b"data"]),
            )

        client.abort_multipart_upload.assert_awaited_once_with(
            Bucket="test-bucket", Key="photos/broken.jpg", UploadId="upload-456"
        )


# ---------------------------------------------------------------------------
# download_stream
# ---------------------------------------------------------------------------


class TestDownloadStream:
    async def test_download_stream_yields_chunks(self):
        """download_stream should yield chunks from the S3 response body."""
        service, client = _make_service()
        body = AsyncMock()
        body.read = AsyncMock(side_effect=[b"chunk1", b"chunk2", b""])
        client.get_object = AsyncMock(return_value={"Body": body})

        chunks = []
        async for chunk in service.download_stream("file.bin"):
            chunks.append(chunk)

        assert chunks == [b"chunk1", b"chunk2"]
        client.get_object.assert_awaited_once_with(Bucket="test-bucket", Key="file.bin")

    async def test_download_stream_client_error(self):
        """A 404 ClientError should raise NotFoundError."""
        service, client = _make_service()
        client.get_object = AsyncMock(side_effect=_make_client_error("404", "GetObject"))

        with pytest.raises(NotFoundError):
            async for _ in service.download_stream("missing.bin"):
                pass  # pragma: no cover


# ---------------------------------------------------------------------------
# get_presigned_upload_url (POST variant)
# ---------------------------------------------------------------------------


class TestGetPresignedUploadUrl:
    async def test_get_presigned_upload_url_success(self):
        service, client = _make_service()
        expected = {"url": "https://s3.example.com/upload", "fields": {"key": "obj"}}
        client.generate_presigned_post = AsyncMock(return_value=expected)

        result = await service.get_presigned_upload_url("obj.jpg", expiration=600)

        assert result == expected
        client.generate_presigned_post.assert_awaited_once_with(
            Bucket="test-bucket", Key="obj.jpg", ExpiresIn=600
        )

    async def test_get_presigned_upload_url_error(self):
        service, client = _make_service()
        client.generate_presigned_post = AsyncMock(
            side_effect=_make_client_error("500", "GeneratePresignedPost")
        )

        with pytest.raises(ServiceUnavailableError):
            await service.get_presigned_upload_url("obj.jpg")


# ---------------------------------------------------------------------------
# Error paths for existing methods
# ---------------------------------------------------------------------------


class TestGetPresignedUrlError:
    async def test_get_presigned_url_error(self):
        service, client = _make_service()
        client.generate_presigned_url = AsyncMock(
            side_effect=_make_client_error("500", "GeneratePresignedUrl")
        )

        with pytest.raises(ServiceUnavailableError):
            await service.get_presigned_url("key.png")


class TestGeneratePresignedPutUrlError:
    async def test_generate_presigned_put_url_error(self):
        service, client = _make_service()
        client.generate_presigned_url = AsyncMock(
            side_effect=_make_client_error("500", "GeneratePresignedUrl")
        )

        with pytest.raises(ServiceUnavailableError):
            await service.generate_presigned_put_url("key.png", content_type="image/png")


class TestDeleteObjectError:
    async def test_delete_object_error(self):
        service, client = _make_service()
        client.delete_object = AsyncMock(side_effect=_make_client_error("500", "DeleteObject"))

        with pytest.raises(ServiceUnavailableError):
            await service.delete_object("key.png")


class TestDeleteObjectsClientError:
    async def test_delete_objects_client_error(self):
        service, client = _make_service()
        client.delete_objects = AsyncMock(side_effect=_make_client_error("500", "DeleteObjects"))

        with pytest.raises(ServiceUnavailableError):
            await service.delete_objects(["a.png", "b.png"])


class TestCopyObjectNotFound:
    async def test_copy_object_not_found(self):
        """A 404 ClientError during copy_object should raise NotFoundError."""
        service, client = _make_service()
        client.copy_object = AsyncMock(side_effect=_make_client_error("404", "CopyObject"))

        with pytest.raises(NotFoundError):
            await service.copy_object("missing.png", "dest.png")


class TestListObjectsError:
    async def test_list_objects_error(self):
        service, client = _make_service()
        client.list_objects_v2 = AsyncMock(side_effect=_make_client_error("500", "ListObjectsV2"))

        with pytest.raises(ServiceUnavailableError):
            await service.list_objects(prefix="uploads/")


class TestDeleteFile:
    async def test_delete_file_delegates(self):
        """delete_file is a thin wrapper that delegates to delete_object."""
        service, client = _make_service()
        client.delete_object = AsyncMock(return_value={})

        await service.delete_file("file.png")

        client.delete_object.assert_awaited_once_with(Bucket="test-bucket", Key="file.png")


class TestHandleClientErrorNon404:
    async def test_handle_client_error_non_404(self):
        """Non-404 codes (e.g. 403) in _handle_client_error should raise
        ServiceUnavailableError, not NotFoundError."""
        service, client = _make_service()
        client.head_object = AsyncMock(side_effect=_make_client_error("403", "HeadObject"))

        # get_object_metadata calls _handle_client_error internally
        with pytest.raises(ServiceUnavailableError):
            await service.get_object_metadata("forbidden.png")


class TestListObjectsWithContinuationToken:
    async def test_list_objects_with_continuation_token(self):
        """When a continuation_token is supplied it should be forwarded
        as ContinuationToken in the S3 request kwargs."""
        service, client = _make_service()
        client.list_objects_v2 = AsyncMock(
            return_value={
                "Contents": [],
                "IsTruncated": False,
                "KeyCount": 0,
            }
        )

        await service.list_objects(prefix="img/", limit=10, continuation_token="tok-abc")

        client.list_objects_v2.assert_awaited_once_with(
            Bucket="test-bucket",
            Prefix="img/",
            MaxKeys=10,
            ContinuationToken="tok-abc",
        )
