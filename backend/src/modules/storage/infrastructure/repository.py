"""Storage repository implementation.

Provides the concrete SQLAlchemy-based implementation of
``IStorageRepository``. Uses the Data Mapper pattern to translate
between the ``StorageObject`` ORM model and the ``StorageFile``
domain entity.
"""

import uuid
from collections.abc import Sequence

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.storage.domain.entities import StorageFile
from src.modules.storage.domain.interfaces import IStorageRepository
from src.modules.storage.infrastructure.models import StorageObject

logger = structlog.get_logger(__name__)


class StorageObjectRepository(IStorageRepository):
    """Repository for managing S3 object metadata.

    Implements the Data Mapper pattern: all public methods accept and
    return ``StorageFile`` domain entities while persisting data through
    the ``StorageObject`` ORM model.

    Args:
        session: An async SQLAlchemy session bound to the current
            unit of work.
    """

    def __init__(self, session: AsyncSession):
        self._session = session
        self._logger = logger.bind(component="storage_object_repository")

    # -- Data Mapper: ORM <-> Domain --

    @staticmethod
    def _to_domain(orm: StorageObject) -> StorageFile:
        """Map an ORM model instance to a domain entity.

        Args:
            orm: The ``StorageObject`` ORM instance.

        Returns:
            The corresponding ``StorageFile`` domain entity.
        """
        return StorageFile(
            id=orm.id,
            bucket_name=orm.bucket_name,
            object_key=orm.object_key,
            content_type=orm.content_type,
            size_bytes=orm.size_bytes,
            is_latest=orm.is_latest,
            owner_module=orm.owner_module,
            version_id=orm.version_id,
            etag=orm.etag,
            content_encoding=orm.content_encoding,
            cache_control=orm.cache_control,
            created_at=orm.created_at,
            last_modified_in_s3=orm.last_modified_in_s3,
        )

    @staticmethod
    def _to_orm(entity: StorageFile) -> StorageObject:
        """Map a domain entity to an ORM model instance.

        Args:
            entity: The ``StorageFile`` domain entity.

        Returns:
            The corresponding ``StorageObject`` ORM instance.
        """
        return StorageObject(
            id=entity.id,
            bucket_name=entity.bucket_name,
            object_key=entity.object_key,
            content_type=entity.content_type,
            size_bytes=entity.size_bytes,
            is_latest=entity.is_latest,
            owner_module=entity.owner_module,
            version_id=entity.version_id,
            etag=entity.etag,
            content_encoding=entity.content_encoding,
            cache_control=entity.cache_control,
            last_modified_in_s3=entity.last_modified_in_s3,
        )

    # -- Repository methods --

    async def add(self, storage_file: StorageFile) -> None:
        """Add a new storage file record (object version).

        Args:
            storage_file: The domain entity to persist.
        """
        orm = self._to_orm(storage_file)
        self._session.add(orm)

    async def update(self, storage_file: StorageFile) -> None:
        """Update an existing storage file record by ID.

        If the record does not exist in the session, the update is
        silently skipped.

        Args:
            storage_file: The domain entity with updated field values.
        """
        orm = await self._session.get(StorageObject, storage_file.id)
        if orm is None:
            return
        orm.object_key = storage_file.object_key
        orm.content_type = storage_file.content_type
        orm.size_bytes = storage_file.size_bytes
        orm.is_latest = storage_file.is_latest
        orm.owner_module = storage_file.owner_module
        orm.version_id = storage_file.version_id
        orm.etag = storage_file.etag
        orm.content_encoding = storage_file.content_encoding
        orm.cache_control = storage_file.cache_control
        orm.last_modified_in_s3 = storage_file.last_modified_in_s3

    async def get_by_key(self, key: uuid.UUID) -> StorageFile | None:
        """Retrieve file metadata by its internal UUID.

        Typically used by other modules to look up a file they hold
        a reference to.

        Args:
            key: The internal UUID of the storage file.

        Returns:
            The matching ``StorageFile``, or ``None`` if not found.
        """
        orm = await self._session.get(StorageObject, key)
        return self._to_domain(orm) if orm else None

    async def get_active_by_key(
        self, bucket_name: str, object_key: str
    ) -> StorageFile | None:
        """Retrieve the current active version of a file by its S3 path.

        Args:
            bucket_name: The S3 bucket name.
            object_key: The full object key within the bucket.

        Returns:
            The active ``StorageFile``, or ``None`` if not found.
        """
        stmt = select(StorageObject).where(
            StorageObject.bucket_name == bucket_name,
            StorageObject.object_key == object_key,
            StorageObject.is_latest.is_(True),
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def get_all_versions(
        self, bucket_name: str, object_key: str
    ) -> Sequence[StorageFile]:
        """Retrieve the full version history of a file, newest first.

        Args:
            bucket_name: The S3 bucket name.
            object_key: The full object key within the bucket.

        Returns:
            A sequence of ``StorageFile`` entities ordered by creation
            date descending.
        """
        stmt = (
            select(StorageObject)
            .where(
                StorageObject.bucket_name == bucket_name,
                StorageObject.object_key == object_key,
            )
            .order_by(StorageObject.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return [self._to_domain(orm) for orm in result.scalars().all()]

    async def deactivate_previous_versions(
        self, bucket_name: str, object_key: str
    ) -> None:
        """Deactivate all existing active versions of a file.

        This **must** be called before ``session.flush()`` when adding a
        new active version, to avoid violating the
        ``uix_storage_active_object`` unique partial index.

        Args:
            bucket_name: The S3 bucket name.
            object_key: The full object key within the bucket.
        """
        stmt = (
            update(StorageObject)
            .where(
                StorageObject.bucket_name == bucket_name,
                StorageObject.object_key == object_key,
                StorageObject.is_latest.is_(True),
            )
            .values(is_latest=False)
        )
        result = await self._session.execute(stmt)

        if result.rowcount > 0:
            self._logger.debug(
                "Previous file versions deactivated",
                bucket_name=bucket_name,
                object_key=object_key,
                deactivated_count=result.rowcount,
            )

    async def mark_as_deleted(self, bucket_name: str, object_key: str) -> None:
        """Soft-delete a file by deactivating all its versions.

        Emulates an S3 delete marker: the file becomes inaccessible as
        an active object, but its records are preserved in the database
        for auditing.

        Args:
            bucket_name: The S3 bucket name.
            object_key: The full object key within the bucket.
        """
        await self.deactivate_previous_versions(bucket_name, object_key)
        self._logger.info(
            "File marked as deleted", bucket_name=bucket_name, object_key=object_key
        )
