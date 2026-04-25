"""
Command handler: book a shipment with the logistics provider.

Two-phase pattern:
1. Persist intent (DRAFT → BOOKING_PENDING) in a DB transaction
2. Call provider API (outside transaction)
3. Persist result (BOOKING_PENDING → BOOKED or FAILED) in a second transaction
"""

import uuid
from dataclasses import dataclass

from src.modules.logistics.application.dto import BookShipmentResult
from src.modules.logistics.domain.exceptions import (
    BookingError,
    BookingPendingError,
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


__all__ = ["BookShipmentCommand", "BookShipmentHandler", "BookShipmentResult"]


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
            sender=shipment.sender,
            recipient=shipment.recipient,
            parcels=shipment.parcels,
            service_code=shipment.service_code,
            delivery_type=shipment.delivery_type,
            provider_payload=shipment.provider_payload or "",
            cod=shipment.cod,
        )

        try:
            result = await booking_provider.book_shipment(booking_request)
        except BookingPendingError:
            # Transient: leave shipment in BOOKING_PENDING for the next retry.
            # The provider has accepted the request but hasn't yet produced
            # a final state (e.g. CDEK polling window expired).
            self._logger.warning(
                "Booking still pending — shipment kept in BOOKING_PENDING",
                shipment_id=str(shipment.id),
            )
            raise
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

            # Detect price drift between the quote shown to the customer
            # and the cost the provider actually committed to.
            self._verify_actual_cost(shipment, result)

            shipment.mark_booked(
                provider_shipment_id=result.provider_shipment_id,
                tracking_number=result.tracking_number,
                estimated_delivery=result.estimated_delivery,
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

    # Tolerance for cost drift between the quoted price (shown to the
    # customer) and the price the provider committed to during booking.
    # Anything larger than 1 % is logged as a price-mismatch warning so
    # that operators can investigate without rejecting valid bookings.
    _PRICE_DRIFT_TOLERANCE = 0.01

    def _verify_actual_cost(self, shipment, result) -> None:
        """Log a warning when the provider-confirmed cost diverges from the quote."""
        actual = result.actual_cost
        if actual is None:
            return
        quoted = shipment.quoted_cost
        if actual.currency_code != quoted.currency_code:
            self._logger.warning(
                "Booking currency mismatch",
                shipment_id=str(shipment.id),
                quoted_currency=quoted.currency_code,
                actual_currency=actual.currency_code,
            )
            return
        if quoted.amount == 0:
            return
        drift = abs(actual.amount - quoted.amount) / quoted.amount
        if drift > self._PRICE_DRIFT_TOLERANCE:
            self._logger.warning(
                "Booking price drift detected",
                shipment_id=str(shipment.id),
                quoted_amount=quoted.amount,
                actual_amount=actual.amount,
                drift_pct=round(drift * 100, 2),
            )
