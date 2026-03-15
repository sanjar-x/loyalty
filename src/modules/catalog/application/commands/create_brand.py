# src/modules/catalog/application/commands/create_brand.py
import uuid
from dataclasses import dataclass

import structlog

from src.bootstrap.config import Settings
from src.modules.catalog.application.constants import raw_logo_key
from src.modules.catalog.domain.entities import Brand
from src.modules.catalog.domain.exceptions import BrandSlugConflictError
from src.modules.catalog.domain.interfaces import IBrandRepository
from src.shared.interfaces.blob_storage import IBlobStorage
from src.shared.interfaces.uow import IUnitOfWork

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class LogoMetadata:
    filename: str
    content_type: str
    size: int | None = None


@dataclass(frozen=True)
class CreateBrandCommand:
    name: str
    slug: str
    logo: LogoMetadata | None = None


@dataclass(frozen=True)
class CreateBrandResult:
    brand_id: uuid.UUID
    presigned_upload_url: str | None = None
    object_key: str | None = None


class CreateBrandHandler:
    def __init__(
        self,
        brand_repo: IBrandRepository,
        uow: IUnitOfWork,
        blob_storage: IBlobStorage,
        settings: Settings,
    ):
        self._brand_repo = brand_repo
        self._uow = uow
        self._blob_storage = blob_storage
        self._settings = settings
        self._logger = logger.bind(handler="CreateBrandHandler")

    async def handle(self, command: CreateBrandCommand) -> CreateBrandResult:
        async with self._uow:
            if await self._brand_repo.check_slug_exists(command.slug):
                raise BrandSlugConflictError(slug=command.slug)

            brand = Brand.create(name=command.name, slug=command.slug)
            brand = await self._brand_repo.add(brand)

            presigned_url: str | None = None
            object_key: str | None = None

            if command.logo:
                # Детерминированный ключ — не зависит от модуля Storage
                object_key = raw_logo_key(brand.id)

                # Stateless: генерация URL без записи в БД
                presigned_url = await self._blob_storage.generate_presigned_put_url(
                    object_name=object_key,
                    content_type=command.logo.content_type,
                )

                # Агрегат генерирует BrandCreatedEvent через Outbox
                brand.init_logo_upload(
                    object_key=object_key,
                    content_type=command.logo.content_type,
                )
                await self._brand_repo.update(brand)

            # Регистрируем агрегат — UoW запишет события в Outbox
            self._uow.register_aggregate(brand)
            await self._uow.commit()

        self._logger.info("Бренд создан", brand_id=str(brand.id))

        return CreateBrandResult(
            brand_id=brand.id,
            presigned_upload_url=presigned_url,
            object_key=object_key,
        )
