"""Background services for the Order module.

* ``StuckInCnDetector`` — PROCURED + last update > 14 days → HoldOrder
  (HoldReason.STUCK_IN_CN).
* ``HoldTtlExpiredCanceller`` — ON_HOLD + hold_until passed →
  Cancel (SYSTEM_HOLD_TTL_EXPIRED, with refund).
* ``ReturnWindowCloser`` — DELIVERED + 14 days passed → CloseOrder.

These services are stateless; they encapsulate one tick of work and
are invoked from TaskIQ scheduled tasks. Each iteration processes up
to 100 orders; the cron runs frequently enough that backlog is bounded.
"""

from datetime import UTC, datetime

from src.modules.order.application.commands.cancel_order import (
    CancelOrderCommand,
    CancelOrderHandler,
)
from src.modules.order.application.commands.close_order import (
    CloseOrderCommand,
    CloseOrderHandler,
)
from src.modules.order.application.commands.hold_order import (
    HoldOrderCommand,
    HoldOrderHandler,
)
from src.modules.order.domain.exceptions import (
    OrderHoldStateError,
    OrderInvalidTransitionError,
)
from src.modules.order.domain.interfaces import IOrderRepository
from src.modules.order.domain.value_objects import (
    CancellationReason,
    HoldReason,
)
from src.modules.order.infrastructure.repositories.order_repository import (
    close_threshold,
    stuck_in_cn_threshold,
)
from shared.interfaces.logger import ILogger

STUCK_IN_CN_THRESHOLD_DAYS = 14


class StuckInCnDetector:
    def __init__(
        self,
        order_repo: IOrderRepository,
        hold_handler: HoldOrderHandler,
        logger: ILogger,
    ) -> None:
        self._order_repo = order_repo
        self._hold = hold_handler
        self._logger = logger.bind(service="StuckInCnDetector")

    async def run(self) -> int:
        threshold = stuck_in_cn_threshold(
            datetime.now(UTC), days=STUCK_IN_CN_THRESHOLD_DAYS
        )
        candidates = await self._order_repo.find_stuck_in_cn(threshold=threshold)
        held = 0
        for order in candidates:
            try:
                await self._hold.handle(
                    HoldOrderCommand(order_id=order.id, reason=HoldReason.STUCK_IN_CN)
                )
                held += 1
            except OrderHoldStateError:
                continue
        self._logger.info("stuck_in_cn.tick", held=held)
        return held


class HoldTtlExpiredCanceller:
    def __init__(
        self,
        order_repo: IOrderRepository,
        cancel_handler: CancelOrderHandler,
        logger: ILogger,
    ) -> None:
        self._order_repo = order_repo
        self._cancel = cancel_handler
        self._logger = logger.bind(service="HoldTtlExpiredCanceller")

    async def run(self) -> int:
        candidates = await self._order_repo.find_hold_ttl_expired()
        cancelled = 0
        for order in candidates:
            try:
                await self._cancel.handle(
                    CancelOrderCommand(
                        order_id=order.id,
                        identity_id=None,
                        reason=CancellationReason.SYSTEM_HOLD_TTL_EXPIRED,
                        actor_id="cron:hold_ttl",
                        idempotency_key=f"hold-ttl:{order.id}",
                    )
                )
                cancelled += 1
            except OrderInvalidTransitionError:
                continue
        self._logger.info("hold_ttl.tick", cancelled=cancelled)
        return cancelled


class ReturnWindowCloser:
    def __init__(
        self,
        order_repo: IOrderRepository,
        close_handler: CloseOrderHandler,
        logger: ILogger,
    ) -> None:
        self._order_repo = order_repo
        self._close = close_handler
        self._logger = logger.bind(service="ReturnWindowCloser")

    async def run(self) -> int:
        threshold = close_threshold(datetime.now(UTC))
        candidates = await self._order_repo.find_eligible_for_close(threshold=threshold)
        closed = 0
        for order in candidates:
            try:
                await self._close.handle(CloseOrderCommand(order_id=order.id))
                closed += 1
            except OrderInvalidTransitionError:
                continue
        self._logger.info("close_window.tick", closed=closed)
        return closed
