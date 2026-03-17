# tests/factories/storage_mothers.py
"""Object Mothers for Storage module domain entities."""

import uuid

from src.modules.storage.domain.entities import StorageFile


class StorageFileMothers:
    """Pre-built StorageFile configurations."""

    @staticmethod
    def pending(
        bucket_name: str = "test-bucket",
        owner_module: str = "catalog",
    ) -> StorageFile:
        """StorageFile just created, not yet processed."""
        return StorageFile.create(
            bucket_name=bucket_name,
            object_key=f"raw_uploads/{owner_module}/{uuid.uuid4().hex}/file",
            content_type="image/png",
            size_bytes=0,
            owner_module=owner_module,
        )

    @staticmethod
    def active(
        bucket_name: str = "test-bucket",
        size_bytes: int = 1024,
    ) -> StorageFile:
        """StorageFile with known size (upload completed)."""
        return StorageFile.create(
            bucket_name=bucket_name,
            object_key=f"processed/catalog/{uuid.uuid4().hex}/image.webp",
            content_type="image/webp",
            size_bytes=size_bytes,
            owner_module="catalog",
        )
