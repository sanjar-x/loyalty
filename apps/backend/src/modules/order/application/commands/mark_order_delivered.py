"""Consumer-driven command: AWAITING_PICKUP → DELIVERED."""

import uuid
from dataclasses import dataclass

from src.modules.order.application._history import record_history
from src.modules.order.domain.exceptions import OrderNotFoundError
from src.modules.order.domain.interfaces import (
    HistoryActor,
    IOrderRepository,
    IOrderStateHistoryWriter,
)
from src.modules.order.domain.value_objects import OrderStatus
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class MarkOrderDeliveredCommand:
    order_id: uuid.UUID


class MarkOrderDeliveredHandler:
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
        self._logger = logger.bind(handler="MarkOrderDeliveredHandler")

    async def handle(self, command: MarkOrderDeliveredCommand) -> None:
        async with self._uow:
            order = await self._order_repo.get_for_update(command.order_id)
            if order is None:
                raise OrderNotFoundError(order_id=str(command.order_id))
            if order.status != OrderStatus.AWAITING_PICKUP:
                self._logger.info(
                    "order.delivered.noop",
                    order_id=str(order.id),
                    status=order.status.value,
                )
                return
            pre = order.status
            order.mark_delivered()
            await self._order_repo.update(order)
            await record_history(
                order=order,
                history_writer=self._history,
                actor=HistoryActor(actor_type="webhook", actor_id="russian_carrier"),
                pre_commit_status=pre,
            )
            self._uow.register_aggregate(order)
            await self._uow.commit()
            self._logger.info("order.delivered", order_id=str(order.id))
