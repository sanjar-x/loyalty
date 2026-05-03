"""Order consumers — DobroPost + Russian carrier event bridges.

The webhook receiver normalises every DobroPost payload into a single
canonical event shape:

    {
        "dp_shipment_id": <int>,            # required (unless passport)
        "status_id": <int>,                 # numeric status code
        "status_label": <str>,              # optional human-readable
        "dp_track_number": <str|null>,      # may arrive via dpTrackNumber
        "passport_validation_status": bool, # for passport-payload variant
    }

The consumers below dispatch on these fields. The full DobroPost
status_id taxonomy lives in
``src.modules.order.infrastructure.dobropost_status_map`` —
``map_status_id_to_action`` projects the 40 codes onto a 5-action enum
for the FSM.

Russian carrier canonical statuses (research (6) §4.3):

* ``AT_PICKUP_POINT`` → mark_awaiting_pickup.
* ``DELIVERED`` → mark_delivered.
* ``RETURN_TO_SENDER`` / ``REFUSED`` → mark_returning_to_warehouse.
* ``IN_TRANSIT`` / ``OUT_FOR_DELIVERY`` (first occurrence) → mark_in_last_mile.
"""

import uuid

from src.modules.order.application.commands.cancel_order import (
    CancelOrderCommand,
    CancelOrderHandler,
)
from src.modules.order.application.commands.hold_order import (
    HoldOrderCommand,
    HoldOrderHandler,
)
from src.modules.order.application.commands.mark_order_arrived_in_ru import (
    MarkOrderArrivedInRuCommand,
    MarkOrderArrivedInRuHandler,
)
from src.modules.order.application.commands.mark_order_awaiting_pickup import (
    MarkOrderAwaitingPickupCommand,
    MarkOrderAwaitingPickupHandler,
)
from src.modules.order.application.commands.mark_order_delivered import (
    MarkOrderDeliveredCommand,
    MarkOrderDeliveredHandler,
)
from src.modules.order.application.commands.mark_order_in_last_mile import (
    MarkOrderInLastMileCommand,
    MarkOrderInLastMileHandler,
)
from src.modules.order.application.commands.return_flow import (
    MarkOrderReturningToWarehouseCommand,
    MarkOrderReturningToWarehouseHandler,
)
from src.modules.order.application.ports import (
    IDobroPostShipmentMappingRepository,
)
from src.modules.order.domain.exceptions import OrderNotFoundError
from src.modules.order.domain.interfaces import IOrderRepository
from src.modules.order.domain.value_objects import (
    CancellationReason,
    HoldReason,
)
from src.modules.order.infrastructure.dobropost_status_map import (
    DobroPostFsmAction,
    map_status_id_to_action,
    status_label,
)
from src.shared.interfaces.logger import ILogger


def _coerce_int(value: object) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


class DobroPostStatusUpdatedConsumer:
    """Maps DobroPost ``status_id`` events to Order FSM commands.

    Pre-condition (enforced by webhook receiver): payload contains
    ``dp_shipment_id`` (int). Resolution to ``order_id`` goes via the
    side-mapping table; fallback ``shipment_id`` (UUID) is supported
    for compatibility with handlers that publish UUIDs directly.
    """

    def __init__(
        self,
        order_repo: IOrderRepository,
        mapping_repo: IDobroPostShipmentMappingRepository,
        arrived_handler: MarkOrderArrivedInRuHandler,
        hold_handler: HoldOrderHandler,
        cancel_handler: CancelOrderHandler,
        logger: ILogger,
    ) -> None:
        self._order_repo = order_repo
        self._mapping_repo = mapping_repo
        self._arrived = arrived_handler
        self._hold = hold_handler
        self._cancel = cancel_handler
        self._logger = logger.bind(consumer="DobroPostStatusUpdatedConsumer")

    async def handle(self, payload: dict) -> None:
        dp_id_raw = (
            payload.get("dp_shipment_id")
            or payload.get("dpShipmentId")
            or payload.get("shipmentId")
        )
        status_id = _coerce_int(payload.get("status_id"))
        if status_id is None:
            self._logger.warning("dobropost.status.skip", reason="bad_status_id")
            return

        order_id: uuid.UUID | None = None
        dp_shipment_id = _coerce_int(dp_id_raw)
        if dp_shipment_id is not None:
            mapping = await self._mapping_repo.get_by_dp_shipment_id(dp_shipment_id)
            if mapping is not None:
                order_id = mapping.order_id
                track = payload.get("dp_track_number") or payload.get("dpTrackNumber")
                await self._mapping_repo.update_status(
                    dp_shipment_id=dp_shipment_id,
                    last_status_id=status_id,
                    dp_track_number=str(track) if track else None,
                )

        if order_id is None:
            shipment_id_raw = payload.get("shipment_id") or payload.get("shipmentUuid")
            if shipment_id_raw is not None:
                try:
                    shipment_uuid = uuid.UUID(str(shipment_id_raw))
                except TypeError, ValueError:
                    shipment_uuid = None
                if shipment_uuid is not None:
                    order = await self._order_repo.get_by_cross_border_shipment(
                        shipment_uuid
                    )
                    if order is not None:
                        order_id = order.id

        if order_id is None:
            self._logger.warning(
                "dobropost.status.skip",
                reason="no_order_for_shipment",
                dp_shipment_id=dp_shipment_id,
                status_id=status_id,
            )
            return

        action = map_status_id_to_action(status_id)
        self._logger.info(
            "dobropost.status.dispatch",
            order_id=str(order_id),
            status_id=status_id,
            label=status_label(status_id),
            action=action.value,
        )
        try:
            if action is DobroPostFsmAction.ARRIVED_IN_RU:
                await self._arrived.handle(
                    MarkOrderArrivedInRuCommand(order_id=order_id)
                )
            elif action is DobroPostFsmAction.PASSPORT_INVALID:
                await self._hold.handle(
                    HoldOrderCommand(
                        order_id=order_id, reason=HoldReason.PASSPORT_INVALID
                    )
                )
            elif action is DobroPostFsmAction.CUSTOMS_REJECT:
                await self._cancel.handle(
                    CancelOrderCommand(
                        order_id=order_id,
                        identity_id=None,
                        reason=CancellationReason.LOGISTICS_CUSTOMS_REJECTED,
                        actor_id=f"dobropost:{status_id}",
                        idempotency_key=f"customs-reject:{order_id}:{status_id}",
                    )
                )
            elif action is DobroPostFsmAction.PARCEL_LOST:
                await self._cancel.handle(
                    CancelOrderCommand(
                        order_id=order_id,
                        identity_id=None,
                        reason=CancellationReason.LOGISTICS_LOST_IN_TRANSIT,
                        actor_id="dobropost:lost",
                        idempotency_key=f"lost:{order_id}:{status_id}",
                    )
                )
        except OrderNotFoundError:
            self._logger.warning(
                "dobropost.status.skip",
                reason="order_missing",
                order_id=str(order_id),
            )


