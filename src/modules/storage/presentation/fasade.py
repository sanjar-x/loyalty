# src/modules/storage/presentation/facade.py
import uuid
from typing import Any, Dict

import structlog

from src.bootstrap.config import Settings
from src.modules.storage.domain.interfaces import IBlobStorage, IStorageRepository
from src.modules.storage.infrastructure.models import StorageObject
from src.shared.exceptions import ValidationError
from src.shared.interfaces.storage import IStorageFacade, PresignedUploadData
from src.shared.interfaces.uow import IUnitOfWork

logger = structlog.get_logger(__name__)


class StorageFacade(IStorageFacade):
    def __init__(
        self,
        blob_storage: IBlobStorage,
        storage_repo: IStorageRepository,
        uow: IUnitOfWork,
        settings: Settings,
    ):
        self._blob_storage: IBlobStorage = blob_storage
        self._storage_repo: IStorageRepository = storage_repo
        self._uow: IUnitOfWork = uow
        self._settings: Settings = settings
        self._logger = logger.bind(component="StorageFacade")

    async def request_upload(
        self, module: str, entity_id: str | uuid.UUID, filename: str
    ) -> PresignedUploadData:
        file_ext = filename.split(".")[-1] if "." in filename else "bin"

        object_key = f"temp/{module}/{entity_id}/upload.{file_ext}"

        url_data = await self._blob_storage.get_presigned_upload_url(
            object_name=object_key, expiration=3600
        )

        self._logger.info("Сгенерирован presigned URL", object_key=object_key)

        return PresignedUploadData(url_data=url_data, object_key=object_key)

    async def request_direct_upload(
        self,
        module: str,
        entity_id: str | uuid.UUID,
        filename: str,
        content_type: str,
        expire_in: int = 300,
    ) -> PresignedUploadData:
        file_ext = filename.split(".")[-1] if "." in filename else "bin"
        object_key = f"raw_uploads/{module}/{entity_id}/upload_raw.{file_ext}"

        url_str = await self._blob_storage.generate_presigned_put_url(
            object_name=object_key, content_type=content_type, expiration=expire_in
        )

        self._logger.info("Сгенерирован PUT presigned URL", object_key=object_key)
        return PresignedUploadData(url_data=url_str, object_key=object_key)

    async def register_processed_media(
        self,
        module: str,
        entity_id: str | uuid.UUID,
        object_key: str,
        content_type: str,
        size: int,
    ) -> uuid.UUID:
        storage_obj = StorageObject(
            bucket_name=self._settings.S3_BUCKET_NAME,
            object_key=object_key,
            size_bytes=size,
            content_type=content_type,
            owner_module=module,
        )

        async with self._uow:
            await self._storage_repo.add(storage_obj)
            await self._uow.commit()

        self._logger.info("Файл зарегистрирован", object_id=str(storage_obj.id))
        return storage_obj.id

    async def verify_module_upload(
        self, module: str, entity_id: str | uuid.UUID
    ) -> Dict[str, Any]:
        prefix = f"temp/{module}/{entity_id}/"

        list_response = await self._blob_storage.list_objects(prefix=prefix, limit=1)

        if not list_response.get("objects"):
            self._logger.error("Файл не найден при верификации", prefix=prefix)
            raise ValidationError(message="Файл не был загружен в хранилище.")

        actual_object_key = list_response["objects"][0]["key"]
        metadata = await self._blob_storage.get_object_metadata(actual_object_key)

        metadata["object_key"] = actual_object_key

        return metadata
