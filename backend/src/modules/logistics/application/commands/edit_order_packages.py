"""
Command handler: replace package layout of a booked shipment.

Wraps Yandex's ``POST /request/places/edit`` (3.12) — async; returns
``editing_task_id`` to poll via ``GetEditTaskStatusQuery``.
"""

import uuid
from dataclasses import dataclass

from src.modules.logistics.application.dto import EditTaskSubmittedResult
from src.modules.logistics.domain.exceptions import ShipmentNotFoundError
from src.modules.logistics.domain.interfaces import (
    IShipmentRepository,
    IShippingProviderRegistry,
)
from src.modules.logistics.domain.value_objects import EditPackage
from src.shared.interfaces.logger import ILogger


@dataclass(frozen=True)
class EditOrderPackagesCommand:
    """Input for replacing the package layout of a shipment."""

    shipment_id: uuid.UUID
    packages: tuple[EditPackage, ...]


class EditOrderPackagesHandler:
    """Replace the box layout of a booked shipment."""

    def __init__(
        self,
        shipment_repo: IShipmentRepository,
        registry: IShippingProviderRegistry,
        logger: ILogger,
    ) -> None:
        self._shipment_repo = shipment_repo
        self._registry = registry
        self._logger = logger.bind(handler="EditOrderPackagesHandler")

    async def handle(
        self, command: EditOrderPackagesCommand
    ) -> EditTaskSubmittedResult:
        if not command.packages:
            raise ValueError("EditOrderPackagesCommand requires at least one package.")

        shipment = await self._shipment_repo.get_by_id(command.shipment_id)
        if shipment is None:
            raise ShipmentNotFoundError(
                details={"shipment_id": str(command.shipment_id)}
            )

        provider = self._registry.get_edit_provider(shipment.provider_code)
        result = await provider.edit_packages(
            order_provider_id=shipment.provider_shipment_id or "",
            packages=list(command.packages),
        )
        self._logger.info(
            "Edit packages task submitted",
            shipment_id=str(shipment.id),
            task_id=result.task_id,
        )
        return EditTaskSubmittedResult(
            shipment_id=shipment.id,
            task_id=result.task_id,
            initial_status=result.initial_status,
        )
