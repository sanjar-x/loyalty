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
from src.modules.logistics.domain.value_objects import EditPackage, EditTaskKind
from src.shared.exceptions import ConflictError, ValidationError
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


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
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._shipment_repo = shipment_repo
        self._registry = registry
        self._uow = uow
        self._logger = logger.bind(handler="EditOrderPackagesHandler")

    async def handle(
        self, command: EditOrderPackagesCommand
    ) -> EditTaskSubmittedResult:
        if not command.packages:
            raise ValidationError(
                message="EditOrderPackagesCommand requires at least one package.",
                details={"shipment_id": str(command.shipment_id)},
            )

        # Phase 1: validate against persisted state.
        shipment = await self._shipment_repo.get_by_id(command.shipment_id)
        if shipment is None:
            raise ShipmentNotFoundError(
                details={"shipment_id": str(command.shipment_id)}
            )
        existing = next(
            (
                t
                for t in shipment.pending_edit_tasks
                if t.kind == EditTaskKind.EDIT_PACKAGES
            ),
            None,
        )
        if existing is not None:
            raise ConflictError(
                message=(
                    "An EDIT_PACKAGES task is already in flight for this shipment."
                ),
                error_code="EDIT_TASK_ALREADY_PENDING",
                details={
                    "shipment_id": str(command.shipment_id),
                    "task_id": existing.task_id,
                    "kind": existing.kind.value,
                },
            )

        # Phase 2: provider call (async — returns editing_task_id).
        provider = self._registry.get_edit_provider(shipment.provider_code)
        result = await provider.edit_packages(
            order_provider_id=shipment.provider_shipment_id or "",
            packages=list(command.packages),
        )

        # Phase 3: record the pending edit task. Local Shipment.parcels
        # is not mutated yet — the change only becomes canonical when
        # the status-poller observes the task transitioning to SUCCESS.
        async with self._uow:
            shipment = await self._shipment_repo.get_by_id(command.shipment_id)
            if shipment is None:
                self._logger.error(
                    "Shipment vanished between edit_packages submit and persist",
                    shipment_id=str(command.shipment_id),
                    task_id=result.task_id,
                )
                raise ShipmentNotFoundError(
                    details={"shipment_id": str(command.shipment_id)}
                )
            shipment.record_edit_task(
                task_id=result.task_id,
                kind=EditTaskKind.EDIT_PACKAGES,
                initial_status=result.initial_status,
            )
            await self._shipment_repo.update(shipment)
            self._uow.register_aggregate(shipment)
            await self._uow.commit()

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
