"""Consumer: book the DobroPost cross-border shipment after Order is procured.

ORD-006 (D1.2 / GAP B fix). Pre-fix the booking happened synchronously
inside ``ProcureOrderHandler``, which left a split-state risk: capture
succeeded, DobroPost down → order stuck in PAID with no shipment +
manual refund. Post-fix the booking is driven by an outbox consumer
with retry semantics inside the DobroPost adapter
(``DOBROPOST_RETRY_MAX_ATTEMPTS`` + circuit breaker). When the
adapter exhausts its budget the consumer pivots the Order into
``ON_HOLD`` with reason ``BOOKING_FAILED`` so the manager can triage
from the admin dashboard instead of the order silently rotting in
PROCURED.
"""

from __future__ import annotations

import uuid

from src.modules.order.application.commands.hold_order import (
    HoldOrderCommand,
    HoldOrderHandler,
)
from src.modules.order.application.ports import IDobroPostGateway
from src.modules.order.domain.exceptions import OrderNotFoundError
from src.modules.order.domain.interfaces import IOrderRepository
from src.modules.order.domain.value_objects import HoldReason, OrderStatus
from shared.interfaces.logger import ILogger
from shared.interfaces.uow import IUnitOfWork


class OrderProcuredConsumer:
    """Books DobroPost shipment + attaches it; falls back to HOLD on failure."""

    def __init__(
        self,
        order_repo: IOrderRepository,
        dobropost_gateway: IDobroPostGateway,
        hold_handler: HoldOrderHandler,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._order_repo = order_repo
        self._dobropost = dobropost_gateway
        self._hold = hold_handler
        self._uow = uow
        self._logger = logger.bind(consumer="OrderProcuredConsumer")

    async def handle(self, payload: dict) -> None:
        order_id_raw = payload.get("order_id")
        if order_id_raw is None:
            self._logger.warning("order.procured.skip", reason="missing_order_id")
            return
        try:
            order_id = uuid.UUID(str(order_id_raw))
        except TypeError, ValueError:
            self._logger.warning(
                "order.procured.skip",
                reason="bad_order_id",
                raw=str(order_id_raw),
            )
            return

        # Pre-flight: load outside any txn so the booking call doesn't
        # hold a row lock. Idempotent on already-attached shipments.
        order = await self._order_repo.get(order_id)
        if order is None:
            self._logger.warning(
                "order.procured.skip", reason="order_missing", order_id=str(order_id)
            )
            return
        if order.cross_border_shipment_id is not None:
            self._logger.info(
                "order.procured.noop",
                reason="cross_border_shipment_already_attached",
                order_id=str(order_id),
                shipment_id=str(order.cross_border_shipment_id),
            )
            return
        if order.status != OrderStatus.PROCURED:
            # Order moved (cancelled, ON_HOLD via another path) before
            # the consumer ran. Nothing to book.
            self._logger.info(
                "order.procured.noop",
                reason="status_changed",
                order_id=str(order_id),
                status=order.status.value,
            )
            return
        if order.incoming_declaration is None:
            # ProcureOrderHandler always sets the declaration before
            # commit, so this shouldn't happen — surface loudly if it
            # does (data corruption / out-of-band write).
            self._logger.error(
                "order.procured.skip",
                reason="missing_incoming_declaration",
                order_id=str(order_id),
            )
            return

        # Real booking call. The adapter owns retry + circuit breaker
        # (DOBROPOST_RETRY_MAX_ATTEMPTS / _BACKOFF / _CIRCUIT_*).
        try:
            shipment_id = await self._dobropost.book_cross_border(
                order_id=order.id,
                identity_id=order.identity_id,
                incoming_declaration=order.incoming_declaration.value,
                idempotency_key=f"order:{order.id}:dobropost",
            )
        except Exception as exc:
            # Adapter exhausted its retry budget — pivot the Order
            # into ON_HOLD(BOOKING_FAILED). Manager triages from the
            # admin dashboard; resume via ResumeOrderHandler once the
            # DobroPost outage clears.
            self._logger.exception(
                "order.procured.dobropost_failed",
                order_id=str(order.id),
                exc_type=type(exc).__name__,
            )
            try:
                await self._hold.handle(
                    HoldOrderCommand(
                        order_id=order.id, reason=HoldReason.BOOKING_FAILED
                    )
                )
            except OrderNotFoundError:
                self._logger.warning(
                    "order.procured.hold_skip",
                    reason="order_missing_after_failure",
                    order_id=str(order.id),
                )
            return

        # Booking succeeded — attach + persist. Run inside its own UoW
        # so the attach is atomic with the version bump.
        async with self._uow:
            fresh = await self._order_repo.get_for_update(order.id)
            if fresh is None:
                self._logger.warning(
                    "order.procured.attach_skip",
                    reason="order_missing_after_book",
                    order_id=str(order.id),
                    shipment_id=str(shipment_id),
                )
                return
            if fresh.cross_border_shipment_id is not None:
                # Concurrent attach — DobroPost adapter is idempotent
                # via the deterministic UUID, but a parallel run might
                # have committed first. Drop silently.
                self._logger.info(
                    "order.procured.attach_noop",
                    order_id=str(order.id),
                    existing=str(fresh.cross_border_shipment_id),
                    incoming=str(shipment_id),
                )
                return
            fresh.attach_cross_border_shipment(shipment_id)
            await self._order_repo.update(fresh)
            self._uow.register_aggregate(fresh)
            await self._uow.commit()

        self._logger.info(
            "order.procured.attached",
            order_id=str(order.id),
            shipment_id=str(shipment_id),
        )
