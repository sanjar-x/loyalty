"""Command handler: update an existing supplier."""

import uuid
from dataclasses import dataclass, field

from src.modules.supplier.domain.exceptions import SupplierNotFoundError
from src.modules.supplier.domain.interfaces import ISupplierRepository
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork

_UNSET = object()


@dataclass(frozen=True)
class UpdateSupplierCommand:
    supplier_id: uuid.UUID
    name: str | None = None
    country_code: str | None = None
    # Use _UNSET sentinel to distinguish "not provided" from "set to None" (clear).
    subdivision_code: str | None | object = field(default=_UNSET)


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

            kwargs: dict = {}
            if command.name is not None:
                kwargs["name"] = command.name
            if command.country_code is not None:
                kwargs["country_code"] = command.country_code
            if command.subdivision_code is not _UNSET:
                kwargs["subdivision_code"] = command.subdivision_code

            if kwargs:
                supplier.update(**kwargs)
                await self._supplier_repo.update(supplier)
                self._uow.register_aggregate(supplier)

            await self._uow.commit()
