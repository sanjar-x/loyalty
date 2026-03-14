# src/modules/catalog/application/commands/confirm_brand_logo.py
import uuid
from dataclasses import dataclass

import structlog

from src.modules.catalog.application.tasks import process_brand_logo_task
from src.modules.catalog.domain.exceptions import (
    BrandNotFoundError,
)
from src.modules.catalog.domain.interfaces import IBrandRepository
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

            # 1. ДЕЛЕГИРУЕМ ВЕРИФИКАЦИЮ
            if not brand.logo_file_id:
                from src.shared.exceptions import ValidationError

                raise ValidationError(message="Бренд ожидает загрузку.")

            await self._storage_facade.verify_upload(file_id=brand.logo_file_id)

            # 2. Обновляем статус
            brand.confirm_logo_upload()
            await self._brand_repo.update(brand)

            # 3. Коммитим транзакцию ДО отправки задачи в брокер
            await self._uow.commit()

        # Транзакция закрыта. Теперь безопасно вызываем воркер.
        # 4. Прямой вызов TaskIQ через метод .kiq()
        try:
            await process_brand_logo_task.kiq(brand_id=brand.id)  # type: ignore
        except Exception:
            self._logger.exception(
                "Не удалось поставить задачу в брокер, откат статуса бренда",
                brand_id=str(brand.id),
            )
            async with self._uow:
                brand.revert_logo_upload()
                await self._brand_repo.update(brand)
                await self._uow.commit()
            raise

        self._logger.info(
            "Бренд переведен в PROCESSING, задача отправлена в TaskIQ",
            brand_id=str(brand.id),
        )
