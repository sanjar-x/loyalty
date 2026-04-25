"""
Command handler: reduce or remove items from a booked shipment.

Wraps Yandex's ``POST /request/items/remove`` (3.15) — async.
"""

import uuid
from dataclasses import dataclass

from src.modules.logistics.application.dto import EditTaskSubmittedResult
from src.modules.logistics.domain.exceptions import ShipmentNotFoundError
from src.modules.logistics.domain.interfaces import (
    IShipmentRepository,
    IShippingProviderRegistry,
)
from src.modules.logistics.domain.value_objects import EditItemRemoval, EditTaskKind
from src.shared.exceptions import ValidationError
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class RemoveOrderItemsCommand:
    """Input for reducing item counts on a shipment.

    ``remaining_count = 0`` removes the item entirely.
    """

    shipment_id: uuid.UUID
    removals: tuple[EditItemRemoval, ...]


class RemoveOrderItemsHandler:
    """Reduce / remove items from a booked shipment."""

    def __init__(
        self,
        shipment_repo: IShipmentRepository,
        registry: IShippingProviderRegistry,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._shipment_repo = shipment_repo
        self._registry = registry
        self._uow = uow
        self._logger = logger.bind(handler="RemoveOrderItemsHandler")

    async def handle(self, command: RemoveOrderItemsCommand) -> EditTaskSubmittedResult:
        if not command.removals:
            raise ValidationError(
                message="RemoveOrderItemsCommand requires at least one removal entry.",
                details={"shipment_id": str(command.shipment_id)},
            )

        shipment = await self._shipment_repo.get_by_id(command.shipment_id)
        if shipment is None:
            raise ShipmentNotFoundError(
                details={"shipment_id": str(command.shipment_id)}
            )

        provider = self._registry.get_edit_provider(shipment.provider_code)
        result = await provider.remove_items(
            order_provider_id=shipment.provider_shipment_id or "",
            items=list(command.removals),
        )

        async with self._uow:
            shipment = await self._shipment_repo.get_by_id(command.shipment_id)
            if shipment is None:
                self._logger.error(
                    "Shipment vanished between remove_items submit and persist",
                    shipment_id=str(command.shipment_id),
                    task_id=result.task_id,
                )
                raise ShipmentNotFoundError(
                    details={"shipment_id": str(command.shipment_id)}
                )
            shipment.record_edit_task(
                task_id=result.task_id,
                kind=EditTaskKind.REMOVE_ITEMS,
                initial_status=result.initial_status,
            )
            await self._shipment_repo.update(shipment)
            self._uow.register_aggregate(shipment)
            await self._uow.commit()

        self._logger.info(
            "Remove items task submitted",
            shipment_id=str(shipment.id),
            task_id=result.task_id,
        )
        return EditTaskSubmittedResult(
            shipment_id=shipment.id,
            task_id=result.task_id,
            initial_status=result.initial_status,
        )