class DobroPostPassportInvalidConsumer:
    """``passportValidationStatus = false`` from DaData webhook → ON_HOLD."""

    def __init__(
        self,
        order_repo: IOrderRepository,
        mapping_repo: IDobroPostShipmentMappingRepository,
        hold_handler: HoldOrderHandler,
        logger: ILogger,
    ) -> None:
        self._order_repo = order_repo
        self._mapping_repo = mapping_repo
        self._hold = hold_handler
        self._logger = logger.bind(consumer="DobroPostPassportInvalidConsumer")

    async def handle(self, payload: dict) -> None:
        valid = payload.get("passport_validation_status")
        if valid is None:
            valid = payload.get("passportValidationStatus")
        if valid is not False:
            return
        order_id: uuid.UUID | None = None
        dp_id = _coerce_int(
            payload.get("dp_shipment_id")
            or payload.get("dpShipmentId")
            or payload.get("shipmentId")
        )
        if dp_id is not None:
            mapping = await self._mapping_repo.get_by_dp_shipment_id(dp_id)
            if mapping is not None:
                order_id = mapping.order_id
        if order_id is None:
            shipment_raw = payload.get("shipment_id")
            if shipment_raw is not None:
                try:
                    shipment_uuid = uuid.UUID(str(shipment_raw))
                except TypeError, ValueError:
                    shipment_uuid = None
                if shipment_uuid is not None:
                    order = await self._order_repo.get_by_cross_border_shipment(
                        shipment_uuid
                    )
                    if order is not None:
                        order_id = order.id
        if order_id is None:
            self._logger.warning(
                "dobropost.passport_invalid.skip",
                reason="no_order_for_shipment",
                dp_shipment_id=dp_id,
            )
            return
        try:
            await self._hold.handle(
                HoldOrderCommand(order_id=order_id, reason=HoldReason.PASSPORT_INVALID)
            )
        except OrderNotFoundError:
            self._logger.warning(
                "dobropost.passport_invalid.skip", reason="order_missing"
            )


class RussianCarrierTrackingConsumer:
    """Maps russian carrier canonical events into Order FSM commands."""

    def __init__(
        self,
        order_repo: IOrderRepository,
        in_last_mile_handler: MarkOrderInLastMileHandler,
        awaiting_pickup_handler: MarkOrderAwaitingPickupHandler,
        delivered_handler: MarkOrderDeliveredHandler,
        returning_handler: MarkOrderReturningToWarehouseHandler,
        logger: ILogger,
    ) -> None:
        self._order_repo = order_repo
        self._in_last_mile = in_last_mile_handler
        self._awaiting_pickup = awaiting_pickup_handler
        self._delivered = delivered_handler
        self._returning = returning_handler
        self._logger = logger.bind(consumer="RussianCarrierTrackingConsumer")

    async def handle(self, payload: dict) -> None:
        canonical = payload.get("canonical_status") or payload.get("status")
        shipment_id_raw = payload.get("shipment_id") or payload.get(
            "last_mile_shipment_id"
        )
        if canonical is None or shipment_id_raw is None:
            self._logger.warning("russian_carrier.skip", reason="bad_payload")
            return
        try:
            shipment_id = uuid.UUID(str(shipment_id_raw))
        except TypeError, ValueError:
            return
        order = await self._order_repo.get_by_last_mile_shipment(shipment_id)
        if order is None:
            self._logger.warning(
                "russian_carrier.skip",
                reason="no_order_for_shipment",
                shipment_id=str(shipment_id),
            )
            return

        normalized = str(canonical).upper()
        try:
            if normalized in {"IN_TRANSIT", "OUT_FOR_DELIVERY"}:
                await self._in_last_mile.handle(
                    MarkOrderInLastMileCommand(order_id=order.id)
                )
            elif normalized == "AT_PICKUP_POINT":
                await self._awaiting_pickup.handle(
                    MarkOrderAwaitingPickupCommand(order_id=order.id)
                )
            elif normalized == "DELIVERED":
                await self._delivered.handle(
                    MarkOrderDeliveredCommand(order_id=order.id)
                )
            elif normalized in {"RETURN_TO_SENDER", "REFUSED", "FAILURE"}:
                await self._returning.handle(
                    MarkOrderReturningToWarehouseCommand(
                        order_id=order.id, reason=normalized.lower()
                    )
                )
        except OrderNotFoundError:
            self._logger.warning("russian_carrier.skip", reason="order_missing")
