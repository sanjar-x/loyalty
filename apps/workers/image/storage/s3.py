"""S3 helpers — minimal aiobotocore wrappers for download / upload / delete.

No ``IBlobStorage`` Protocol, no abstraction beyond what the worker
actually needs. The same wire format (single bucket + key) is what
backend writes when it provisions the row in the storage_objects
table.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from aiobotocore.session import AioSession
from types_aiobotocore_s3.client import S3Client  # only at type-check time

from config import settings

# Single AioSession shared across calls — boto's session is thread-safe
# and the underlying connection pool is held by the client context
# manager, not the session.
_session = AioSession()


@asynccontextmanager
async def s3_client() -> AsyncIterator[S3Client]:
    """Yield an aiobotocore S3 client configured from worker env vars."""
    async with _session.create_client(  # ty:ignore
        "s3",
        endpoint_url=settings.S3_ENDPOINT_URL,
        region_name=settings.S3_REGION,
        aws_access_key_id=settings.S3_ACCESS_KEY.get_secret_value(),
        aws_secret_access_key=settings.S3_SECRET_KEY.get_secret_value(),
    ) as client:
        yield client


async def download_bytes(object_key: str) -> bytes:
    """Read the full body of ``object_key`` from the configured bucket."""
    async with s3_client() as client:
        response = await client.get_object(  # ty:ignore
            Bucket=settings.S3_BUCKET_NAME, Key=object_key
        )
        async with response["Body"] as stream:
            return await stream.read()


async def upload_bytes(
    object_key: str, data: bytes, content_type: str
) -> None:
    """Upload a single object — full-buffer ``PutObject`` (no multipart).

    Variants and main WebPs are <1 MB, so multipart upload overhead is
    not worth it here. Backend's S3 service uses multipart for large
    raw uploads on the request path; this worker only writes processed
    output that fits comfortably in one request.
    """
    async with s3_client() as client:
        await client.put_object(  # ty:ignore
            Bucket=settings.S3_BUCKET_NAME,
            Key=object_key,
            Body=data,
            ContentType=content_type,
        )


async def delete_object(object_key: str) -> None:
    """Delete a single S3 object — used by both process_image (drop raw
    upload after variants are persisted) and cleanup_orphans
    (drop pending uploads older than 24 h).
    """
    async with s3_client() as client:
        await client.delete_object(  # ty:ignore
            Bucket=settings.S3_BUCKET_NAME, Key=object_key
        )
