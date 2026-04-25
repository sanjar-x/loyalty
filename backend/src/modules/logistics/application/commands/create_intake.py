"""
Command handler: schedule a courier intake (pickup) with the provider.

The intake is scheduled for an already-booked shipment. The shipment
provides the provider code and pickup address; the caller picks the
date / time window after consulting ``GetAvailableIntakeDaysQuery``.
"""

import uuid
from dataclasses import dataclass

from src.modules.logistics.application.dto import CreateIntakeResult
from src.modules.logistics.domain.exceptions import ShipmentNotFoundError
from src.modules.logistics.domain.interfaces import (
    IShipmentRepository,
    IShippingProviderRegistry,
)
from src.modules.logistics.domain.value_objects import IntakeRequest
from src.shared.exceptions import ValidationError
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class CreateIntakeCommand:
    """Input for scheduling a courier intake.

    Attributes:
        shipment_id: UUID of the BOOKED shipment that should be picked up.
        intake_date: Target date for pickup (YYYY-MM-DD).
        intake_time_from: Earliest pickup time (HH:MM).
        intake_time_to: Latest pickup time (HH:MM).
        comment: Free-form note for the courier.
        lunch_time_from: Optional lunch break start (HH:MM).
        lunch_time_to: Optional lunch break end (HH:MM).
        need_call: Whether the courier should call before arrival.
    """

    shipment_id: uuid.UUID
    intake_date: str
    intake_time_from: str
    intake_time_to: str
    comment: str | None = None
    lunch_time_from: str | None = None
    lunch_time_to: str | None = None
    need_call: bool = False


class CreateIntakeHandler:
    """Schedule a courier intake with the shipment's provider."""

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
        self._logger = logger.bind(handler="CreateIntakeHandler")

    async def handle(self, command: CreateIntakeCommand) -> CreateIntakeResult:
        # Phase 1: validate inputs against the persisted shipment.
        shipment = await self._shipment_repo.get_by_id(command.shipment_id)
        if shipment is None:
            raise ShipmentNotFoundError(
                details={"shipment_id": str(command.shipment_id)}
            )
        if not shipment.parcels:
            raise ValidationError(
                message="Shipment has no parcels — cannot schedule intake.",
                details={"shipment_id": str(command.shipment_id)},
            )

        # Phase 2: external provider call — runs outside any DB tx.
        provider = self._registry.get_intake_provider(shipment.provider_code)
        request = IntakeRequest(
            order_provider_id=shipment.provider_shipment_id or "",
            intake_date=command.intake_date,
            intake_time_from=command.intake_time_from,
            intake_time_to=command.intake_time_to,
            from_address=shipment.origin,
            sender=shipment.sender,
            package=shipment.parcels[0],
            comment=command.comment,
            lunch_time_from=command.lunch_time_from,
            lunch_time_to=command.lunch_time_to,
            need_call=command.need_call,
        )
        result = await provider.create_intake(request)

        # Phase 3: persist the scheduled intake on the aggregate so the
        # audit trail and outbox event-stream stay consistent with what
        # the carrier acknowledged.
        async with self._uow:
            shipment = await self._shipment_repo.get_by_id(command.shipment_id)
            if shipment is None:
                # Window between Phase 1 and Phase 3 — unlikely but the
                # carrier already accepted the intake. Log loud so an
                # operator can reconcile manually.
                self._logger.error(
                    "Shipment vanished between intake creation and persist",
                    shipment_id=str(command.shipment_id),
                    provider_intake_id=result.provider_intake_id,
                )
                raise ShipmentNotFoundError(
                    details={"shipment_id": str(command.shipment_id)}
                )
            shipment.record_intake(
                provider_intake_id=result.provider_intake_id,
                status=result.status,
            )
            await self._shipment_repo.update(shipment)
            self._uow.register_aggregate(shipment)
            await self._uow.commit()

        self._logger.info(
            "Intake scheduled",
            shipment_id=str(shipment.id),
            provider_intake_id=result.provider_intake_id,
            status=result.status.value,
        )
        return CreateIntakeResult(
            shipment_id=shipment.id,
            provider_intake_id=result.provider_intake_id,
            status=result.status,
        )
