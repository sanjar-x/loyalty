"""S3 helpers — minimal aiobotocore wrappers.

Mirror of the storage worker's ``s3.py`` so both workers share the
wire-level contract with backend but not the Python code.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from aiobotocore.session import AioSession
from config import settings
from types_aiobotocore_s3.client import S3Client

_session = AioSession()


@asynccontextmanager
async def s3_client() -> AsyncIterator[S3Client]:
    async with _session.create_client(  # ty:ignore
        "s3",
        endpoint_url=settings.S3_ENDPOINT_URL,
        region_name=settings.S3_REGION,
        aws_access_key_id=settings.S3_ACCESS_KEY.get_secret_value(),
        aws_secret_access_key=settings.S3_SECRET_KEY.get_secret_value(),
    ) as client:
        yield client


async def download_bytes(object_key: str) -> bytes:
    async with s3_client() as client:
        response = await client.get_object(  # ty:ignore
            Bucket=settings.S3_BUCKET_NAME, Key=object_key
        )
        async with response["Body"] as stream:
            return await stream.read()


async def upload_bytes(object_key: str, data: bytes, content_type: str) -> None:
    async with s3_client() as client:
        await client.put_object(  # ty:ignore
            Bucket=settings.S3_BUCKET_NAME,
            Key=object_key,
            Body=data,
            ContentType=content_type,
        )
