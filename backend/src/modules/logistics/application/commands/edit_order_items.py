"""
Command handler: replace per-item article + marking codes for a shipment.

Wraps Yandex's ``POST /request/items-instances/edit`` (3.14) — async.
"""

import uuid
from dataclasses import dataclass

from src.modules.logistics.application.dto import EditTaskSubmittedResult
from src.modules.logistics.domain.exceptions import ShipmentNotFoundError
from src.modules.logistics.domain.interfaces import (
    IShipmentRepository,
    IShippingProviderRegistry,
)
from src.modules.logistics.domain.value_objects import EditItemMarking
from src.shared.interfaces.logger import ILogger


@dataclass(frozen=True)
class EditOrderItemsCommand:
    """Input for editing item articles / marking codes."""

    shipment_id: uuid.UUID
    items: tuple[EditItemMarking, ...]


class EditOrderItemsHandler:
    """Patch articles / marking codes for the items of a shipment."""

    def __init__(
        self,
        shipment_repo: IShipmentRepository,
        registry: IShippingProviderRegistry,
        logger: ILogger,
    ) -> None:
        self._shipment_repo = shipment_repo
        self._registry = registry
        self._logger = logger.bind(handler="EditOrderItemsHandler")

    async def handle(self, command: EditOrderItemsCommand) -> EditTaskSubmittedResult:
        if not command.items:
            raise ValueError("EditOrderItemsCommand requires at least one item.")

        shipment = await self._shipment_repo.get_by_id(command.shipment_id)
        if shipment is None:
            raise ShipmentNotFoundError(
                details={"shipment_id": str(command.shipment_id)}
            )

        provider = self._registry.get_edit_provider(shipment.provider_code)
        result = await provider.edit_items_instances(
            order_provider_id=shipment.provider_shipment_id or "",
            items=list(command.items),
        )
        self._logger.info(
            "Edit items instances task submitted",
            shipment_id=str(shipment.id),
            task_id=result.task_id,
        )
        return EditTaskSubmittedResult(
            shipment_id=shipment.id,
            task_id=result.task_id,
            initial_status=result.initial_status,
        )
