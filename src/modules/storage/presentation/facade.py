# src/modules/storage/presentation/facade.py
import uuid
from typing import Any

from src.modules.storage.domain.entities import StorageFile
from src.modules.storage.domain.interfaces import IStorageRepository
from src.shared.exceptions import ValidationError
from src.shared.interfaces.blob_storage import IBlobStorage
from src.shared.interfaces.config import IStorageConfig
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.storage import IStorageFacade, PresignedUploadData
from src.shared.interfaces.uow import IUnitOfWork


class StorageFacade(IStorageFacade):
    def __init__(
        self,
        blob_storage: IBlobStorage,
        storage_repo: IStorageRepository,
        uow: IUnitOfWork,
        settings: IStorageConfig,
        logger: ILogger,
    ):
        self._blob_storage: IBlobStorage = blob_storage
        self._storage_repo: IStorageRepository = storage_repo
        self._uow: IUnitOfWork = uow
        self._settings: IStorageConfig = settings
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
        storage_file = StorageFile.create(
            bucket_name=self._settings.S3_BUCKET_NAME,
            object_key=object_key,
            content_type=content_type,
            size_bytes=size,
            owner_module=module,
        )

        async with self._uow:
            await self._storage_repo.add(storage_file)
            await self._uow.commit()

        self._logger.info("Файл зарегистрирован", object_key=str(storage_file.id))
        return storage_file.id

    async def _check_file_in_s3(self, object_key: str) -> dict[str, Any]:
        """Проверяет наличие файла в S3 и возвращает его метаданные."""
        metadata = await self._blob_storage.get_object_metadata(object_key)
        if not metadata:
            self._logger.error("Файл не найден в S3", object_key=object_key)
            raise ValidationError(message="Файл не был загружен в хранилище.")
        metadata["object_key"] = object_key
        return metadata

    async def verify_module_upload(
        self, module: str, entity_id: str | uuid.UUID, object_key: str
    ) -> dict[str, Any]:
        return await self._check_file_in_s3(object_key)

    async def reserve_upload_slot(
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

        storage_file = StorageFile.create(
            bucket_name=self._settings.S3_BUCKET_NAME,
            object_key=object_key,
            content_type=content_type,
            owner_module=module,
        )

        async with self._uow:
            await self._storage_repo.add(storage_file)
            await self._uow.commit()

        self._logger.info(
            "Зарезервирован слот для загрузки",
            object_key=object_key,
            file_id=str(storage_file.id),
        )

        return PresignedUploadData(
            url_data=url_str,
            object_key=object_key,
            file_id=storage_file.id,
        )

    async def verify_upload(self, file_id: uuid.UUID) -> dict[str, Any]:
        async with self._uow:
            storage_file = await self._storage_repo.get_by_key(file_id)

        if not storage_file:
            raise ValidationError(message="Запись о файле не найдена.")

        return await self._check_file_in_s3(storage_file.object_key)

    async def update_object_metadata(
        self,
        file_id: uuid.UUID,
        object_key: str,
        size_bytes: int,
        content_type: str,
    ) -> None:
        async with self._uow:
            storage_file = await self._storage_repo.get_by_key(file_id)
            if not storage_file:
                raise ValidationError(message="Запись о файле не найдена.")

            storage_file.object_key = object_key
            storage_file.size_bytes = size_bytes
            storage_file.content_type = content_type

            await self._storage_repo.update(storage_file)
            await self._uow.commit()

        self._logger.info("Метаданные файла обновлены", file_id=str(file_id))
