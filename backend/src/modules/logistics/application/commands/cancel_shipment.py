"""
Command handler: cancel a booked shipment.

Two-phase pattern analogous to BookShipmentHandler:
1. Persist intent (BOOKED → CANCEL_PENDING)
2. Call provider API
3. Persist result (CANCEL_PENDING → CANCELLED or reverts to BOOKED)
"""

import uuid
from dataclasses import dataclass

from src.modules.logistics.domain.exceptions import (
    CancellationError,
    ShipmentNotFoundError,
)
from src.modules.logistics.domain.interfaces import (
    IShipmentRepository,
    IShippingProviderRegistry,
)
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class CancelShipmentCommand:
    """Input for cancelling a booked shipment.

    Attributes:
        shipment_id: UUID of the shipment to cancel.
    """

    shipment_id: uuid.UUID


@dataclass(frozen=True)
class CancelShipmentResult:
    """Output of a successful cancellation.

    Attributes:
        shipment_id: UUID of the cancelled shipment.
    """

    shipment_id: uuid.UUID


class CancelShipmentHandler:
    """Cancel a BOOKED shipment via the logistics provider."""

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
        self._logger = logger.bind(handler="CancelShipmentHandler")

    async def handle(self, command: CancelShipmentCommand) -> CancelShipmentResult:
        # Phase 1: Mark as CANCEL_PENDING
        async with self._uow:
            shipment = await self._shipment_repo.get_by_id(command.shipment_id)
            if shipment is None:
                raise ShipmentNotFoundError(
                    details={"shipment_id": str(command.shipment_id)}
                )

            shipment.mark_cancel_pending()
            shipment = await self._shipment_repo.update(shipment)
            self._uow.register_aggregate(shipment)
            await self._uow.commit()

        # Phase 2: Call provider (skip if never booked)
        if not shipment.provider_shipment_id:
            self._logger.warning(
                "Shipment has no provider_shipment_id, skipping provider cancel",
                shipment_id=str(shipment.id),
            )
        else:
            booking_provider = self._registry.get_booking_provider(
                shipment.provider_code
            )

            try:
                result = await booking_provider.cancel_shipment(
                    shipment.provider_shipment_id
                )
            except Exception as exc:
                self._logger.error(
                    "Cancellation failed",
                    shipment_id=str(shipment.id),
                    error=str(exc),
                )
                async with self._uow:
                    shipment = await self._shipment_repo.get_by_id(command.shipment_id)
                    if shipment:
                        shipment.mark_cancellation_failed(reason=str(exc))
                        await self._shipment_repo.update(shipment)
                        self._uow.register_aggregate(shipment)
                        await self._uow.commit()
                raise CancellationError(
                    message=f"Provider cancellation failed: {exc}",
                    details={"shipment_id": str(command.shipment_id)},
                ) from exc

            if not result.success:
                async with self._uow:
                    shipment = await self._shipment_repo.get_by_id(command.shipment_id)
                    if shipment:
                        shipment.mark_cancellation_failed(
                            reason=result.reason or "Provider rejected cancellation"
                        )
                        await self._shipment_repo.update(shipment)
                        self._uow.register_aggregate(shipment)
                        await self._uow.commit()
                raise CancellationError(
                    message=result.reason or "Provider rejected cancellation",
                    details={"shipment_id": str(command.shipment_id)},
                )

        # Phase 3: Mark as CANCELLED
        async with self._uow:
            shipment = await self._shipment_repo.get_by_id(command.shipment_id)
            if shipment is None:
                raise ShipmentNotFoundError(
                    details={"shipment_id": str(command.shipment_id)}
                )
            shipment.mark_cancelled()
            shipment = await self._shipment_repo.update(shipment)
            self._uow.register_aggregate(shipment)
            await self._uow.commit()

        self._logger.info("Shipment cancelled", shipment_id=str(shipment.id))
        return CancelShipmentResult(shipment_id=shipment.id)
