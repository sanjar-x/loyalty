# src/modules/catalog/application/commands/create_brand.py
import uuid
from dataclasses import dataclass

import structlog

from src.modules.catalog.domain.exceptions import BrandSlugConflictError
from src.modules.catalog.domain.interfaces import IBrandRepository
from src.modules.catalog.infrastructure.models import (
    MediaProcessingStatus,  # Добавлен импорт Enum
)
from src.shared.interfaces.storage import IS3torageService
from src.shared.interfaces.uow import IUnitOfWork

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class CreateBrandCommand:
    name: str
    slug: str
    logo_filename: str
    logo_content_type: str


@dataclass(frozen=True)
class CreateBrandResult:
    brand_id: uuid.UUID
    presigned_post: dict
    object_key: str


class CreateBrandHandler:
    def __init__(
        self,
        brand_repo: IBrandRepository,
        uow: IUnitOfWork,
        storage_service: IS3torageService,
    ):
        self._brand_repo = brand_repo
        self._uow = uow
        self._storage_service = storage_service
        self._logger = logger.bind(handler="CreateBrandHandler")

    async def handle(self, command: CreateBrandCommand) -> CreateBrandResult:
        async with self._uow:
            # 1. Проверка бизнес-правил
            if await self._brand_repo.check_slug_exists(command.slug):
                raise BrandSlugConflictError(slug=command.slug)

            # Используем uuid4 для brand_id
            brand_id = uuid.uuid4()

            # 2. ДЕТЕРМИНИРОВАННЫЙ КЛЮЧ
            # Мы не сохраняем его в БД, поэтому он всегда вычисляется одинаково:
            object_key = f"temp/brands/{brand_id}/logo_upload"

            # 3. Подготовка DTO строго по полям модели Brand
            new_brand_data = {
                "id": brand_id,
                "name": command.name,
                "slug": command.slug,
                "logo_status": MediaProcessingStatus.PENDING_UPLOAD,  # Используем Enum!
            }

            brand = await self._brand_repo.add(new_brand_data)

            # 4. Генерация ссылки
            presigned_data = await self._storage_service.get_presigned_upload_url(
                object_name=object_key,
                expiration=3600,
            )

            await self._uow.commit()
            self._logger.info("Инициировано создание бренда", brand_id=str(brand_id))

            return CreateBrandResult(
                brand_id=brand.id, presigned_post=presigned_data, object_key=object_key
            )
