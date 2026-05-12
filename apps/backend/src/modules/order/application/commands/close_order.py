"""Cron-driven command: DELIVERED → CLOSED after 14-day return window."""

import uuid
from dataclasses import dataclass

from src.modules.order.application._history import record_history
from src.modules.order.domain.exceptions import OrderNotFoundError
from src.modules.order.domain.interfaces import (
    HistoryActor,
    IOrderRepository,
    IOrderStateHistoryWriter,
)
from shared.interfaces.logger import ILogger
from shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class CloseOrderCommand:
    order_id: uuid.UUID


class CloseOrderHandler:
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
        self._logger = logger.bind(handler="CloseOrderHandler")

    async def handle(self, command: CloseOrderCommand) -> None:
        async with self._uow:
            order = await self._order_repo.get_for_update(command.order_id)
            if order is None:
                raise OrderNotFoundError(order_id=str(command.order_id))
            pre = order.status
            order.close()
            await self._order_repo.update(order)
            await record_history(
                order=order,
                history_writer=self._history,
                actor=HistoryActor(actor_type="system", actor_id="cron:close"),
                pre_commit_status=pre,
            )
            self._uow.register_aggregate(order)
            await self._uow.commit()
            self._logger.info("order.closed", order_id=str(order.id))
