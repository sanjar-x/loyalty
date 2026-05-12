"""
Command handler: cancel a previously scheduled courier intake.
"""

import uuid
from dataclasses import dataclass

from src.modules.logistics.application.dto import CancelIntakeResult
from src.modules.logistics.domain.interfaces import (
    IShipmentRepository,
    IShippingProviderRegistry,
)
from src.modules.logistics.domain.value_objects import ProviderCode
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class CancelIntakeCommand:
    """Input for intake cancellation.

    Attributes:
        provider_code: Logistics provider that owns the intake.
        provider_intake_id: Provider's UUID of the intake to cancel.
        shipment_id: Optional Shipment aggregate the intake belongs to.
            When supplied, a successful cancellation also clears the
            ``scheduled_intake`` slot on the shipment and emits
            :class:`ShipmentIntakeScheduledEvent`'s counterpart through
            the aggregate's event stream. When ``None``, the
            cancellation runs as a pure provider-side call (no DB write).
    """

    provider_code: ProviderCode
    provider_intake_id: str
    shipment_id: uuid.UUID | None = None


class CancelIntakeHandler:
    """Cancel a courier intake with the provider."""

    def __init__(
        self,
        registry: IShippingProviderRegistry,
        shipment_repo: IShipmentRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._registry = registry
        self._shipment_repo = shipment_repo
        self._uow = uow
        self._logger = logger.bind(handler="CancelIntakeHandler")

    async def handle(self, command: CancelIntakeCommand) -> CancelIntakeResult:
        provider = self._registry.get_intake_provider(command.provider_code)
        success = await provider.cancel_intake(command.provider_intake_id)
        self._logger.info(
            "Intake cancellation",
            provider_code=command.provider_code,
            provider_intake_id=command.provider_intake_id,
            success=success,
        )

        if success and command.shipment_id is not None:
            async with self._uow:
                shipment = await self._shipment_repo.get_by_id(command.shipment_id)
                if shipment is not None and (
                    shipment.scheduled_intake is not None
                    and shipment.scheduled_intake.provider_intake_id
                    == command.provider_intake_id
                ):
                    shipment.clear_intake()
                    await self._shipment_repo.update(shipment)
                    self._uow.register_aggregate(shipment)
                    await self._uow.commit()

        return CancelIntakeResult(success=success)
