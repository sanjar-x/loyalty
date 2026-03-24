"""Command handler: update an existing supplier's name and/or region."""

import uuid
from dataclasses import dataclass

from src.modules.supplier.domain.exceptions import SupplierNotFoundError
from src.modules.supplier.domain.interfaces import ISupplierRepository
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class UpdateSupplierCommand:
    supplier_id: uuid.UUID
    name: str | None = None
    region: str | None = None


class UpdateSupplierHandler:
    def __init__(
        self,
        supplier_repo: ISupplierRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._supplier_repo = supplier_repo
        self._uow = uow
        self._logger = logger.bind(handler="UpdateSupplierHandler")

    async def handle(self, command: UpdateSupplierCommand) -> None:
        async with self._uow:
            supplier = await self._supplier_repo.get(command.supplier_id)
            if supplier is None:
                raise SupplierNotFoundError(command.supplier_id)

            kwargs = {}
            if command.name is not None:
                kwargs["name"] = command.name
            if command.region is not None:
                kwargs["region"] = command.region

            if kwargs:
                supplier.update(**kwargs)
                await self._supplier_repo.update(supplier)
                self._uow.register_aggregate(supplier)

            await self._uow.commit()
