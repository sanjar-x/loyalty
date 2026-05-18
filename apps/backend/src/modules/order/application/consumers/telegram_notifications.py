"""Customer-facing Telegram push notifications for order lifecycle events.

T-2 / D3.1. Consumes the order FSM transitions that the customer cares
about (procured, arrived in RU, last-mile booked, awaiting pickup,
delivered) and pushes a localized HTML message to the customer's
Telegram chat — *if* they have a Telegram-linked identity.

Flow per event:

1. Resolve ``order_id`` from the outbox payload.
2. Load the Order aggregate (gives us ``identity_id`` and snapshots).
3. Resolve ``identity_id`` → Telegram ``chat_id`` via
   :class:`ITelegramChatLookup`. ``None`` → skip (customer signed up
   via email/OIDC without Telegram).
4. Format an HTML message (Russian, customer-facing) and push via
   :class:`ITelegramNotifier`.

Idempotency: the outbox handler bridge (``order/infrastructure/tasks``)
wraps every consumer in ``run_inbox_idempotent``, so duplicate broker
deliveries are no-ops.
"""

from __future__ import annotations

import uuid
from typing import Final

from src.modules.order.application.ports import (
    ITelegramChatLookup,
    ITelegramNotifier,
)
from src.modules.order.domain.entities import Order
from src.modules.order.domain.interfaces import IOrderRepository
from src.shared.interfaces.logger import ILogger

# Carrier code → human-readable Russian label for last-mile push.
_PICKUP_CARRIER_LABELS_RU: Final[dict[str, str]] = {
    "cdek": "СДЭК",
    "yandex": "Яндекс Доставку",
    "boxberry": "Boxberry",
    "pochta": "Почту России",
}


def _format_order_number(order: Order) -> str:
    """Return the human-readable order number for display."""
    return order.number.value


def _format_pickup_target(order: Order) -> str:
    """Render the carrier label for last-mile push."""
    return _PICKUP_CARRIER_LABELS_RU.get(
        order.pickup_point.carrier.value,
        order.pickup_point.carrier.value,
    )


