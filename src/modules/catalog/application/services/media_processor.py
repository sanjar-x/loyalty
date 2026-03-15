import io
import uuid

import structlog
from PIL import Image

from src.bootstrap.config import Settings
from src.modules.catalog.application.constants import public_logo_key, raw_logo_key
from src.modules.catalog.domain.events import BrandLogoProcessedEvent
from src.modules.catalog.domain.interfaces import IBrandRepository
from src.shared.interfaces.blob_storage import IBlobStorage
from src.shared.interfaces.uow import IUnitOfWork

logger = structlog.get_logger(__name__)

MAX_LOGO_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
MAX_LOGO_DIMENSION = 800


class BrandLogoProcessor:
    def __init__(
        self,
        brand_repo: IBrandRepository,
        blob_storage: IBlobStorage,
        uow: IUnitOfWork,
        settings: Settings,
    ):
        self._brand_repo = brand_repo
        self._blob_storage = blob_storage
        self._uow = uow
        self._settings = settings
        self._logger = logger.bind(service="BrandLogoProcessor")

    async def process(self, brand_id: uuid.UUID) -> None:
        log = self._logger.bind(brand_id=str(brand_id))
        log.info("Начало обработки логотипа")

        # Детерминированные ключи — не зависят от модуля Storage
        raw_key = raw_logo_key(brand_id)
        pub_key = public_logo_key(brand_id)

        try:
            # 1. Загружаем сырой файл напрямую через IBlobStorage
            log.debug("Загрузка файла из временного хранилища...", raw_key=raw_key)
            buffer = io.BytesIO()
            total_size = 0
            async for chunk in self._blob_storage.download_stream(raw_key):
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
            log.debug("Загрузка обработанного файла в S3...", public_key=pub_key)

            async def stream_gen():
                yield output_buffer.getvalue()

            await self._blob_storage.upload_stream(
                object_name=pub_key,
                data_stream=stream_gen(),
                content_type="image/webp",
            )
            log.info("Обработанный файл загружен", public_key=pub_key)

            # 4. Удаляем временный файл
            log.debug("Удаление временного файла из S3...")
            await self._blob_storage.delete_file(raw_key)
            log.debug("Временный файл удален")

            # 5. Обновляем статус бренда
            logo_url = f"{self._settings.S3_PUBLIC_BASE_URL}/{pub_key}"
            log.debug("Обновление статуса бренда в БД...")
            async with self._uow:
                brand = await self._brand_repo.get_for_update(brand_id)
                if brand:
                    brand.complete_logo_processing(url=logo_url)

                    # Генерируем событие для модуля Storage (регистрация файла)
                    brand.add_domain_event(
                        BrandLogoProcessedEvent(
                            brand_id=brand_id,
                            object_key=pub_key,
                            content_type="image/webp",
                            size_bytes=processed_size,
                            aggregate_id=str(brand_id),
                        )
                    )
                    await self._brand_repo.update(brand)
                    self._uow.register_aggregate(brand)
                    await self._uow.commit()
                    log.info("Статус бренда обновлен на COMPLETED")
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
