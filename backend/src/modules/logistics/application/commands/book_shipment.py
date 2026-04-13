"""
Command handler: book a shipment with the logistics provider.

Two-phase pattern:
1. Persist intent (DRAFT → BOOKING_PENDING) in a DB transaction
2. Call provider API (outside transaction)
3. Persist result (BOOKING_PENDING → BOOKED or FAILED) in a second transaction
"""

import uuid
from dataclasses import dataclass

from src.modules.logistics.domain.exceptions import (
    BookingError,
    ShipmentNotFoundError,
)
from src.modules.logistics.domain.interfaces import (
    IShipmentRepository,
    IShippingProviderRegistry,
)
from src.modules.logistics.domain.value_objects import BookingRequest
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class BookShipmentCommand:
    """Input for booking a shipment with the provider.

    Attributes:
        shipment_id: UUID of the DRAFT shipment to book.
    """

    shipment_id: uuid.UUID


@dataclass(frozen=True)
class BookShipmentResult:
    """Output of a successful booking.

    Attributes:
        shipment_id: UUID of the booked shipment.
        provider_shipment_id: Provider's shipment identifier.
        tracking_number: Provider's tracking number (may be None).
    """

    shipment_id: uuid.UUID
    provider_shipment_id: str
    tracking_number: str | None


class BookShipmentHandler:
    """Book a DRAFT shipment with its logistics provider.

    Uses the two-phase pattern to keep external API calls outside
    the database transaction boundary.
    """

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
        self._logger = logger.bind(handler="BookShipmentHandler")

    async def handle(self, command: BookShipmentCommand) -> BookShipmentResult:
        # Phase 1: Mark as BOOKING_PENDING (DB transaction)
        async with self._uow:
            shipment = await self._shipment_repo.get_by_id(command.shipment_id)
            if shipment is None:
                raise ShipmentNotFoundError(
                    details={"shipment_id": str(command.shipment_id)}
                )

            shipment.mark_booking_pending()
            shipment = await self._shipment_repo.update(shipment)
            self._uow.register_aggregate(shipment)
            await self._uow.commit()

        # Phase 2: Call provider API (outside DB transaction)
        booking_provider = self._registry.get_booking_provider(shipment.provider_code)
        booking_request = BookingRequest(
            shipment_id=shipment.id,
            origin=shipment.origin,
            destination=shipment.destination,
            recipient=shipment.recipient,
            parcels=shipment.parcels,
            service_code=shipment.service_code,
            delivery_type=shipment.delivery_type,
            provider_payload=shipment.provider_payload or "",
        )

        try:
            result = await booking_provider.book_shipment(booking_request)
        except Exception as exc:
            # Phase 3a: Mark as FAILED
            self._logger.error(
                "Booking failed",
                shipment_id=str(shipment.id),
                error=str(exc),
            )
            async with self._uow:
                shipment = await self._shipment_repo.get_by_id(command.shipment_id)
                if shipment:
                    shipment.mark_booking_failed(reason=str(exc))
                    await self._shipment_repo.update(shipment)
                    self._uow.register_aggregate(shipment)
                    await self._uow.commit()
            raise BookingError(
                message=f"Provider booking failed: {exc}",
                details={"shipment_id": str(command.shipment_id)},
            ) from exc

        # Phase 3b: Mark as BOOKED
        async with self._uow:
            shipment = await self._shipment_repo.get_by_id(command.shipment_id)
            if shipment is None:
                raise ShipmentNotFoundError(
                    details={"shipment_id": str(command.shipment_id)}
                )

            shipment.mark_booked(
                provider_shipment_id=result.provider_shipment_id,
                tracking_number=result.tracking_number,
            )
            shipment = await self._shipment_repo.update(shipment)
            self._uow.register_aggregate(shipment)
            await self._uow.commit()

        self._logger.info(
            "Shipment booked",
            shipment_id=str(shipment.id),
            provider_shipment_id=result.provider_shipment_id,
        )
        return BookShipmentResult(
            shipment_id=shipment.id,
            provider_shipment_id=result.provider_shipment_id,
            tracking_number=result.tracking_number,
        )
