# src/shared/interfaces/blob_storage.py
from collections.abc import AsyncIterator
from typing import Any, Protocol


class IBlobStorage(Protocol):
    """
    Доменный контракт для работы с бинарным (объектным) хранилищем.
    """

    def download_stream(
        self, object_name: str, chunk_size: int = 65536
    ) -> AsyncIterator[bytes]: ...
    async def get_presigned_url(
        self, object_name: str, expiration: int = 3600
    ) -> str: ...

    async def get_presigned_upload_url(
        self, object_name: str, expiration: int = 3600
    ) -> dict: ...

    async def generate_presigned_put_url(
        self, object_name: str, content_type: str, expiration: int = 3600
    ) -> str: ...

    async def upload_stream(
        self,
        object_name: str,
        data_stream: AsyncIterator[bytes],
        content_type: str = "application/octet-stream",
    ) -> str: ...

    async def object_exists(self, object_name: str) -> bool: ...

    async def get_object_metadata(self, object_name: str) -> dict[str, Any]: ...

    async def list_objects(
        self,
        prefix: str = "",
        limit: int = 1000,
        continuation_token: str | None = None,
    ) -> dict: ...

    async def delete_object(self, object_name: str) -> None: ...
    async def delete_file(self, object_name: str) -> None: ...

    async def delete_objects(self, object_names: list[str]) -> list[str]: ...

    async def copy_object(self, source_name: str, dest_name: str) -> None: ...
