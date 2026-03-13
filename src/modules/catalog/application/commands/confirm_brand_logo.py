# src/modules/catalog/application/commands/confirm_brand_logo.py
import uuid
from dataclasses import dataclass

import structlog

from src.modules.catalog.domain.exceptions import (
    BrandNotFoundError,
    InvalidLogoStateException,
)
from src.modules.catalog.domain.interfaces import IBrandRepository
from src.modules.catalog.domain.value_objects import MediaProcessingStatus
from src.modules.catalog.presentation.tasks import process_brand_logo_task
from src.shared.interfaces.storage import IStorageFacade
from src.shared.interfaces.uow import IUnitOfWork

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class ConfirmBrandLogoUploadCommand:
    brand_id: uuid.UUID
    object_key: str


class ConfirmBrandLogoUploadHandler:
    def __init__(
        self,
        brand_repo: IBrandRepository,
        uow: IUnitOfWork,
        storage_facade: IStorageFacade,
    ):
        self._brand_repo = brand_repo
        self._storage_facade = storage_facade
        self._uow = uow
        self._logger = logger.bind(handler="ConfirmBrandLogoUploadHandler")

    async def handle(self, command: ConfirmBrandLogoUploadCommand) -> None:
        async with self._uow:
            brand = await self._brand_repo.get(command.brand_id)
            if not brand:
                raise BrandNotFoundError(brand_id=command.brand_id)

            # Идемпотентность
            if brand.logo_status in (
                MediaProcessingStatus.PROCESSING,
                MediaProcessingStatus.COMPLETED,
            ):
                self._logger.info(
                    "Бренд уже обрабатывается или активен", brand_id=str(brand.id)
                )
                return
            elif brand.logo_status == MediaProcessingStatus.FAILED:
                # Требуется повторная загрузка с фронтенда (S3 ключ мог протухнуть)
                raise InvalidLogoStateException(
                    brand_id=command.brand_id,
                    current_status=str(brand.logo_status),
                    expected_status=MediaProcessingStatus.PENDING_UPLOAD,
                )

            # 1. ДЕЛЕГИРУЕМ ВЕРИФИКАЦИЮ
            metadata = await self._storage_facade.verify_module_upload(
                module="catalog", entity_id=brand.id, object_key=command.object_key
            )

            # 2. Обновляем статус
            brand.confirm_logo_upload()
            await self._brand_repo.update(brand)

            # 3. Формируем событие, забирая точный S3-ключ из метаданных фасада
            # Коммитим транзакцию ДО отправки задачи в брокер
            await self._uow.commit()

        # Транзакция закрыта. Теперь безопасно вызываем воркер.
        # 4. Прямой вызов TaskIQ через метод .kiq()
        await process_brand_logo_task.kiq(  # type: ignore
            brand_id=brand.id,
            raw_object_key=metadata["object_key"],
        )

        self._logger.info(
            "Бренд переведен в PROCESSING, задача отправлена напрямую в TaskIQ",
            brand_id=str(brand.id),
        )
