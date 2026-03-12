# src/modules/catalog/application/commands/confirm_brand_logo.py
import uuid
from dataclasses import dataclass

import structlog

from src.modules.catalog.domain.events import BrandLogoUploadConfirmedEvent
from src.modules.catalog.domain.exceptions import BrandNotFoundError
from src.modules.catalog.domain.interfaces import IBrandRepository
from src.modules.catalog.infrastructure.models import MediaProcessingStatus
from src.shared.interfaces.broker import IEventPublisher
from src.shared.interfaces.storage import IStorageFacade
from src.shared.interfaces.uow import IUnitOfWork

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class ConfirmBrandLogoUploadCommand:
    brand_id: uuid.UUID


class ConfirmBrandLogoUploadHandler:
    def __init__(
        self,
        brand_repo: IBrandRepository,
        uow: IUnitOfWork,
        storage_facade: IStorageFacade,  # ИСПРАВЛЕНО: Зависим от Фасада
        publisher: IEventPublisher,
    ):
        self._brand_repo = brand_repo
        self._storage_facade = storage_facade
        self._publisher = publisher
        self._uow = uow
        self._logger = logger.bind(handler="ConfirmBrandLogoUploadHandler")

    async def handle(self, command: ConfirmBrandLogoUploadCommand) -> None:
        async with self._uow:
            brand = await self._brand_repo.get(command.brand_id)
            if not brand:
                raise BrandNotFoundError(brand_id=command.brand_id)

            # Идемпотентность
            if brand.logo_status != MediaProcessingStatus.PENDING_UPLOAD:
                self._logger.warning(
                    "Бренд уже обрабатывается или активен", brand_id=str(brand.id)
                )
                return

            # 1. ДЕЛЕГИРУЕМ ВЕРИФИКАЦИЮ (Каталог ничего не знает про list_objects и S3!)
            metadata = await self._storage_facade.verify_module_upload(
                module="catalog", entity_id=brand.id
            )

            # 2. Обновляем статус
            brand.logo_status = MediaProcessingStatus.PROCESSING

            # 3. Формируем событие, забирая точный S3-ключ из метаданных фасада
            event = BrandLogoUploadConfirmedEvent(
                payload={
                    "brand_id": brand.id,
                    "object_key": metadata["object_key"],
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

            await self._uow.commit()

            self._logger.info(
                "Бренд переведен в PROCESSING, задача отправлена",
                brand_id=str(brand.id),
            )
