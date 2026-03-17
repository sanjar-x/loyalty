# src/modules/storage/domain/entities.py
import uuid
from datetime import datetime

from attr import dataclass


@dataclass
class StorageFile:
    """Доменная сущность файла в объектном хранилище."""

    id: uuid.UUID
    bucket_name: str
    object_key: str
    content_type: str
    size_bytes: int = 0
    is_latest: bool = True
    owner_module: str | None = None
    version_id: str | None = None
    etag: str | None = None
    content_encoding: str | None = None
    cache_control: str | None = None
    created_at: datetime | None = None
    last_modified_in_s3: datetime | None = None

    @classmethod
    def create(
        cls,
        bucket_name: str,
        object_key: str,
        content_type: str,
        size_bytes: int = 0,
        owner_module: str | None = None,
    ) -> StorageFile:
        return cls(
            id=uuid.uuid7() if hasattr(uuid, "uuid7") else uuid.uuid4(),
            bucket_name=bucket_name,
            object_key=object_key,
            content_type=content_type,
            size_bytes=size_bytes,
            owner_module=owner_module,
        )
