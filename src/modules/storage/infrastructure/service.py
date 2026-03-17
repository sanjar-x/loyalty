"""S3-compatible blob storage service.

Implements the ``IBlobStorage`` interface using ``aiobotocore`` to
communicate with an S3-compatible object store (AWS S3, MinIO, etc.).
Provides streaming upload/download, presigned URL generation, object
listing, deletion, and copy operations.
"""

from collections.abc import AsyncIterator
from typing import Any

import structlog
from aiobotocore.client import AioBaseClient
from botocore.exceptions import ClientError

from src.shared.exceptions import NotFoundError, ServiceUnavailableError
from src.shared.interfaces.blob_storage import IBlobStorage

logger = structlog.get_logger(__name__)


class S3StorageService(IBlobStorage):
    """Blob storage service backed by an S3-compatible API.

    Wraps an ``aiobotocore`` client and translates S3 ``ClientError``
    exceptions into application-level ``NotFoundError`` and
    ``ServiceUnavailableError``.

    Args:
        s3_client: An ``aiobotocore`` S3 client instance.
        bucket_name: Default bucket to operate on.
    """

    def __init__(self, s3_client: AioBaseClient, bucket_name: str):
        self._client: AioBaseClient = s3_client
        self._bucket = bucket_name

    def _handle_client_error(self, e: ClientError, object_name: str) -> None:
        """Translate an S3 ``ClientError`` into a domain exception.

        Args:
            e: The original boto client error.
            object_name: The S3 object key that triggered the error.

        Raises:
            NotFoundError: If the error code indicates the object does not exist.
            ServiceUnavailableError: For all other S3 errors.
        """
        error_code = e.response.get("Error", {}).get("Code", "")
        if error_code in ("404", "NoSuchKey", "NotFound"):
            raise NotFoundError(
                message=f"Object '{object_name}' not found in storage.",
                details={"bucket": self._bucket, "key": object_name},
            )
        logger.error(
            "s3_client_error",
            object_name=object_name,
            error_code=error_code,
            error=str(e),
        )
        raise ServiceUnavailableError(
            message="Error communicating with the storage service.",
            details={"error_code": error_code},
        )

    async def download_stream(
        self, object_name: str, chunk_size: int = 65536
    ) -> AsyncIterator[bytes]:
        """Download an object as an async byte stream.

        Args:
            object_name: The S3 object key to download.
            chunk_size: Number of bytes per chunk. Defaults to 64 KB.

        Yields:
            Byte chunks of the requested object.

        Raises:
            NotFoundError: If the object does not exist.
            ServiceUnavailableError: On S3 communication failure.
        """
        try:
            response = await self._client.get_object(Bucket=self._bucket, Key=object_name)
            stream = response["Body"]

            while True:
                chunk = await stream.read(chunk_size)
                if not chunk:
                    break
                yield chunk
        except ClientError as e:
            self._handle_client_error(e, object_name)

    async def get_presigned_url(self, object_name: str, expiration: int = 3600) -> str:
        """Generate a presigned GET URL for downloading an object.

        Args:
            object_name: The S3 object key.
            expiration: URL validity duration in seconds. Defaults to 3600.

        Returns:
            A presigned URL string.

        Raises:
            ServiceUnavailableError: If URL generation fails.
        """
        try:
            return await self._client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self._bucket, "Key": object_name},
                ExpiresIn=expiration,
            )
        except ClientError as e:
            logger.error("s3_presigned_url_error", object_name=object_name, error=str(e))
            raise ServiceUnavailableError(
                message="Failed to generate a presigned download URL.",
                details={"key": object_name},
            )

    async def upload_stream(
        self,
        object_name: str,
        data_stream: AsyncIterator[bytes],
        content_type: str = "application/octet-stream",
    ) -> str:
        """Upload data via S3 multipart upload.

        Reads from the async byte stream and uploads in parts of at
        least 5 MB (the AWS S3 multipart minimum). On failure, any
        incomplete upload is aborted to avoid orphaned parts on the
        server.

        Args:
            object_name: The target S3 object key.
            data_stream: An async iterator yielding byte chunks.
            content_type: MIME type for the uploaded object.

        Returns:
            The object key of the successfully uploaded file.

        Raises:
            ServiceUnavailableError: If the upload fails.
        """
        upload_id = None
        parts = []
        part_number = 1
        buffer = b""
        min_part_size = 5 * 1024 * 1024  # 5 MB - AWS S3 multipart minimum

        try:
            # Initialize multipart upload
            mpu = await self._client.create_multipart_upload(
                Bucket=self._bucket, Key=object_name, ContentType=content_type
            )
            upload_id = mpu["UploadId"]

            # Read stream and upload in chunks
            async for chunk in data_stream:
                buffer += chunk
                while len(buffer) >= min_part_size:
                    part_data = buffer[:min_part_size]
                    buffer = buffer[min_part_size:]

                    upload_result = await self._client.upload_part(
                        Bucket=self._bucket,
                        Key=object_name,
                        PartNumber=part_number,
                        UploadId=upload_id,
                        Body=part_data,
                    )
                    parts.append({"PartNumber": part_number, "ETag": upload_result["ETag"]})
                    part_number += 1

            # Flush remaining buffer (tail), even if smaller than 5 MB
            if buffer or part_number == 1:
                upload_result = await self._client.upload_part(
                    Bucket=self._bucket,
                    Key=object_name,
                    PartNumber=part_number,
                    UploadId=upload_id,
                    Body=buffer,
                )
                parts.append({"PartNumber": part_number, "ETag": upload_result["ETag"]})

            # Finalize the multipart upload on S3
            await self._client.complete_multipart_upload(
                Bucket=self._bucket,
                Key=object_name,
                UploadId=upload_id,
                MultipartUpload={"Parts": parts},
            )
            logger.debug(
                "s3_multipart_upload_completed",
                object_name=object_name,
                total_parts=len(parts),
            )
            return object_name

        except Exception as e:
            # On error, abort the multipart upload to clean up orphaned parts
            logger.error("s3_upload_stream_error", object_name=object_name, error=str(e))
            if upload_id:
                try:
                    await self._client.abort_multipart_upload(
                        Bucket=self._bucket, Key=object_name, UploadId=upload_id
                    )
                except Exception as abort_err:
                    logger.error(
                        "s3_abort_multipart_error",
                        object_name=object_name,
                        upload_id=upload_id,
                        error=str(abort_err),
                    )

            raise ServiceUnavailableError(
                message="Error uploading file to storage.",
                details={"key": object_name, "error": str(e)},
            )

    async def get_presigned_upload_url(self, object_name: str, expiration: int = 3600) -> dict:
        """Generate a presigned POST URL for browser-based uploads.

        Args:
            object_name: The target S3 object key.
            expiration: URL validity duration in seconds. Defaults to 3600.

        Returns:
            A dict containing the POST URL and form fields.

        Raises:
            ServiceUnavailableError: If URL generation fails.
        """
        try:
            return await self._client.generate_presigned_post(
                Bucket=self._bucket, Key=object_name, ExpiresIn=expiration
            )
        except ClientError as e:
            logger.error("s3_presigned_upload_url_error", object_name=object_name, error=str(e))
            raise ServiceUnavailableError(
                message="Failed to generate a presigned upload URL.",
                details={"key": object_name},
            )

    async def generate_presigned_put_url(
        self, object_name: str, content_type: str, expiration: int = 3600
    ) -> str:
        """Generate a presigned PUT URL for direct file uploads.

        Args:
            object_name: The target S3 object key.
            content_type: Required MIME type for the upload.
            expiration: URL validity duration in seconds. Defaults to 3600.

        Returns:
            A presigned PUT URL string.

        Raises:
            ServiceUnavailableError: If URL generation fails.
        """
        try:
            return await self._client.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": self._bucket,
                    "Key": object_name,
                    "ContentType": content_type,
                },
                ExpiresIn=expiration,
            )
        except ClientError as e:
            logger.error("s3_presigned_put_url_error", object_name=object_name, error=str(e))
            raise ServiceUnavailableError(
                message="Failed to generate a direct upload URL.",
                details={"key": object_name},
            )

    async def object_exists(self, object_name: str) -> bool:
        """Check whether an object exists in the bucket.

        Args:
            object_name: The S3 object key to check.

        Returns:
            ``True`` if the object exists, ``False`` otherwise.

        Raises:
            ServiceUnavailableError: On unexpected S3 errors.
        """
        try:
            await self._client.head_object(Bucket=self._bucket, Key=object_name)
            return True
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            if error_code in ("404", "NoSuchKey", "NotFound"):
                return False

            logger.error("s3_object_exists_error", object_name=object_name, error=str(e))
            raise ServiceUnavailableError(message="Error checking file existence.")

    async def get_object_metadata(self, object_name: str) -> dict[str, Any]:
        """Retrieve metadata for an object via a HEAD request.

        Args:
            object_name: The S3 object key.

        Returns:
            A dict with ``content_length``, ``content_type``, ``etag``,
            ``last_modified``, and ``metadata`` keys.

        Raises:
            NotFoundError: If the object does not exist.
            ServiceUnavailableError: On S3 communication failure.
        """
        try:
            response = await self._client.head_object(Bucket=self._bucket, Key=object_name)
            return {
                "content_length": response.get("ContentLength"),
                "content_type": response.get("ContentType"),
                "etag": response.get("ETag", "").strip('"'),
                "last_modified": response.get("LastModified"),
                "metadata": response.get("Metadata", {}),
            }
        except ClientError as e:
            self._handle_client_error(e, object_name)
            return {}

    async def list_objects(
        self,
        prefix: str = "",
        limit: int = 1000,
        continuation_token: str | None = None,
    ) -> dict:
        """List objects in the bucket with optional prefix filtering.

        Supports cursor-based pagination via ``continuation_token``.

        Args:
            prefix: Object key prefix to filter by. Defaults to ``""``.
            limit: Maximum number of keys to return. Defaults to 1000.
            continuation_token: Token from a previous response for
                fetching the next page.

        Returns:
            A dict with ``objects`` (list of key/size/date/etag dicts),
            ``next_continuation_token``, ``is_truncated``, and
            ``key_count``.

        Raises:
            ServiceUnavailableError: On S3 communication failure.
        """
        kwargs: dict[str, Any] = {
            "Bucket": self._bucket,
            "Prefix": prefix,
            "MaxKeys": limit,
        }
        if continuation_token:
            kwargs["ContinuationToken"] = continuation_token

        try:
            response = await self._client.list_objects_v2(**kwargs)

            objects = []
            for s3_item in response.get("Contents", []):
                objects.append(
                    {
                        "key": s3_item["Key"],
                        "size": s3_item["Size"],
                        "last_modified": s3_item["LastModified"],
                        "etag": s3_item.get("ETag", "").strip('"'),
                    }
                )

            return {
                "objects": objects,
                "next_continuation_token": response.get("NextContinuationToken"),
                "is_truncated": response.get("IsTruncated", False),
                "key_count": response.get("KeyCount", 0),
            }
        except ClientError as e:
            logger.error("s3_list_objects_error", prefix=prefix, error=str(e))
            raise ServiceUnavailableError(message="Error listing files from storage.")

    async def delete_object(self, object_name: str) -> None:
        """Delete a single object from the bucket.

        Args:
            object_name: The S3 object key to delete.

        Raises:
            ServiceUnavailableError: If deletion fails.
        """
        try:
            await self._client.delete_object(Bucket=self._bucket, Key=object_name)
        except ClientError as e:
            logger.error("s3_delete_object_error", object_name=object_name, error=str(e))
            raise ServiceUnavailableError(
                message="Failed to delete file.", details={"key": object_name}
            )

    async def delete_objects(self, object_names: list[str]) -> list[str]:
        """Delete multiple objects in batches of up to 1000.

        Args:
            object_names: List of S3 object keys to delete.

        Returns:
            A list of keys that failed to delete.

        Raises:
            ServiceUnavailableError: On S3 communication failure.
        """
        failed_keys = []
        chunk_size = 1000

        try:
            for i in range(0, len(object_names), chunk_size):
                chunk = object_names[i : i + chunk_size]
                delete_request = {
                    "Objects": [{"Key": key} for key in chunk],
                    "Quiet": True,
                }

                response = await self._client.delete_objects(
                    Bucket=self._bucket, Delete=delete_request
                )

                if "Errors" in response:
                    failed_keys.extend([error["Key"] for error in response["Errors"]])

            return failed_keys
        except ClientError as e:
            logger.error("s3_batch_delete_error", count=len(object_names), error=str(e))
            raise ServiceUnavailableError(message="Error during batch file deletion.")

    async def copy_object(self, source_name: str, dest_name: str) -> None:
        """Copy an object within the same bucket.

        Args:
            source_name: The source S3 object key.
            dest_name: The destination S3 object key.

        Raises:
            NotFoundError: If the source object does not exist.
            ServiceUnavailableError: On S3 communication failure.
        """
        try:
            copy_source = {"Bucket": self._bucket, "Key": source_name}
            await self._client.copy_object(
                Bucket=self._bucket, CopySource=copy_source, Key=dest_name
            )
        except ClientError as e:
            self._handle_client_error(e, source_name)
