# src/modules/catalog/application/services/media_processor.py
import io
import uuid

import structlog
from PIL import Image

from src.modules.catalog.domain.interfaces import IBrandRepository
from src.modules.storage.domain.interfaces import IBlobStorage
from src.shared.interfaces.storage import IStorageFacade
from src.shared.interfaces.uow import IUnitOfWork

logger = structlog.get_logger(__name__)


class BrandLogoProcessor:
    def __init__(
        self,
        brand_repo: IBrandRepository,
        storage_facade: IStorageFacade,
        blob_storage: IBlobStorage,
        uow: IUnitOfWork,
    ):
        self._brand_repo = brand_repo
        self._storage_facade = storage_facade
        self._blob_storage = blob_storage
        self._uow = uow
        self._logger = logger.bind(service="BrandLogoProcessor")

    async def process(self, brand_id: uuid.UUID, raw_object_key: str) -> None:
        self._logger.info(
            "Начало обработки логотипа", brand_id=str(brand_id), key=raw_object_key
        )

        async with self._uow:
            brand = await self._brand_repo.get(brand_id)
            if not brand:
                self._logger.error("Бренд не найден", brand_id=str(brand_id))
                return

            try:
                # 1. Загружаем сырой файл
                buffer = io.BytesIO()
                async for chunk in self._blob_storage.download_stream(raw_object_key):
                    buffer.write(chunk)
                buffer.seek(0)

                # 2. Обработка Pillow
                with Image.open(buffer) as img:
                    img.thumbnail((512, 512))
                    output_buffer = io.BytesIO()
                    img.save(output_buffer, format="WEBP", quality=85)
                    output_buffer.seek(0)

                # 3. Загружаем обработанный файл
                public_key = f"public/brands/{brand_id}/logo.webp"

                async def stream_gen():
                    yield output_buffer.getvalue()

                await self._blob_storage.upload_stream(
                    object_name=public_key,
                    data_stream=stream_gen(),
                    content_type="image/webp",
                )

                # 4. Удаляем временный файл
                await self._blob_storage.delete_file(raw_object_key)

                # 5. Регистрируем в Storage Facade
                await self._storage_facade.register_processed_media(
                    module="catalog",
                    entity_id=brand_id,
                    object_key=public_key,
                    content_type="image/webp",
                    size=len(output_buffer.getvalue()),
                )

                # 6. Обновляем статус бренда
                brand.complete_logo_processing()
                await self._brand_repo.update(brand)
                await self._uow.commit()

                self._logger.info("Логотип успешно обработан", brand_id=str(brand_id))

            except Exception:
                self._logger.exception(
                    "Ошибка обработки логотипа", brand_id=str(brand_id)
                )
                brand.fail_logo_processing()
                await self._brand_repo.update(brand)
                await self._uow.commit()
                raise
