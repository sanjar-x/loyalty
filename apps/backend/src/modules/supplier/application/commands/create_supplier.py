"""Command handler: create a new supplier."""

import uuid
from dataclasses import dataclass

from src.modules.supplier.domain.entities import Supplier
from src.modules.supplier.domain.interfaces import ISupplierRepository
from src.modules.supplier.domain.value_objects import SupplierType
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class CreateSupplierCommand:
    name: str
    type: SupplierType
    country_code: str
    subdivision_code: str | None = None


@dataclass(frozen=True)
class CreateSupplierResult:
    supplier_id: uuid.UUID


class CreateSupplierHandler:
    def __init__(
        self,
        supplier_repo: ISupplierRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._supplier_repo = supplier_repo
        self._uow = uow
        self._logger = logger.bind(handler="CreateSupplierHandler")

    async def handle(self, command: CreateSupplierCommand) -> CreateSupplierResult:
        async with self._uow:
            supplier = Supplier.create(
                name=command.name,
                supplier_type=command.type,
                country_code=command.country_code,
                subdivision_code=command.subdivision_code,
            )
            await self._supplier_repo.add(supplier)
            self._uow.register_aggregate(supplier)
            await self._uow.commit()

        return CreateSupplierResult(supplier_id=supplier.id)
