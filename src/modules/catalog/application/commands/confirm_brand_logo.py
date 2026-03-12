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
        storage_service: IS3torageService,
        publisher: IEventPublisher,
    ):
        self._brand_repo: IBrandRepository = brand_repo
        self._storage_service: IS3torageService = storage_service
        self._publisher: IEventPublisher = publisher
        self._uow: IUnitOfWork = uow
        self._logger = logger.bind(handler="ConfirmBrandLogoUploadHandler")

    async def handle(self, command: ConfirmBrandLogoUploadCommand) -> None:
        async with self._uow:
            brand = await self._brand_repo.get(command.brand_id)
            if not brand:
                raise BrandNotFoundError(brand_id=command.brand_id)

            if brand.logo_status != MediaProcessingStatus.PENDING_UPLOAD:
                self._logger.warning(
                    "Бренд уже обрабатывается или активен", brand_id=str(brand.id)
                )
                return

            prefix = f"temp/brands/{brand.id}/logo_upload"
            list_response = await self._storage_service.list_objects(
                prefix=prefix, limit=1
            )

            if not list_response.get("objects"):
                self._logger.error(
                    "Файл не найден в S3 при подтверждении", prefix=prefix
                )
                raise ValidationError(message="Файл не был загружен в хранилище.")

            actual_object_key = list_response["objects"][0]["key"]
            metadata = await self._storage_service.get_object_metadata(
                actual_object_key
            )

            brand.logo_status = MediaProcessingStatus.PROCESSING

            event = BrandLogoUploadConfirmedEvent(
                payload={
                    "brand_id": brand.id,
                    "object_key": actual_object_key,
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
