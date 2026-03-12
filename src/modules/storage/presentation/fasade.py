# src/modules/storage/presentation/facade.py
import uuid
from typing import Any, Dict

import structlog

from src.modules.storage.domain.interfaces import IBlobStorage
from src.shared.exceptions import ValidationError
from src.shared.interfaces.storage import IStorageFacade, PresignedUploadData

logger = structlog.get_logger(__name__)


class StorageFacade(IStorageFacade):
    def __init__(self, blob_storage: IBlobStorage):
        self._blob_storage: IBlobStorage = blob_storage
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
