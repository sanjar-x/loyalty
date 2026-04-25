"""Command handler: reactivate a supplier."""

import uuid
from dataclasses import dataclass

from src.modules.supplier.domain.exceptions import SupplierNotFoundError
from src.modules.supplier.domain.interfaces import ISupplierRepository
from src.shared.cache_keys import bump_storefront_product_generation
from src.shared.interfaces.cache import ICacheService
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class ActivateSupplierCommand:
    supplier_id: uuid.UUID


class ActivateSupplierHandler:
    def __init__(
        self,
        supplier_repo: ISupplierRepository,
        uow: IUnitOfWork,
        cache: ICacheService,
        logger: ILogger,
    ) -> None:
        self._supplier_repo = supplier_repo
        self._uow = uow
        self._cache = cache
        self._logger = logger.bind(handler="ActivateSupplierHandler")

    async def handle(self, command: ActivateSupplierCommand) -> None:
        async with self._uow:
            supplier = await self._supplier_repo.get(command.supplier_id)
            if supplier is None:
                raise SupplierNotFoundError(command.supplier_id)

            supplier.activate()
            await self._supplier_repo.update(supplier)
            self._uow.register_aggregate(supplier)
            await self._uow.commit()

        try:
            await bump_storefront_product_generation(self._cache)
        except Exception as exc:  # pragma: no cover
            self._logger.warning(
                "storefront_cache_invalidation_failed",
                error=str(exc),
                supplier_id=str(command.supplier_id),
            )
