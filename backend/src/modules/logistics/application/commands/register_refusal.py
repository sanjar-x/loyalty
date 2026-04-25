"""
Command handler: register a doorstep refusal with the provider.

A refusal is the recipient declining to accept the parcel at the
doorstep. The provider returns the parcel to the sender without
creating a separate return order.
"""

import uuid
from dataclasses import dataclass

from src.modules.logistics.application.dto import RegisterReturnResult
from src.modules.logistics.domain.exceptions import ShipmentNotFoundError
from src.modules.logistics.domain.interfaces import (
    IShipmentRepository,
    IShippingProviderRegistry,
)
from src.modules.logistics.domain.value_objects import RefusalRequest
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class RegisterRefusalCommand:
    """Input for registering a doorstep refusal.

    Attributes:
        shipment_id: UUID of the shipment being refused.
        reason: Optional free-form reason (passed to the provider).
    """

    shipment_id: uuid.UUID
    reason: str | None = None


class RegisterRefusalHandler:
    """Register a doorstep refusal with the shipment's provider."""

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
        self._logger = logger.bind(handler="RegisterRefusalHandler")

    async def handle(self, command: RegisterRefusalCommand) -> RegisterReturnResult:
        shipment = await self._shipment_repo.get_by_id(command.shipment_id)
        if shipment is None:
            raise ShipmentNotFoundError(
                details={"shipment_id": str(command.shipment_id)}
            )

        provider = self._registry.get_return_provider(shipment.provider_code)
        request = RefusalRequest(
            order_provider_id=shipment.provider_shipment_id or "",
            reason=command.reason,
        )
        result = await provider.register_refusal(request)

        if result.success:
            async with self._uow:
                shipment = await self._shipment_repo.get_by_id(command.shipment_id)
                if shipment is None:
                    self._logger.error(
                        "Shipment vanished between refusal submit and persist",
                        shipment_id=str(command.shipment_id),
                    )
                    raise ShipmentNotFoundError(
                        details={"shipment_id": str(command.shipment_id)}
                    )
                shipment.record_refusal(reason=command.reason)
                await self._shipment_repo.update(shipment)
                self._uow.register_aggregate(shipment)
                await self._uow.commit()
            self._logger.info(
                "Refusal registered", shipment_id=str(command.shipment_id)
            )
        else:
            self._logger.warning(
                "Refusal rejected by provider",
                shipment_id=str(command.shipment_id),
                reason=result.reason,
            )
        return RegisterReturnResult(
            shipment_id=command.shipment_id,
            success=result.success,
            provider_return_id=result.provider_return_id,
            reason=result.reason,
        )
