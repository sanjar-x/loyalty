"""Unit test for the BUY_NOW_ENABLED kill-switch.

Гарантирует, что когда флаг выключен, endpoint бросает
``ServiceUnavailableError(BUY_NOW_DISABLED)`` ДО вызова handler'а —
handler не выполняется, никакой Order / PaymentIntent / outbox row не
создаётся. Прогон без HTTP-стека, прямой вызов router-функции.

Sprint 1.5 / Q10. See ADR-010.
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest

from src.modules.order.presentation.router_orders import buy_now_order
from src.modules.order.presentation.schemas import BuyNowOrderRequest
from src.shared.exceptions import ServiceUnavailableError
from src.shared.interfaces.auth import AuthContext

pytestmark = pytest.mark.unit


class _ExplodingHandler:
    """Handler-stub, который роняет тест если его вообще вызвали.

    Если guard в endpoint'е перестанет fire'ить — handler.handle()
    зайдёт сюда, AssertionError утопит тест на ясной строке.
    """

    async def handle(self, _command: Any) -> None:
        raise AssertionError(
            "Handler must NOT be invoked when BUY_NOW_ENABLED=False — "
            "the kill-switch guard regressed"
        )


def _request() -> BuyNowOrderRequest:
    return BuyNowOrderRequest(
        sku_id=uuid.uuid4(),
        quantity=1,
        recipient_id=uuid.uuid4(),
        pickup_carrier="cdek",
        pickup_point_id="MSK-1",
        idempotency_key="buy-now-flag-test-12345",
    )


def _auth() -> AuthContext:
    return AuthContext(
        identity_id=uuid.uuid4(),
        session_id=uuid.uuid4(),
        is_staff=False,
    )


async def test_buy_now_returns_503_when_flag_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.bootstrap import config as cfg

    monkeypatch.setattr(cfg.settings, "BUY_NOW_ENABLED", False)

    with pytest.raises(ServiceUnavailableError) as exc:
        await buy_now_order(
            body=_request(),
            auth=_auth(),
            handler=_ExplodingHandler(),  # ty:ignore[invalid-argument-type]
        )

    assert exc.value.error_code == "BUY_NOW_DISABLED"
    assert exc.value.status_code == 503
    assert "disabled" in exc.value.message.lower()


async def test_buy_now_handler_invoked_when_flag_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Positive control: with flag=True, handler IS invoked.

    Confirms что guard branch'ит только на False — иначе любой
    refactor, который случайно инвертирует условие, не отловится
    одним только negative-тестом выше.
    """
    from src.bootstrap import config as cfg

    monkeypatch.setattr(cfg.settings, "BUY_NOW_ENABLED", True)

    called: dict[str, bool] = {"flag": False}

    class _RecordingHandler:
        async def handle(self, _command: Any) -> Any:
            called["flag"] = True

            class _Result:
                order_id = uuid.uuid4()
                payment_intent_id = uuid.uuid4()
                client_secret = "x"
                total_amount = 100
                currency = "RUB"
                auto_captured = True

            return _Result()

    response = await buy_now_order(
        body=_request(),
        auth=_auth(),
        handler=_RecordingHandler(),  # ty:ignore[invalid-argument-type]
    )

    assert called["flag"] is True
    assert response.auto_captured is True
