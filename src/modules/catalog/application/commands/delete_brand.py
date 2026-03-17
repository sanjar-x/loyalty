import uuid
from dataclasses import dataclass

from src.modules.catalog.domain.exceptions import BrandNotFoundError
from src.modules.catalog.domain.interfaces import IBrandRepository
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class DeleteBrandCommand:
    brand_id: uuid.UUID


class DeleteBrandHandler:
    def __init__(
        self,
        brand_repo: IBrandRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ):
        self._brand_repo = brand_repo
        self._uow = uow
        self._logger = logger.bind(handler="DeleteBrandHandler")

    async def handle(self, command: DeleteBrandCommand) -> None:
        async with self._uow:
            brand = await self._brand_repo.get(command.brand_id)
            if brand is None:
                raise BrandNotFoundError(brand_id=command.brand_id)

            self._uow.register_aggregate(brand)
            await self._brand_repo.delete(command.brand_id)
            await self._uow.commit()

        self._logger.info("Бренд удалён", brand_id=str(command.brand_id))
