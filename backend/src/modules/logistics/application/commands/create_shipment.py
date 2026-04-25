"""
Command handler: create a new Shipment in DRAFT status.

Takes a quote_id, looks up the server-side DeliveryQuote for price
integrity, and persists the shipment aggregate.
Part of the application layer (CQRS write side).
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from src.modules.logistics.application.dto import CreateShipmentResult
from src.modules.logistics.domain.entities import Shipment
from src.modules.logistics.domain.exceptions import (
    QuoteExpiredError,
    QuoteNotFoundError,
)
from src.modules.logistics.domain.interfaces import (
    IDeliveryQuoteRepository,
    IShipmentRepository,
)
from src.modules.logistics.domain.value_objects import (
    Address,
    CashOnDelivery,
    ContactInfo,
    Parcel,
)
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class CreateShipmentCommand:
    """Input for creating a new shipment from a selected quote.

    Attributes:
        quote_id: Server-side quote identifier (from calculate_rates).
        origin: Sender address.
        destination: Recipient address.
        sender: Sender contact details.
        recipient: Recipient contact details.
        parcels: Packages to ship.
        order_id: Optional link to the order/checkout.
        cod: Cash-on-delivery configuration, if applicable.
    """

    quote_id: uuid.UUID
    origin: Address
    destination: Address
    sender: ContactInfo
    recipient: ContactInfo
    parcels: list[Parcel]
    order_id: uuid.UUID | None = None
    cod: CashOnDelivery | None = None


__all__ = ["CreateShipmentCommand", "CreateShipmentHandler", "CreateShipmentResult"]


class CreateShipmentHandler:
    """Create a new Shipment in DRAFT status from a server-side quote."""

    def __init__(
        self,
        shipment_repo: IShipmentRepository,
        quote_repo: IDeliveryQuoteRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._shipment_repo = shipment_repo
        self._quote_repo = quote_repo
        self._uow = uow
        self._logger = logger.bind(handler="CreateShipmentHandler")

    async def handle(self, command: CreateShipmentCommand) -> CreateShipmentResult:
        """Execute the create-shipment command.

        Looks up a trusted server-side quote, validates expiry,
        creates a Shipment aggregate in DRAFT status. The actual
        provider booking happens in a separate BookShipment command
        to keep external API calls outside the DB transaction.
        """
        quote = await self._quote_repo.get_by_id(command.quote_id)
        if quote is None:
            raise QuoteNotFoundError(quote_id=command.quote_id)

        if quote.expires_at is not None and quote.expires_at < datetime.now(UTC):
            raise QuoteExpiredError(
                quote_id=command.quote_id,
                expires_at=quote.expires_at,
            )

        async with self._uow:
            shipment = Shipment.create(
                quote=quote,
                origin=command.origin,
                destination=command.destination,
                sender=command.sender,
                recipient=command.recipient,
                parcels=command.parcels,
                order_id=command.order_id,
                cod=command.cod,
            )
            shipment = await self._shipment_repo.add(shipment)
            self._uow.register_aggregate(shipment)
            await self._uow.commit()

        self._logger.info(
            "Shipment created",
            shipment_id=str(shipment.id),
            provider=quote.rate.provider_code,
        )
        return CreateShipmentResult(shipment_id=shipment.id)
