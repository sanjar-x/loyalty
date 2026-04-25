"""Upsert a ``SupplierType → PricingContext`` mapping (PUT semantics)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from src.modules.pricing.domain.entities.supplier_type_context_mapping import (
    SupplierTypeContextMapping,
)
from src.modules.pricing.domain.exceptions import (
    PricingContextNotFoundError,
)
from src.modules.pricing.domain.interfaces import (
    IPricingContextRepository,
    ISupplierTypeContextMappingRepository,
)
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class UpsertSupplierTypeContextMappingCommand:
    supplier_type: str
    context_id: uuid.UUID
    actor_id: uuid.UUID


@dataclass(frozen=True)
class UpsertSupplierTypeContextMappingResult:
    mapping_id: uuid.UUID
    supplier_type: str
    context_id: uuid.UUID
    version_lock: int
    created: bool


class UpsertSupplierTypeContextMappingHandler:
    """Create or re-target a ``supplier_type → context`` mapping.

    Writes require the target context to exist (404 otherwise). They are NOT
    blocked when the context is frozen/inactive: this is meta-configuration,
    not a pricing operation.
    """

    def __init__(
        self,
        mapping_repo: ISupplierTypeContextMappingRepository,
        context_repo: IPricingContextRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._mapping_repo = mapping_repo
        self._context_repo = context_repo
        self._uow = uow
        self._logger = logger.bind(
            handler="UpsertSupplierTypeContextMappingHandler"
        )

    async def handle(
        self, command: UpsertSupplierTypeContextMappingCommand
    ) -> UpsertSupplierTypeContextMappingResult:
        async with self._uow:
            ctx = await self._context_repo.get_by_id(command.context_id)
            if ctx is None:
                raise PricingContextNotFoundError(context_id=command.context_id)

            existing = await self._mapping_repo.get_by_supplier_type(
                command.supplier_type
            )

            if existing is not None:
                existing.change_context(
                    new_context_id=command.context_id,
                    actor_id=command.actor_id,
                )
                updated = await self._mapping_repo.update(existing)
                self._uow.register_aggregate(existing)
                await self._uow.commit()
                self._logger.info(
                    "pricing_supplier_type_mapping_updated",
                    mapping_id=str(updated.id),
                    supplier_type=updated.supplier_type,
                    context_id=str(updated.context_id),
                )
                return UpsertSupplierTypeContextMappingResult(
                    mapping_id=updated.id,
                    supplier_type=updated.supplier_type,
                    context_id=updated.context_id,
                    version_lock=updated.version_lock,
                    created=False,
                )

            mapping = SupplierTypeContextMapping.create(
                supplier_type=command.supplier_type,
                context_id=command.context_id,
                actor_id=command.actor_id,
            )
            added = await self._mapping_repo.add(mapping)
            self._uow.register_aggregate(mapping)
            await self._uow.commit()
            self._logger.info(
                "pricing_supplier_type_mapping_created",
                mapping_id=str(added.id),
                supplier_type=added.supplier_type,
                context_id=str(added.context_id),
            )
            return UpsertSupplierTypeContextMappingResult(
                mapping_id=added.id,
                supplier_type=added.supplier_type,
                context_id=added.context_id,
                version_lock=added.version_lock,
                created=True,
            )


__all__: list[Any] = [
    "UpsertSupplierTypeContextMappingCommand",
    "UpsertSupplierTypeContextMappingHandler",
    "UpsertSupplierTypeContextMappingResult",
]
