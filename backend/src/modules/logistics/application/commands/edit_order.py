"""
Command handler: edit recipient / destination / packages of a booked shipment.

Wraps Yandex's ``POST /request/edit`` (3.06). The provider returns a
synchronous edit ticket; callers may poll ``GetEditTaskStatusQuery``
for additional confirmation, but ``initial_status`` is already
``SUCCESS`` for this endpoint.
"""

import uuid
from dataclasses import dataclass, field

from src.modules.logistics.application.dto import EditTaskSubmittedResult
from src.modules.logistics.domain.exceptions import ShipmentNotFoundError
from src.modules.logistics.domain.interfaces import (
    IShipmentRepository,
    IShippingProviderRegistry,
)
from src.modules.logistics.domain.value_objects import (
    Address,
    ContactInfo,
    DeliveryType,
    EditOrderRequest,
    EditPlaceSwap,
)
from src.shared.interfaces.logger import ILogger


@dataclass(frozen=True)
class EditOrderCommand:
    """Input for editing a booked shipment.

    At least one of ``recipient`` / ``destination`` / ``places`` must
    be supplied — the provider rejects empty patches.
    """

    shipment_id: uuid.UUID
    recipient: ContactInfo | None = None
    destination: Address | None = None
    delivery_type: DeliveryType | None = None
    places: tuple[EditPlaceSwap, ...] = field(default_factory=tuple)


class EditOrderHandler:
    """Mutate recipient / destination / packages on a booked shipment."""

    def __init__(
        self,
        shipment_repo: IShipmentRepository,
        registry: IShippingProviderRegistry,
        logger: ILogger,
    ) -> None:
        self._shipment_repo = shipment_repo
        self._registry = registry
        self._logger = logger.bind(handler="EditOrderHandler")

    async def handle(self, command: EditOrderCommand) -> EditTaskSubmittedResult:
        if (
            command.recipient is None
            and command.destination is None
            and not command.places
        ):
            raise ValueError(
                "EditOrderCommand requires at least one of recipient, "
                "destination or places."
            )

        shipment = await self._shipment_repo.get_by_id(command.shipment_id)
        if shipment is None:
            raise ShipmentNotFoundError(
                details={"shipment_id": str(command.shipment_id)}
            )

        provider = self._registry.get_edit_provider(shipment.provider_code)
        request = EditOrderRequest(
            order_provider_id=shipment.provider_shipment_id or "",
            recipient=command.recipient,
            destination=command.destination,
            delivery_type=command.delivery_type,
            places=command.places,
        )
        result = await provider.edit_order(request)
        self._logger.info(
            "Edit order ticket submitted",
            shipment_id=str(shipment.id),
            task_id=result.task_id,
            status=result.initial_status.value,
        )
        return EditTaskSubmittedResult(
            shipment_id=shipment.id,
            task_id=result.task_id,
            initial_status=result.initial_status,
        )
