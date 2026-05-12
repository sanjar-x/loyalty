"""Return-flow commands.

* ``RegisterReturn``: DELIVERED → RETURN_IN_PROGRESS.
* ``MarkReturnReceived``: RETURN_IN_PROGRESS → RETURNED.
* ``MarkOrderReturningToWarehouse``: IN_LAST_MILE / AWAITING_PICKUP →
  RETURNING_TO_RU_WAREHOUSE.
* ``MarkOrderNotDelivered``: RETURNING_TO_RU_WAREHOUSE → NOT_DELIVERED.
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
from shared.interfaces.logger import ILogger
from shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class RegisterReturnCommand:
    order_id: uuid.UUID
    identity_id: uuid.UUID | None
    reason: str = ""


class RegisterReturnHandler:
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
        self._logger = logger.bind(handler="RegisterReturnHandler")

    async def handle(self, command: RegisterReturnCommand) -> None:
        async with self._uow:
            order = await self._order_repo.get_for_update(command.order_id)
            if order is None:
                raise OrderNotFoundError(order_id=str(command.order_id))
            if (
                command.identity_id is not None
                and order.identity_id != command.identity_id
            ):
                raise OrderNotFoundError(order_id=str(command.order_id))
            pre = order.status
            order.request_return(reason=command.reason)
            await self._order_repo.update(order)
            await record_history(
                order=order,
                history_writer=self._history,
                actor=HistoryActor(
                    actor_type="customer",
                    actor_id=str(command.identity_id or ""),
                ),
                pre_commit_status=pre,
            )
            self._uow.register_aggregate(order)
            await self._uow.commit()
            self._logger.info("order.return_requested", order_id=str(order.id))


@dataclass(frozen=True)
class MarkReturnReceivedCommand:
    order_id: uuid.UUID


class MarkReturnReceivedHandler:
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
        self._logger = logger.bind(handler="MarkReturnReceivedHandler")

    async def handle(self, command: MarkReturnReceivedCommand) -> None:
        async with self._uow:
            order = await self._order_repo.get_for_update(command.order_id)
            if order is None:
                raise OrderNotFoundError(order_id=str(command.order_id))
            pre = order.status
            order.mark_returned()
            await self._order_repo.update(order)
            await record_history(
                order=order,
                history_writer=self._history,
                actor=HistoryActor(actor_type="manager", actor_id="return"),
                pre_commit_status=pre,
            )
            self._uow.register_aggregate(order)
            await self._uow.commit()
            self._logger.info("order.returned", order_id=str(order.id))


@dataclass(frozen=True)
class MarkOrderReturningToWarehouseCommand:
    order_id: uuid.UUID
    reason: str = ""


class MarkOrderReturningToWarehouseHandler:
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
        self._logger = logger.bind(handler="MarkOrderReturningToWarehouseHandler")

    async def handle(self, command: MarkOrderReturningToWarehouseCommand) -> None:
        async with self._uow:
            order = await self._order_repo.get_for_update(command.order_id)
            if order is None:
                raise OrderNotFoundError(order_id=str(command.order_id))
            pre = order.status
            order.mark_returning_to_warehouse(reason=command.reason)
            await self._order_repo.update(order)
            await record_history(
                order=order,
                history_writer=self._history,
                actor=HistoryActor(actor_type="webhook", actor_id="russian_carrier"),
                pre_commit_status=pre,
            )
            self._uow.register_aggregate(order)
            await self._uow.commit()
            self._logger.info(
                "order.returning_to_warehouse",
                order_id=str(order.id),
                reason=command.reason,
            )


@dataclass(frozen=True)
class MarkOrderNotDeliveredCommand:
    order_id: uuid.UUID


class MarkOrderNotDeliveredHandler:
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
        self._logger = logger.bind(handler="MarkOrderNotDeliveredHandler")

    async def handle(self, command: MarkOrderNotDeliveredCommand) -> None:
        async with self._uow:
            order = await self._order_repo.get_for_update(command.order_id)
            if order is None:
                raise OrderNotFoundError(order_id=str(command.order_id))
            pre = order.status
            order.mark_not_delivered()
            await self._order_repo.update(order)
            await record_history(
                order=order,
                history_writer=self._history,
                actor=HistoryActor(actor_type="manager", actor_id="not_delivered"),
                pre_commit_status=pre,
            )
            self._uow.register_aggregate(order)
            await self._uow.commit()
            self._logger.info("order.not_delivered", order_id=str(order.id))
