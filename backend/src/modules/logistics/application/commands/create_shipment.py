"""
Command handler: create a new Shipment in DRAFT status.

Takes a selected DeliveryQuote and persists the shipment aggregate.
Part of the application layer (CQRS write side).
"""

import uuid
from dataclasses import dataclass

from src.modules.logistics.domain.entities import Shipment
from src.modules.logistics.domain.interfaces import IShipmentRepository
from src.modules.logistics.domain.value_objects import (
    Address,
    ContactInfo,
    DeliveryQuote,
    Parcel,
)
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class CreateShipmentCommand:
    """Input for creating a new shipment from a selected quote.

    Attributes:
        quote: The selected DeliveryQuote (rate + provider payload).
        origin: Sender address.
        destination: Recipient address.
        recipient: Recipient contact details.
        parcels: Packages to ship.
        order_id: Optional link to the order/checkout.
    """

    quote: DeliveryQuote
    origin: Address
    destination: Address
    recipient: ContactInfo
    parcels: list[Parcel]
    order_id: uuid.UUID | None = None


@dataclass(frozen=True)
class CreateShipmentResult:
    """Output of shipment creation.

    Attributes:
        shipment_id: UUID of the newly created shipment.
    """

    shipment_id: uuid.UUID


class CreateShipmentHandler:
    """Create a new Shipment in DRAFT status."""

    def __init__(
        self,
        shipment_repo: IShipmentRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._shipment_repo = shipment_repo
        self._uow = uow
        self._logger = logger.bind(handler="CreateShipmentHandler")

    async def handle(self, command: CreateShipmentCommand) -> CreateShipmentResult:
        """Execute the create-shipment command.

        Creates a Shipment aggregate in DRAFT status. The actual provider
        booking happens in a separate BookShipment command to keep
        external API calls outside the DB transaction.
        """
        async with self._uow:
            shipment = Shipment.create(
                quote=command.quote,
                origin=command.origin,
                destination=command.destination,
                recipient=command.recipient,
                parcels=command.parcels,
                order_id=command.order_id,
            )
            shipment = await self._shipment_repo.add(shipment)
            self._uow.register_aggregate(shipment)
            await self._uow.commit()

        self._logger.info(
            "Shipment created",
            shipment_id=str(shipment.id),
            provider=command.quote.rate.provider_code.value,
        )
        return CreateShipmentResult(shipment_id=shipment.id)
