"""Delete a ``SupplierType → PricingContext`` mapping."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from src.modules.pricing.domain.exceptions import (
    SupplierTypeContextMappingNotFoundError,
)
from src.modules.pricing.domain.interfaces import (
    ISupplierTypeContextMappingRepository,
)
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class DeleteSupplierTypeContextMappingCommand:
    supplier_type: str
    actor_id: uuid.UUID


class DeleteSupplierTypeContextMappingHandler:
    """Hard-delete by ``supplier_type``; 404 if absent."""

    def __init__(
        self,
        mapping_repo: ISupplierTypeContextMappingRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._mapping_repo = mapping_repo
        self._uow = uow
        self._logger = logger.bind(
            handler="DeleteSupplierTypeContextMappingHandler"
        )

    async def handle(
        self, command: DeleteSupplierTypeContextMappingCommand
    ) -> None:
        async with self._uow:
            existing = await self._mapping_repo.get_by_supplier_type(
                command.supplier_type
            )
            if existing is None:
                raise SupplierTypeContextMappingNotFoundError(
                    supplier_type=command.supplier_type
                )

            existing.mark_deleted(actor_id=command.actor_id)
            self._uow.register_aggregate(existing)
            await self._mapping_repo.delete(existing.id)
            await self._uow.commit()
            self._logger.info(
                "pricing_supplier_type_mapping_deleted",
                mapping_id=str(existing.id),
                supplier_type=existing.supplier_type,
                context_id=str(existing.context_id),
            )
