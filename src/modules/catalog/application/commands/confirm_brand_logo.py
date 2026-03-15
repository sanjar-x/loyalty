# src/modules/catalog/application/commands/confirm_brand_logo.py
import uuid
from dataclasses import dataclass

import structlog

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

            # 1. Верификация загрузки
            if not brand.logo_file_id:
                from src.shared.exceptions import ValidationError

                raise ValidationError(message="Бренд ожидает загрузку.")

            await self._storage_facade.verify_upload(file_id=brand.logo_file_id)

            # 2. Обновляем статус (внутри генерируется BrandLogoConfirmedEvent)
            brand.confirm_logo_upload()
            await self._brand_repo.update(brand)

            # 3. Регистрируем агрегат — UoW извлечёт события и запишет в Outbox
            self._uow.register_aggregate(brand)

            # 4. Атомарный коммит: бизнес-данные + Outbox в одной транзакции
            await self._uow.commit()

        self._logger.info(
            "Бренд переведен в PROCESSING, событие записано в Outbox",
            brand_id=str(brand.id),
        )
