import uuid
from dataclasses import dataclass

from src.modules.catalog.domain.entities import Brand
from src.modules.catalog.domain.exceptions import (
    BrandNotFoundError,
    BrandSlugConflictError,
)
from src.modules.catalog.domain.interfaces import IBrandRepository
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class UpdateBrandCommand:
    brand_id: uuid.UUID
    name: str | None = None
    slug: str | None = None


@dataclass(frozen=True)
class UpdateBrandResult:
    id: uuid.UUID
    name: str
    slug: str
    logo_url: str | None = None
    logo_status: str | None = None


class UpdateBrandHandler:
    def __init__(
        self,
        brand_repo: IBrandRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ):
        self._brand_repo = brand_repo
        self._uow = uow
        self._logger = logger.bind(handler="UpdateBrandHandler")

    async def handle(self, command: UpdateBrandCommand) -> UpdateBrandResult:
        async with self._uow:
            brand: Brand | None = await self._brand_repo.get_for_update(
                command.brand_id
            )
            if brand is None:
                raise BrandNotFoundError(brand_id=command.brand_id)

            if command.slug is not None and command.slug != brand.slug:
                if await self._brand_repo.check_slug_exists_excluding(
                    command.slug, command.brand_id
                ):
                    raise BrandSlugConflictError(slug=command.slug)

            brand.update(name=command.name, slug=command.slug)
            await self._brand_repo.update(brand)
            self._uow.register_aggregate(brand)
            await self._uow.commit()

        self._logger.info("Бренд обновлён", brand_id=str(brand.id))

        return UpdateBrandResult(
            id=brand.id,
            name=brand.name,
            slug=brand.slug,
            logo_url=brand.logo_url,
            logo_status=brand.logo_status.value if brand.logo_status else None,
        )
