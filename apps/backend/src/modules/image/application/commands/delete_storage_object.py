"""Delete a storage object — both S3 keys and DB record.

Public application-layer entry point used by:

* :func:`delete_media` route handler in ``presentation/router_admin.py``
* :class:`MediaCleanupAdapter` in the catalog module (cross-module cleanup
  on product / brand image replacement)

Both paths share this handler so the deletion semantics — best-effort S3
removal + soft-delete of the DB row — stay defined in exactly one place.
"""

from __future__ import annotations

import uuid

import structlog

from src.modules.image.domain.interfaces import IBlobStorage, IStorageRepository
from shared.interfaces.uow import IUnitOfWork

logger = structlog.get_logger(__name__)


class DeleteStorageObjectHandler:
    """Best-effort delete of all S3 keys + soft-delete of the DB row.

    Idempotent: calling on an already-deleted or never-existed
    ``storage_object_id`` is a no-op (no exception).
    """

    def __init__(
        self,
        repo: IStorageRepository,
        blob_storage: IBlobStorage,
        uow: IUnitOfWork,
    ) -> None:
        self._repo = repo
        self._blob = blob_storage
        self._uow = uow
        self._log = logger.bind(component="DeleteStorageObjectHandler")

    async def handle(self, storage_object_id: uuid.UUID) -> None:
        storage_file = await self._repo.get_by_id(storage_object_id)
        if storage_file is None:
            return  # idempotent

        keys_to_delete: list[str] = [
            storage_file.object_key,
            f"public/{storage_object_id}.webp",
        ]
        for suffix in ("thumb", "md", "lg"):
            keys_to_delete.append(f"public/{storage_object_id}_{suffix}.webp")

        try:
            await self._blob.delete_objects(keys_to_delete)
        except Exception:
            self._log.warning(
                "S3 batch delete failed (best-effort)",
                storage_object_id=str(storage_object_id),
                keys=keys_to_delete,
                exc_info=True,
            )

        async with self._uow:
            await self._repo.mark_as_deleted(
                storage_file.bucket_name, storage_file.object_key
            )
            await self._uow.commit()

        self._log.info(
            "Storage object deleted",
            storage_object_id=str(storage_object_id),
            keys=keys_to_delete,
        )
