"""Consumer-driven command: PROCURED → ARRIVED_IN_RU."""

import uuid
from dataclasses import dataclass

from src.modules.order.application._history import record_history
from src.modules.order.application.ports import IRussianCarrierGateway
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
class MarkOrderArrivedInRuCommand:
    order_id: uuid.UUID


class MarkOrderArrivedInRuHandler:
    def __init__(
        self,
        order_repo: IOrderRepository,
        russian_carrier: IRussianCarrierGateway,
        history_writer: IOrderStateHistoryWriter,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._order_repo = order_repo
        self._russian = russian_carrier
        self._history = history_writer
        self._uow = uow
        self._logger = logger.bind(handler="MarkOrderArrivedInRuHandler")

    async def handle(self, command: MarkOrderArrivedInRuCommand) -> None:
        async with self._uow:
            order = await self._order_repo.get_for_update(command.order_id)
            if order is None:
                raise OrderNotFoundError(order_id=str(command.order_id))
            if order.status != OrderStatus.PROCURED:
                self._logger.info(
                    "order.arrived_in_ru.noop",
                    order_id=str(order.id),
                    status=order.status.value,
                )
                return
            if order.cross_border_shipment_id is None:
                self._logger.warning(
                    "order.arrived_in_ru.skip",
                    order_id=str(order.id),
                    reason="no_cross_border_shipment",
                )
                return

            pre = order.status
            order.mark_arrived_in_ru()

            last_mile_shipment_id = await self._russian.book_last_mile(
                order_id=order.id,
                cross_border_shipment_id=order.cross_border_shipment_id,
                pickup_point=order.pickup_point,
                idempotency_key=f"order:{order.id}:lastmile",
            )
            order.attach_last_mile_shipment(last_mile_shipment_id)
            await self._order_repo.update(order)
            await record_history(
                order=order,
                history_writer=self._history,
                actor=HistoryActor(actor_type="webhook", actor_id="dobropost"),
                pre_commit_status=pre,
            )
            self._uow.register_aggregate(order)
            await self._uow.commit()

            self._logger.info(
                "order.arrived_in_ru",
                order_id=str(order.id),
                last_mile_shipment_id=str(last_mile_shipment_id),
            )
