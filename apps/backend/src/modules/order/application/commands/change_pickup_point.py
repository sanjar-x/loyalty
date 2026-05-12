"""Change pickup point — allowed before last-mile shipment is created.

This is informational (no FSM transition); ``record_history`` skips it
(no FSM event_type), but we still call it for consistency with other
handlers — adding new FSM-bearing events later (e.g. address-validation
failure) auto-falls into the audit log.
"""

import uuid
from dataclasses import dataclass

from src.modules.order.application._history import record_history
from src.modules.order.domain.exceptions import OrderNotFoundError
from src.modules.order.domain.interfaces import (
    HistoryActor,
    IOrderRepository,
    IOrderStateHistoryWriter,
)
from src.modules.order.domain.value_objects import (
    PickupCarrier,
    PickupPointPreference,
)
from shared.interfaces.logger import ILogger
from shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class ChangePickupPointCommand:
    order_id: uuid.UUID
    identity_id: uuid.UUID | None
    carrier: str
    point_id: str


class ChangePickupPointHandler:
    def __init__(
        self,
        order_repo: IOrderRepository,
        history_writer: IOrderStateHistoryWriter,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._order_repo = order_repo
        self._history = history_writer
        self._uow = uow
        self._logger = logger.bind(handler="ChangePickupPointHandler")

    async def handle(self, command: ChangePickupPointCommand) -> None:
        async with self._uow:
            order = await self._order_repo.get_for_update(command.order_id)
            if order is None:
                raise OrderNotFoundError(order_id=str(command.order_id))
            if (
                command.identity_id is not None
                and order.identity_id != command.identity_id
            ):
                raise OrderNotFoundError(order_id=str(command.order_id))
            new = PickupPointPreference(
                carrier=PickupCarrier(command.carrier),
                point_id=command.point_id,
            )
            pre = order.status
            order.change_pickup_point(new)
            await self._order_repo.update(order)
            await record_history(
                order=order,
                history_writer=self._history,
                actor=HistoryActor(
                    actor_type=("customer" if command.identity_id else "manager"),
                    actor_id=str(command.identity_id or "admin"),
                ),
                pre_commit_status=pre,
            )
            self._uow.register_aggregate(order)
            await self._uow.commit()
            self._logger.info(
                "order.pickup_point_changed",
                order_id=str(order.id),
                carrier=command.carrier,
                point_id=command.point_id,
            )
