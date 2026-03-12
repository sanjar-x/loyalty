# src/modules/catalog/application/commands/confirm_brand_logo.py
import uuid
from dataclasses import dataclass

import structlog

from src.modules.catalog.domain.events import BrandLogoUploadConfirmedEvent
from src.modules.catalog.domain.exceptions import BrandNotFoundError
from src.modules.catalog.domain.interfaces import IBrandRepository
from src.modules.catalog.infrastructure.models import MediaProcessingStatus
from src.shared.exceptions import ValidationError
from src.shared.interfaces.broker import IEventPublisher
from src.shared.interfaces.storage import IS3torageService

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class ConfirmBrandLogoUploadCommand:
    brand_id: uuid.UUID


class ConfirmBrandLogoUploadHandler:
    def __init__(
        self,
        brand_repo: IBrandRepository,
        storage_service: IS3torageService,
        publisher: IEventPublisher,
    ):
        self._brand_repo: IBrandRepository = brand_repo
        self._storage_service: IS3torageService = storage_service
        self._publisher: IEventPublisher = publisher
        self._logger = logger.bind(handler="ConfirmBrandLogoUploadHandler")

    async def handle(self, command: ConfirmBrandLogoUploadCommand) -> None:
        brand = await self._brand_repo.get(command.brand_id)
        if not brand:
            raise BrandNotFoundError(brand_id=command.brand_id)

        # 1. Проверяем статус строго через Enum поля logo_status
        if brand.logo_status != MediaProcessingStatus.PENDING_UPLOAD:
            self._logger.warning(
                "Бренд уже активен или логотип подтвержден", brand_id=str(brand.id)
            )
            return

        # 2. Вычисляем тот же самый детерминированный ключ
        object_key = f"temp/brands/{brand.id}/logo_upload"

        # 3. Валидация файла в S3
        exists = await self._storage_service.object_exists(object_key)
        if not exists:
            self._logger.error("Файл не найден в S3 при подтверждении", key=object_key)
            raise ValidationError(message="Файл не был загружен в хранилище.")

        metadata = await self._storage_service.get_object_metadata(object_key)

        event = BrandLogoUploadConfirmedEvent(
            payload={
                "brand_id": brand.id,
                "object_key": object_key,
                "content_type": metadata.get(
                    "content_type", "application/octet-stream"
                ),
            }
        )

        await self._publisher.publish(
            exchange_name="catalog.events",
            routing_key="brand.logo.uploaded",
            event=event,
        )

        self._logger.info(
            "Отправлена задача на обработку логотипа бренда", brand_id=str(brand.id)
        )