class TelegramOrderNotifier:
    """Outbox-consumer body for order-lifecycle Telegram push notifications.

    Each ``handle_*`` method consumes one event type. The dispatcher
    in ``order/infrastructure/tasks.py`` calls the right method based
    on the registered event_type → TaskIQ task mapping.
    """

    def __init__(
        self,
        order_repo: IOrderRepository,
        chat_lookup: ITelegramChatLookup,
        notifier: ITelegramNotifier,
        logger: ILogger,
    ) -> None:
        self._order_repo = order_repo
        self._chat_lookup = chat_lookup
        self._notifier = notifier
        self._logger = logger.bind(consumer="TelegramOrderNotifier")

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    async def on_order_paid(self, payload: dict) -> None:
        """Bridge ``OrderPaidEvent`` → "оплата принята" push.

        Закрывает разрыв «оплатил → тишина 24-72 часа до procurement».
        Эмитится после успешного capture (cart-flow / Buy Now /
        walk-in без offline-receipt). Не эмитится для
        :class:`OrderPaidOfflineEvent` — там у admin'а есть свой
        канал коммуникации с customer'ом (walk-in).
        """
        order = await self._resolve_order(payload, event_type="OrderPaidEvent")
        if order is None:
            return
        chat_id = await self._resolve_chat_id(order, event_type="OrderPaidEvent")
        if chat_id is None:
            return
        text = (
            f"<b>Заказ {_format_order_number(order)} оплачен</b>\n\n"
            "Спасибо! Менеджер выкупит товар в ближайшие 24 часа — "
            "как только это произойдёт, мы сообщим, что посылка "
            "отправилась из Китая в Россию."
        )
        await self._send(chat_id, text, event_type="OrderPaidEvent", order=order)

    async def on_order_procured(self, payload: dict) -> None:
        order = await self._resolve_order(payload, event_type="OrderProcuredEvent")
        if order is None:
            return
        chat_id = await self._resolve_chat_id(order, event_type="OrderProcuredEvent")
        if chat_id is None:
            return
        text = (
            f"<b>Ваш заказ {_format_order_number(order)} выкуплен</b>\n\n"
            "Менеджер забрал товар у поставщика и передал его в логистику. "
            "Скоро посылка отправится из Китая в Россию — мы сообщим, "
            "когда она пересечёт границу."
        )
        await self._send(chat_id, text, event_type="OrderProcuredEvent", order=order)

    async def on_order_arrived_in_ru(self, payload: dict) -> None:
        order = await self._resolve_order(payload, event_type="OrderArrivedInRuEvent")
        if order is None:
            return
        chat_id = await self._resolve_chat_id(order, event_type="OrderArrivedInRuEvent")
        if chat_id is None:
            return
        text = (
            f"<b>Ваш заказ {_format_order_number(order)} прибыл в Россию</b>\n\n"
            "Посылка прошла таможню и поступила на склад. Сейчас мы готовим "
            "доставку до пункта выдачи — следующее сообщение придёт, когда "
            "перевозчик заберёт заказ."
        )
        await self._send(chat_id, text, event_type="OrderArrivedInRuEvent", order=order)

    async def on_order_entered_last_mile(self, payload: dict) -> None:
        order = await self._resolve_order(
            payload, event_type="OrderEnteredLastMileEvent"
        )
        if order is None:
            return
        chat_id = await self._resolve_chat_id(
            order, event_type="OrderEnteredLastMileEvent"
        )
        if chat_id is None:
            return
        text = (
            f"<b>Заказ {_format_order_number(order)} едет к вам</b>\n\n"
            f"Заказ передан в {_format_pickup_target(order)}. "
            "Мы пришлём уведомление, как только посылка прибудет в пункт "
            "выдачи."
        )
        await self._send(
            chat_id, text, event_type="OrderEnteredLastMileEvent", order=order
        )

    async def on_order_awaiting_pickup(self, payload: dict) -> None:
        order = await self._resolve_order(
            payload, event_type="OrderAwaitingPickupEvent"
        )
        if order is None:
            return
        chat_id = await self._resolve_chat_id(
            order, event_type="OrderAwaitingPickupEvent"
        )
        if chat_id is None:
            return
        text = (
            f"<b>Заказ {_format_order_number(order)} в пункте выдачи</b>\n\n"
            "Можно забирать! Не забудьте взять документ, удостоверяющий "
            "личность — данные паспорта мы передавали в таможню "
            "одновременно с оформлением посылки."
        )
        await self._send(
            chat_id, text, event_type="OrderAwaitingPickupEvent", order=order
        )

    async def on_order_delivered(self, payload: dict) -> None:
        order = await self._resolve_order(payload, event_type="OrderDeliveredEvent")
        if order is None:
            return
        chat_id = await self._resolve_chat_id(order, event_type="OrderDeliveredEvent")
        if chat_id is None:
            return
        text = (
            f"<b>Спасибо, что выбрали Loyality! 💛</b>\n\n"
            f"Ваш заказ {_format_order_number(order)} доставлен. "
            "В течение 14 дней действует возврат — если что-то не так, "
            "напишите нам в чат поддержки."
        )
        await self._send(chat_id, text, event_type="OrderDeliveredEvent", order=order)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _resolve_order(self, payload: dict, *, event_type: str) -> Order | None:
        raw_id = payload.get("order_id")
        if raw_id is None:
            self._logger.warning(
                "telegram_notify.skip",
                event_type=event_type,
                reason="missing_order_id",
            )
            return None
        try:
            order_id = uuid.UUID(str(raw_id))
        except TypeError, ValueError:
            self._logger.warning(
                "telegram_notify.skip",
                event_type=event_type,
                reason="bad_order_id",
            )
            return None
        order = await self._order_repo.get(order_id)
        if order is None:
            self._logger.warning(
                "telegram_notify.skip",
                event_type=event_type,
                reason="order_missing",
                order_id=str(order_id),
            )
            return None
        return order

    async def _resolve_chat_id(self, order: Order, *, event_type: str) -> int | None:
        chat_id = await self._chat_lookup.get_chat_id(order.identity_id)
        if chat_id is None:
            self._logger.info(
                "telegram_notify.skip",
                event_type=event_type,
                reason="not_telegram_linked",
                order_id=str(order.id),
                identity_id=str(order.identity_id),
            )
            return None
        return chat_id

    async def _send(
        self, chat_id: int, html: str, *, event_type: str, order: Order
    ) -> None:
        await self._notifier.send_html(chat_id=chat_id, html=html)
        self._logger.info(
            "telegram_notify.sent",
            event_type=event_type,
            order_id=str(order.id),
            chat_id=chat_id,
        )
