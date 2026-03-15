# src/modules/catalog/application/commands/create_brand.py
import uuid
from dataclasses import dataclass

import structlog

from src.modules.catalog.domain.entities import Brand
from src.modules.catalog.domain.exceptions import BrandSlugConflictError
from src.modules.catalog.domain.interfaces import IBrandRepository
from src.shared.interfaces.storage import IStorageFacade
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
        upload_data = None
        if command.logo:
            upload_data = await self._storage_facade.reserve_upload_slot(
                module="catalog",
                entity_id=uuid.uuid4(),
                filename=command.logo.filename,
                content_type=command.logo.content_type,
            )

        async with self._uow:
            if await self._brand_repo.check_slug_exists(command.slug):
                raise BrandSlugConflictError(slug=command.slug)

            brand = Brand.create(name=command.name, slug=command.slug)
            brand = await self._brand_repo.add(brand)

            if upload_data:
                if upload_data.file_id is None:
                    raise RuntimeError("reserve_upload_slot вернул upload_data без file_id")
                brand.init_logo_upload(file_id=upload_data.file_id)
                await self._brand_repo.update(brand)

            await self._uow.commit()

        self._logger.info("Инициировано создание бренда", brand_id=str(brand.id))

        return CreateBrandResult(
            brand_id=brand.id,
            presigned_upload_url=str(upload_data.url_data) if upload_data else None,
        )
