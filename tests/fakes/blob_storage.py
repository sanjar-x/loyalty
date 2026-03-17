# tests/fakes/blob_storage.py
"""
Fake implementation of IBlobStorage for testing.
Uses an in-memory dict instead of S3/MinIO.
"""

from collections.abc import AsyncIterator
from typing import Any


class InMemoryBlobStorage:
    """In-memory fake implementing IBlobStorage protocol."""

    def __init__(self) -> None:
        self._objects: dict[str, bytes] = {}
        self._metadata: dict[str, dict[str, Any]] = {}

    async def download_stream(
        self, object_name: str, chunk_size: int = 65536
    ) -> AsyncIterator[bytes]:
        data = self._objects.get(object_name, b"")
        yield data

    async def get_presigned_url(self, object_name: str, expiration: int = 3600) -> str:
        return f"https://fake-s3.test/{object_name}?expires={expiration}"

    async def get_presigned_upload_url(
        self, object_name: str, expiration: int = 3600
    ) -> dict:
        return {
            "url": f"https://fake-s3.test/{object_name}",
            "fields": {"key": object_name},
        }

    async def generate_presigned_put_url(
        self, object_name: str, content_type: str, expiration: int = 3600
    ) -> str:
        return f"https://fake-s3.test/{object_name}?content_type={content_type}&expires={expiration}"

    async def upload_stream(
        self,
        object_name: str,
        data_stream: AsyncIterator[bytes],
        content_type: str = "application/octet-stream",
    ) -> str:
        chunks = []
        async for chunk in data_stream:
            chunks.append(chunk)
        self._objects[object_name] = b"".join(chunks)
        self._metadata[object_name] = {"content_type": content_type}
        return object_name

    async def object_exists(self, object_name: str) -> bool:
        return object_name in self._objects

    async def get_object_metadata(self, object_name: str) -> dict[str, Any]:
        return self._metadata.get(object_name, {})

    async def list_objects(
        self,
        prefix: str = "",
        limit: int = 1000,
        continuation_token: str | None = None,
    ) -> dict:
        keys = [k for k in self._objects if k.startswith(prefix)][:limit]
        return {"objects": keys, "continuation_token": None}

    async def delete_object(self, object_name: str) -> None:
        self._objects.pop(object_name, None)
        self._metadata.pop(object_name, None)

    async def delete_objects(self, object_names: list[str]) -> list[str]:
        deleted = []
        for name in object_names:
            if name in self._objects:
                await self.delete_object(name)
                deleted.append(name)
        return deleted

    async def copy_object(self, source_name: str, dest_name: str) -> None:
        if source_name in self._objects:
            self._objects[dest_name] = self._objects[source_name]
            self._metadata[dest_name] = self._metadata.get(source_name, {}).copy()
