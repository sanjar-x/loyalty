# src/modules/catalog/application/commands/create_brand.py
import uuid
from dataclasses import dataclass

import structlog

from src.modules.catalog.domain.exceptions import BrandSlugConflictError
from src.modules.catalog.domain.interfaces import IBrandRepository
from src.modules.catalog.infrastructure.models import MediaProcessingStatus
from src.shared.interfaces.storage import IStorageFacade
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
        storage_facade: IStorageFacade,
    ):
        self._brand_repo = brand_repo
        self._uow = uow
        self._storage_facade = storage_facade
        self._logger = logger.bind(handler="CreateBrandHandler")

    async def handle(self, command: CreateBrandCommand) -> CreateBrandResult:
        async with self._uow:
            if await self._brand_repo.check_slug_exists(command.slug):
                raise BrandSlugConflictError(slug=command.slug)

            # 1. Генерируем ID бренда на уровне Application
            brand_id = uuid.uuid4()

            # 2. Делегируем работу с хранилищем Фасаду! Каталог не знает путей S3.
            upload_data = await self._storage_facade.request_upload(
                module="catalog",
                entity_id=brand_id,
                filename=command.logo_filename,
            )

            # 3. Создаем сущность
            new_brand_data = {
                "id": brand_id,
                "name": command.name,
                "slug": command.slug,
                "logo_status": MediaProcessingStatus.PENDING_UPLOAD,
            }

            brand = await self._brand_repo.add(new_brand_data)
            await self._uow.commit()

            self._logger.info("Инициировано создание бренда", brand_id=str(brand_id))

            return CreateBrandResult(
                brand_id=brand.id,
                presigned_post=upload_data.url_data,
                object_key=upload_data.object_key,
            )
