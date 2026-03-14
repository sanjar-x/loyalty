import io
import uuid

import structlog
from PIL import Image

from src.bootstrap.config import Settings
from src.modules.catalog.domain.interfaces import IBrandRepository
from src.shared.interfaces.blob_storage import IBlobStorage
from src.shared.interfaces.storage import IStorageFacade
from src.shared.interfaces.uow import IUnitOfWork

logger = structlog.get_logger(__name__)

MAX_LOGO_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
MAX_LOGO_DIMENSION = 800


class BrandLogoProcessor:
    def __init__(
        self,
        brand_repo: IBrandRepository,
        storage_facade: IStorageFacade,
        blob_storage: IBlobStorage,
        uow: IUnitOfWork,
        settings: Settings,
    ):
        self._brand_repo = brand_repo
        self._storage_facade = storage_facade
        self._blob_storage = blob_storage
        self._uow = uow
        self._settings = settings
        self._logger = logger.bind(service="BrandLogoProcessor")

    async def process(self, brand_id: uuid.UUID) -> None:
        log = self._logger.bind(brand_id=str(brand_id))
        log.info("Начало обработки логотипа")

        async with self._uow:
            brand = await self._brand_repo.get(brand_id)
            if not brand or not brand.logo_file_id:
                log.error("Бренд или ID файла не найдены")
                return

            # Получаем StorageObject через фасад (или репо)
            storage_metadata = await self._storage_facade.verify_upload(
                brand.logo_file_id
            )
            raw_object_key = storage_metadata["object_key"]
            log = log.bind(raw_key=raw_object_key)

        try:
            # 1. Загружаем сырой файл
            log.debug("Загрузка файла из временного хранилища...")
            buffer = io.BytesIO()
            total_size = 0
            async for chunk in self._blob_storage.download_stream(raw_object_key):
                buffer.write(chunk)
                total_size += len(chunk)
                if total_size > MAX_LOGO_SIZE_BYTES:
                    raise ValueError(f"Файл превышает лимит {MAX_LOGO_SIZE_BYTES} байт")
            buffer.seek(0)
            log.info("Файл успешно загружен в буфер", size_bytes=total_size)

            # 2. Конвертация в WebP с ресайзом через Pillow
            log.debug("Конвертация изображения в WebP (Pillow)...")
            output_buffer = io.BytesIO()
            with Image.open(buffer) as img:
                img = img.convert("RGBA")
                img.thumbnail(
                    (MAX_LOGO_DIMENSION, MAX_LOGO_DIMENSION),
                    Image.Resampling.LANCZOS,
                )
                img.save(output_buffer, format="WEBP", quality=85)
            output_buffer.seek(0)
            processed_size = len(output_buffer.getvalue())
            log.info("Изображение конвертировано", processed_size=processed_size)

            # 3. Загружаем обработанный файл
            public_key = f"public/brands/{brand_id}/logo.webp"
            log.debug("Загрузка обработанного файла в S3...", public_key=public_key)

            async def stream_gen():
                yield output_buffer.getvalue()

            await self._blob_storage.upload_stream(
                object_name=public_key,
                data_stream=stream_gen(),
                content_type="image/webp",
            )
            log.info("Обработанный файл загружен", public_key=public_key)

            # 4. Удаляем временный файл
            log.debug("Удаление временного файла из S3...")
            await self._blob_storage.delete_file(raw_object_key)
            log.debug("Временный файл удален")

            # 5. Обновляем Storage Object (вместо регистрации нового)
            log.debug("Обновление метаданных в Storage Facade...")
            await self._storage_facade.update_object_metadata(
                file_id=brand.logo_file_id,
                object_key=public_key,
                content_type="image/webp",
                size_bytes=processed_size,
            )
            log.info("Запись файла обновлена в реестре")
            file_id = brand.logo_file_id

            # 6. Обновляем статус бренда
            logo_url = f"{self._settings.S3_PUBLIC_BASE_URL}/{public_key}"
            log.debug("Обновление статуса бренда в БД...")
            async with self._uow:
                brand = await self._brand_repo.get(brand_id)
                if brand:
                    brand.complete_logo_processing(file_id=file_id, url=logo_url)
                    await self._brand_repo.update(brand)
                    await self._uow.commit()
                    log.info("Статус бренда обновлен на SUCCESS")
                else:
                    log.warning("Бренд исчез на этапе финального обновления")

            log.info("Процесс обработки полностью завершен")

        except Exception as e:
            log.exception("Критическая ошибка при обработке логотипа", error=str(e))

            log.info("Попытка перевести бренд в статус ошибки...")
            async with self._uow:
                brand = await self._brand_repo.get(brand_id)
                if brand:
                    brand.fail_logo_processing()
                    await self._brand_repo.update(brand)
                    await self._uow.commit()
                    log.warning("Статус бренда изменен на FAILED")
            raise
