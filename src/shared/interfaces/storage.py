# src\shared\interfaces\storage.py
import abc
from typing import Any, AsyncIterator, Dict, List, Optional


class IS3torageService(abc.ABC):
    @abc.abstractmethod
    async def download_stream(
        self, object_name: str, chunk_size: int = 65536
    ) -> AsyncIterator[bytes]:
        yield b""

    @abc.abstractmethod
    async def get_presigned_url(self, object_name: str, expiration: int = 3600) -> str:
        pass

    @abc.abstractmethod
    async def get_presigned_upload_url(
        self, object_name: str, expiration: int = 3600
    ) -> dict:
        pass

    @abc.abstractmethod
    async def upload_stream(
        self,
        object_name: str,
        data_stream: AsyncIterator[bytes],
        content_type: str = "application/octet-stream",
    ) -> str:
        pass

    @abc.abstractmethod
    async def object_exists(self, object_name: str) -> bool:
        pass

    @abc.abstractmethod
    async def get_object_metadata(self, object_name: str) -> Dict[str, Any]:
        pass

    @abc.abstractmethod
    async def list_objects(
        self,
        prefix: str = "",
        limit: int = 1000,
        continuation_token: Optional[str] = None,
    ) -> dict:
        pass

    @abc.abstractmethod
    async def delete_object(self, object_name: str) -> None:
        pass

    @abc.abstractmethod
    async def delete_objects(self, object_names: List[str]) -> List[str]:
        pass

    @abc.abstractmethod
    async def copy_object(self, source_name: str, dest_name: str) -> None:
        pass
