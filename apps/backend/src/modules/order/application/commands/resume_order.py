"""Resume order from ON_HOLD back to its pre-hold state."""

import uuid
from dataclasses import dataclass

from src.modules.order.application._history import record_history
from src.modules.order.domain.exceptions import OrderNotFoundError
from src.modules.order.domain.interfaces import (
    HistoryActor,
    IOrderRepository,
    IOrderStateHistoryWriter,
)
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class ResumeOrderCommand:
    order_id: uuid.UUID


class ResumeOrderHandler:
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
        self._logger = logger.bind(handler="ResumeOrderHandler")

    async def handle(self, command: ResumeOrderCommand) -> None:
        async with self._uow:
            order = await self._order_repo.get_for_update(command.order_id)
            if order is None:
                raise OrderNotFoundError(order_id=str(command.order_id))
            pre = order.status
            order.resume_from_hold()
            await self._order_repo.update(order)
            await record_history(
                order=order,
                history_writer=self._history,
                actor=HistoryActor(actor_type="manager", actor_id="resume"),
                pre_commit_status=pre,
            )
            self._uow.register_aggregate(order)
            await self._uow.commit()
            self._logger.info("order.resumed", order_id=str(order.id))
