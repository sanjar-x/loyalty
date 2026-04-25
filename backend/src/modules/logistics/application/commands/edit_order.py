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
    EditTaskKind,
)
from src.shared.exceptions import ConflictError, ValidationError
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


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
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._shipment_repo = shipment_repo
        self._registry = registry
        self._uow = uow
        self._logger = logger.bind(handler="EditOrderHandler")

    async def handle(self, command: EditOrderCommand) -> EditTaskSubmittedResult:
        if (
            command.recipient is None
            and command.destination is None
            and not command.places
        ):
            raise ValidationError(
                message=(
                    "EditOrderCommand requires at least one of recipient, "
                    "destination or places."
                ),
                details={"shipment_id": str(command.shipment_id)},
            )

        # Phase 1: read-only validation against the persisted shipment.
        shipment = await self._shipment_repo.get_by_id(command.shipment_id)
        if shipment is None:
            raise ShipmentNotFoundError(
                details={"shipment_id": str(command.shipment_id)}
            )
        # Idempotency guard. ``record_edit_task`` "replaces any previous
        # task of the same kind" — without the guard a double-click
        # submits two tickets to Yandex; the first task_id is orphaned
        # locally and the carrier silently last-write-wins.
        existing = next(
            (
                t
                for t in shipment.pending_edit_tasks
                if t.kind == EditTaskKind.EDIT_ORDER
            ),
            None,
        )
        if existing is not None:
            raise ConflictError(
                message=(
                    "An EDIT_ORDER task is already in flight for this shipment; "
                    "wait for it to settle before submitting another."
                ),
                error_code="EDIT_TASK_ALREADY_PENDING",
                details={
                    "shipment_id": str(command.shipment_id),
                    "task_id": existing.task_id,
                    "kind": existing.kind.value,
                },
            )

        # Phase 2: provider call.
        provider = self._registry.get_edit_provider(shipment.provider_code)
        request = EditOrderRequest(
            order_provider_id=shipment.provider_shipment_id or "",
            recipient=command.recipient,
            destination=command.destination,
            delivery_type=command.delivery_type,
            places=command.places,
        )
        result = await provider.edit_order(request)

        # Phase 3: persist mutations + record edit task. Yandex /request/edit
        # is synchronous (initial_status=SUCCESS); apply the recipient /
        # destination patches locally so the next read does not drift
        # from the carrier-side state. Package swaps remain attached to
        # the task ticket — the local Shipment.parcels list does not track
        # individual barcodes, so the canonical state stays on the
        # provider until a future sync.
        async with self._uow:
            shipment = await self._shipment_repo.get_by_id(command.shipment_id)
            if shipment is None:
                self._logger.error(
                    "Shipment vanished between edit submission and persist",
                    shipment_id=str(command.shipment_id),
                    task_id=result.task_id,
                )
                raise ShipmentNotFoundError(
                    details={"shipment_id": str(command.shipment_id)}
                )
            if command.recipient is not None:
                shipment.apply_recipient_change(command.recipient)
            if command.destination is not None:
                shipment.apply_destination_change(
                    command.destination,
                    delivery_type=command.delivery_type,
                )
            shipment.record_edit_task(
                task_id=result.task_id,
                kind=EditTaskKind.EDIT_ORDER,
                initial_status=result.initial_status,
            )
            await self._shipment_repo.update(shipment)
            self._uow.register_aggregate(shipment)
            await self._uow.commit()

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
