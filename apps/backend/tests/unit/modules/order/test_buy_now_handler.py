"""Unit tests for ``CreateBuyNowOrderHandler`` (no DB; fake ports).

Covers:

* happy-path flow (single SKU, recipient resolved, Order created in
  PENDING — or PAID when ``PAYMENT_AUTO_CAPTURE_ON_AUTHORIZE`` is on);
* SKU usability checks (missing / inactive / unpriced);
* recipient ownership + archive checks;
* delivery-quote ownership / currency / expiry;
* idempotency replay (second call returns same order, no double-spend);
* phantom cart_id and ``is_walk_in=False`` invariant.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any

import pytest

from src.modules.order.application.commands.create_buy_now_order import (
    CreateBuyNowOrderCommand,
    CreateBuyNowOrderHandler,
)
from src.modules.order.application.ports import (
    CatalogSkuSnapshot,
    PaymentTicket,
)
from src.modules.order.domain.entities import Order
from src.modules.order.domain.exceptions import IdempotencyKeyConflictError
from src.modules.order.domain.interfaces import (
    DeliveryQuoteLookupResult,
    PassportLookupResult,
    RecipientLookupResult,
)
from src.modules.order.domain.value_objects import (
    OrderCreationSource,
    OrderStatus,
    PickupCarrier,
    PickupPointPreference,
)
from src.shared.exceptions import UnprocessableEntityError, ValidationError

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class _FakeOrderRepo:
    def __init__(self) -> None:
        self.orders: dict[uuid.UUID, Order] = {}

    async def add(self, order: Order) -> Order:
        self.orders[order.id] = order
        return order

    async def get(self, order_id: uuid.UUID) -> Order | None:
        return self.orders.get(order_id)

    async def update(self, order: Order) -> Order:
        self.orders[order.id] = order
        return order


class _FakeSkuReader:
    def __init__(self, snapshots: dict[uuid.UUID, CatalogSkuSnapshot]) -> None:
        self._snapshots = snapshots
        self.calls = 0

    async def get_many(
        self, sku_ids: Any, *, locale: str = "ru"
    ) -> dict[uuid.UUID, CatalogSkuSnapshot]:
        self.calls += 1
        return {sid: self._snapshots[sid] for sid in sku_ids if sid in self._snapshots}


class _FakeRecipientLookup:
    def __init__(self, records: dict[uuid.UUID, RecipientLookupResult]) -> None:
        self._records = records

    async def get(self, recipient_id: uuid.UUID) -> RecipientLookupResult | None:
        return self._records.get(recipient_id)


class _FakePassportLookup:
    def __init__(self, records: dict[uuid.UUID, PassportLookupResult]) -> None:
        self._records = records

    async def get(self, passport_id: uuid.UUID) -> PassportLookupResult | None:
        return self._records.get(passport_id)


class _FakeDeliveryQuoteLookup:
    def __init__(self, records: dict[uuid.UUID, DeliveryQuoteLookupResult]) -> None:
        self._records = records

    async def get(self, quote_id: uuid.UUID) -> DeliveryQuoteLookupResult | None:
        return self._records.get(quote_id)


class _FakePaymentGateway:
    def __init__(self) -> None:
        self.authorize_calls = 0
        self.capture_calls: list[uuid.UUID] = []
        self.refund_calls: list[uuid.UUID] = []
        self._intent_id = uuid.uuid4()

    async def authorize(
        self,
        *,
        order_id: uuid.UUID,
        identity_id: uuid.UUID,
        amount: int,
        currency: str,
        idempotency_key: str,
        provider: str,
    ) -> PaymentTicket:
        self.authorize_calls += 1
        return PaymentTicket(intent_id=self._intent_id, client_secret="secret-xyz")

    async def capture(self, *, intent_id: uuid.UUID, idempotency_key: str) -> None:
        self.capture_calls.append(intent_id)

    async def refund(self, *, intent_id: uuid.UUID, idempotency_key: str) -> None:
        self.refund_calls.append(intent_id)


class _FakeIdem:
    def __init__(self) -> None:
        self._reserved: dict[tuple[str, str], uuid.UUID] = {}
        self._results: dict[tuple[str, str], uuid.UUID] = {}

    async def reserve(self, *, key, identity_id, scope, expires_at) -> bool:
        if (scope, key) in self._reserved:
            return False
        self._reserved[(scope, key)] = identity_id
        return True

    async def attach_result(self, *, key, scope, resource_id) -> None:
        self._results[(scope, key)] = resource_id

    async def get_result(self, *, key, scope) -> uuid.UUID | None:
        return self._results.get((scope, key))


class _FakeHistory:
    def __init__(self) -> None:
        self.calls: list[Any] = []

    async def append(self, **kwargs) -> None:
        self.calls.append(kwargs)


class _FakeUow:
    def __init__(self) -> None:
        self.committed = False
        self.aggregates: list[Any] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def flush(self) -> None:
        pass

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        pass

    def register_aggregate(self, aggregate: Any) -> None:
        self.aggregates.append(aggregate)

    def enqueue_external_event(self, **kwargs: Any) -> None:
        pass


class _FakeLogger:
    def bind(self, **_kwargs) -> _FakeLogger:
        return self

    def info(self, *args, **kwargs) -> None:
        pass

    def warning(self, *args, **kwargs) -> None:
        pass

    def error(self, *args, **kwargs) -> None:
        pass

    def exception(self, *args, **kwargs) -> None:
        pass

    def debug(self, *args, **kwargs) -> None:
        pass

    def critical(self, *args, **kwargs) -> None:
        pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _snapshot(
    sku_id: uuid.UUID,
    *,
    price: int | None = 5000,
    currency: str = "RUB",
    active: bool = True,
    supplier_type: str = "local",
) -> CatalogSkuSnapshot:
    return CatalogSkuSnapshot(
        sku_id=sku_id,
        product_id=uuid.uuid4(),
        variant_id=uuid.uuid4(),
        product_name="Sneakers",
        variant_label="42",
        supplier_type=supplier_type,
        selling_price_amount=price,
        currency=currency,
        is_active=active,
    )


def _recipient(
    *, identity_id: uuid.UUID, is_archived: bool = False
) -> RecipientLookupResult:
    return RecipientLookupResult(
        recipient_id=uuid.uuid4(),
        identity_id=identity_id,
        full_name_ru="Иван Иванов",
        full_name_lat="Ivan Ivanov",
        phone="+79108897762",
        email="ivan@example.com",
        is_archived=is_archived,
    )


def _passport(
    *, identity_id: uuid.UUID, is_archived: bool = False
) -> PassportLookupResult:
    return PassportLookupResult(
        passport_id=uuid.uuid4(),
        identity_id=identity_id,
        full_name_ru="Иван Иванов",
        full_name_lat="Ivan Ivanov",
        passport_serial="1234",
        passport_number="567890",
        passport_issue_date=date(2015, 5, 22),
        birth_date=date(1990, 1, 1),
        inn="500100732272",
        validation_status="pending",
        is_archived=is_archived,
    )


def _quote(
    *,
    identity_id: uuid.UUID | None,
    amount: int = 30000,
    currency: str = "RUB",
    expires_at: datetime | None = None,
) -> DeliveryQuoteLookupResult:
    return DeliveryQuoteLookupResult(
        quote_id=uuid.uuid4(),
        amount=amount,
        currency=currency,
        expires_at=expires_at,
        identity_id=identity_id,
    )


def _build_handler(
    *,
    sku_snapshots: dict[uuid.UUID, CatalogSkuSnapshot] | None = None,
    recipient: RecipientLookupResult | None = None,
    passport: PassportLookupResult | None = None,
    quote: DeliveryQuoteLookupResult | None = None,
) -> tuple:
    repo = _FakeOrderRepo()
    reader = _FakeSkuReader(sku_snapshots or {})
    recipients = _FakeRecipientLookup(
        {recipient.recipient_id: recipient} if recipient else {}
    )
    passports = _FakePassportLookup(
        {passport.passport_id: passport} if passport else {}
    )
    quotes = _FakeDeliveryQuoteLookup({quote.quote_id: quote} if quote else {})
    payment = _FakePaymentGateway()
    idem = _FakeIdem()
    history = _FakeHistory()
    uow = _FakeUow()
    handler = CreateBuyNowOrderHandler(
        order_repo=repo,  # ty:ignore[invalid-argument-type]
        sku_reader=reader,  # ty:ignore[invalid-argument-type]
        recipient_lookup=recipients,  # ty:ignore[invalid-argument-type]
        passport_lookup=passports,  # ty:ignore[invalid-argument-type]
        delivery_quote_lookup=quotes,  # ty:ignore[invalid-argument-type]
        idempotency_store=idem,  # ty:ignore[invalid-argument-type]
        payment_gateway=payment,  # ty:ignore[invalid-argument-type]
        history_writer=history,  # ty:ignore[invalid-argument-type]
        uow=uow,  # ty:ignore[invalid-argument-type]
        logger=_FakeLogger(),
    )
    return handler, repo, reader, recipients, quotes, payment, idem, history, uow


def _cmd(
    *,
    identity_id: uuid.UUID,
    sku_id: uuid.UUID,
    recipient_id: uuid.UUID,
    quantity: int = 1,
    delivery_quote_id: uuid.UUID | None = None,
    idempotency_key: str = "buy-now-idemp-12345",
) -> CreateBuyNowOrderCommand:
    return CreateBuyNowOrderCommand(
        identity_id=identity_id,
        sku_id=sku_id,
        quantity=quantity,
        recipient_id=recipient_id,
        pickup_point=PickupPointPreference(
            carrier=PickupCarrier.CDEK, point_id="MSK-1"
        ),
        delivery_quote_id=delivery_quote_id,
        idempotency_key=idempotency_key,
    )


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_happy_path_creates_paid_order(monkeypatch) -> None:
    # Default settings.PAYMENT_AUTO_CAPTURE_ON_AUTHORIZE=True → Order
    # is born PAID and auto_captured=True is returned.
    identity_id = uuid.uuid4()
    sku_id = uuid.uuid4()
    recipient = _recipient(identity_id=identity_id)
    handler, repo, reader, _r, _q, payment, _idem, _hist, uow = _build_handler(
        sku_snapshots={sku_id: _snapshot(sku_id, price=5000)},
        recipient=recipient,
    )
    result = await handler.handle(
        _cmd(
            identity_id=identity_id,
            sku_id=sku_id,
            recipient_id=recipient.recipient_id,
            quantity=2,
        )
    )

    assert reader.calls == 1
    assert payment.authorize_calls == 1
    assert len(payment.capture_calls) == 1, "capture under skip-payment short-circuit"
    assert len(repo.orders) == 1
    order = repo.orders[result.order_id]
    assert order.status is OrderStatus.PAID
    assert order.is_walk_in is False
    # BE-6 / ADR-010 §I3 — Buy Now handler stamps creation_source.
    assert order.creation_source is OrderCreationSource.BUY_NOW
    assert order.identity_id == identity_id
    assert order.total_amount == 10000  # 5000 * 2
    assert order.delivery_amount == 0
    assert len(order.items) == 1
    item = order.items[0]
    assert item.sku_id == sku_id
    assert item.quantity == 2
    assert item.unit_price_amount == 5000
    assert result.auto_captured is True
    assert uow.committed is True


@pytest.mark.asyncio
async def test_happy_path_without_auto_capture(monkeypatch) -> None:
    """When PAYMENT_AUTO_CAPTURE_ON_AUTHORIZE is False, Order stays PENDING."""
    from src.bootstrap import config as cfg

    monkeypatch.setattr(cfg.settings, "PAYMENT_AUTO_CAPTURE_ON_AUTHORIZE", False)

    identity_id = uuid.uuid4()
    sku_id = uuid.uuid4()
    recipient = _recipient(identity_id=identity_id)
    handler, repo, _r, _rc, _q, payment, *_ = _build_handler(
        sku_snapshots={sku_id: _snapshot(sku_id, price=5000)},
        recipient=recipient,
    )
    result = await handler.handle(
        _cmd(
            identity_id=identity_id,
            sku_id=sku_id,
            recipient_id=recipient.recipient_id,
        )
    )

    order = repo.orders[result.order_id]
    assert order.status is OrderStatus.PENDING
    assert order.payment_intent_id == payment._intent_id
    assert payment.capture_calls == []
    assert result.auto_captured is False


@pytest.mark.asyncio
async def test_delivery_quote_amount_included_in_total() -> None:
    identity_id = uuid.uuid4()
    sku_id = uuid.uuid4()
    recipient = _recipient(identity_id=identity_id)
    quote = _quote(identity_id=identity_id, amount=30000)
    handler, repo, *_ = _build_handler(
        sku_snapshots={sku_id: _snapshot(sku_id, price=5000)},
        recipient=recipient,
        quote=quote,
    )
    result = await handler.handle(
        _cmd(
            identity_id=identity_id,
            sku_id=sku_id,
            recipient_id=recipient.recipient_id,
            delivery_quote_id=quote.quote_id,
        )
    )
    order = repo.orders[result.order_id]
    assert order.delivery_amount == 30000
    assert order.delivery_quote_id == quote.quote_id
    assert order.total_amount == 5000 + 30000


# ---------------------------------------------------------------------------
# SKU usability
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_missing_sku_returns_422() -> None:
    identity_id = uuid.uuid4()
    sku_id = uuid.uuid4()
    recipient = _recipient(identity_id=identity_id)
    handler, *_ = _build_handler(sku_snapshots={}, recipient=recipient)
    with pytest.raises(UnprocessableEntityError) as exc:
        await handler.handle(
            _cmd(
                identity_id=identity_id,
                sku_id=sku_id,
                recipient_id=recipient.recipient_id,
            )
        )
    assert exc.value.error_code == "BUY_NOW_SKU_NOT_FOUND"
    assert exc.value.details["sku_id"] == str(sku_id)


@pytest.mark.asyncio
async def test_inactive_sku_returns_422() -> None:
    identity_id = uuid.uuid4()
    sku_id = uuid.uuid4()
    recipient = _recipient(identity_id=identity_id)
    handler, *_ = _build_handler(
        sku_snapshots={sku_id: _snapshot(sku_id, active=False)},
        recipient=recipient,
    )
    with pytest.raises(UnprocessableEntityError) as exc:
        await handler.handle(
            _cmd(
                identity_id=identity_id,
                sku_id=sku_id,
                recipient_id=recipient.recipient_id,
            )
        )
    assert exc.value.error_code == "BUY_NOW_SKU_INACTIVE"


@pytest.mark.asyncio
async def test_unpriced_sku_returns_422() -> None:
    identity_id = uuid.uuid4()
    sku_id = uuid.uuid4()
    recipient = _recipient(identity_id=identity_id)
    handler, *_ = _build_handler(
        sku_snapshots={sku_id: _snapshot(sku_id, price=None)},
        recipient=recipient,
    )
    with pytest.raises(UnprocessableEntityError) as exc:
        await handler.handle(
            _cmd(
                identity_id=identity_id,
                sku_id=sku_id,
                recipient_id=recipient.recipient_id,
            )
        )
    assert exc.value.error_code == "BUY_NOW_SKU_UNPRICED"


@pytest.mark.asyncio
async def test_invalid_quantity_rejected_by_domain() -> None:
    """quantity<1 is enforced by Pydantic at HTTP boundary; the direct
    command call falls through to ``Order.create`` which raises
    ``OrderItemQuantityError`` — that is the contract for bypassing the
    schema layer (no defensive duplication in the handler)."""
    from src.modules.order.domain.exceptions import OrderItemQuantityError

    identity_id = uuid.uuid4()
    sku_id = uuid.uuid4()
    recipient = _recipient(identity_id=identity_id)
    handler, *_ = _build_handler(
        sku_snapshots={sku_id: _snapshot(sku_id)}, recipient=recipient
    )
    with pytest.raises(OrderItemQuantityError):
        await handler.handle(
            _cmd(
                identity_id=identity_id,
                sku_id=sku_id,
                recipient_id=recipient.recipient_id,
                quantity=0,
            )
        )


# ---------------------------------------------------------------------------
# Recipient
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_missing_recipient_rejected() -> None:
    identity_id = uuid.uuid4()
    sku_id = uuid.uuid4()
    handler, *_ = _build_handler(
        sku_snapshots={sku_id: _snapshot(sku_id)}, recipient=None
    )
    with pytest.raises(UnprocessableEntityError) as exc:
        await handler.handle(
            _cmd(
                identity_id=identity_id,
                sku_id=sku_id,
                recipient_id=uuid.uuid4(),
            )
        )
    assert exc.value.error_code == "ORDER_RECIPIENT_INVALID"


@pytest.mark.asyncio
async def test_archived_recipient_rejected() -> None:
    identity_id = uuid.uuid4()
    sku_id = uuid.uuid4()
    recipient = _recipient(identity_id=identity_id, is_archived=True)
    handler, *_ = _build_handler(
        sku_snapshots={sku_id: _snapshot(sku_id)}, recipient=recipient
    )
    with pytest.raises(UnprocessableEntityError) as exc:
        await handler.handle(
            _cmd(
                identity_id=identity_id,
                sku_id=sku_id,
                recipient_id=recipient.recipient_id,
            )
        )
    assert exc.value.error_code == "ORDER_RECIPIENT_INVALID"


@pytest.mark.asyncio
async def test_recipient_belonging_to_other_customer_rejected() -> None:
    """CR-2 ownership: customer cannot use another customer's recipient."""
    placing_identity = uuid.uuid4()
    owner_identity = uuid.uuid4()
    sku_id = uuid.uuid4()
    recipient = _recipient(identity_id=owner_identity)  # owned by someone else
    handler, *_ = _build_handler(
        sku_snapshots={sku_id: _snapshot(sku_id)}, recipient=recipient
    )
    with pytest.raises(UnprocessableEntityError) as exc:
        await handler.handle(
            _cmd(
                identity_id=placing_identity,
                sku_id=sku_id,
                recipient_id=recipient.recipient_id,
            )
        )
    assert exc.value.error_code == "ORDER_RECIPIENT_OWNERSHIP_MISMATCH"


# ---------------------------------------------------------------------------
# Delivery quote
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_quote_belonging_to_other_customer_rejected() -> None:
    identity_id = uuid.uuid4()
    other_identity = uuid.uuid4()
    sku_id = uuid.uuid4()
    recipient = _recipient(identity_id=identity_id)
    quote = _quote(identity_id=other_identity)
    handler, *_ = _build_handler(
        sku_snapshots={sku_id: _snapshot(sku_id)},
        recipient=recipient,
        quote=quote,
    )
    with pytest.raises(UnprocessableEntityError) as exc:
        await handler.handle(
            _cmd(
                identity_id=identity_id,
                sku_id=sku_id,
                recipient_id=recipient.recipient_id,
                delivery_quote_id=quote.quote_id,
            )
        )
    assert exc.value.error_code == "ORDER_DELIVERY_QUOTE_OWNERSHIP_MISMATCH"


@pytest.mark.asyncio
async def test_quote_currency_mismatch_rejected() -> None:
    identity_id = uuid.uuid4()
    sku_id = uuid.uuid4()
    recipient = _recipient(identity_id=identity_id)
    # SKU priced in RUB, quote in USD → mismatch
    quote = _quote(identity_id=identity_id, currency="USD")
    handler, *_ = _build_handler(
        sku_snapshots={sku_id: _snapshot(sku_id, currency="RUB")},
        recipient=recipient,
        quote=quote,
    )
    with pytest.raises(ValidationError) as exc:
        await handler.handle(
            _cmd(
                identity_id=identity_id,
                sku_id=sku_id,
                recipient_id=recipient.recipient_id,
                delivery_quote_id=quote.quote_id,
            )
        )
    assert exc.value.error_code == "ORDER_DELIVERY_QUOTE_CURRENCY_MISMATCH"


@pytest.mark.asyncio
async def test_expired_quote_rejected() -> None:
    identity_id = uuid.uuid4()
    sku_id = uuid.uuid4()
    recipient = _recipient(identity_id=identity_id)
    quote = _quote(
        identity_id=identity_id,
        expires_at=datetime.now(UTC) - timedelta(minutes=5),
    )
    handler, *_ = _build_handler(
        sku_snapshots={sku_id: _snapshot(sku_id)},
        recipient=recipient,
        quote=quote,
    )
    with pytest.raises(UnprocessableEntityError) as exc:
        await handler.handle(
            _cmd(
                identity_id=identity_id,
                sku_id=sku_id,
                recipient_id=recipient.recipient_id,
                delivery_quote_id=quote.quote_id,
            )
        )
    assert exc.value.error_code == "ORDER_DELIVERY_QUOTE_EXPIRED"


@pytest.mark.asyncio
async def test_admin_quote_no_identity_passes_ownership_check() -> None:
    """``quote.identity_id is None`` opt-out for legacy/admin quotes."""
    identity_id = uuid.uuid4()
    sku_id = uuid.uuid4()
    recipient = _recipient(identity_id=identity_id)
    quote = _quote(identity_id=None, amount=2000)  # admin-side quote
    handler, repo, *_ = _build_handler(
        sku_snapshots={sku_id: _snapshot(sku_id, price=5000)},
        recipient=recipient,
        quote=quote,
    )
    result = await handler.handle(
        _cmd(
            identity_id=identity_id,
            sku_id=sku_id,
            recipient_id=recipient.recipient_id,
            delivery_quote_id=quote.quote_id,
        )
    )
    order = repo.orders[result.order_id]
    assert order.delivery_amount == 2000


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_idempotency_replay_returns_same_order() -> None:
    identity_id = uuid.uuid4()
    sku_id = uuid.uuid4()
    recipient = _recipient(identity_id=identity_id)
    handler, repo, reader, *_, payment, _idem, _hist, _uow = _build_handler(
        sku_snapshots={sku_id: _snapshot(sku_id, price=5000)},
        recipient=recipient,
    )
    cmd = _cmd(
        identity_id=identity_id,
        sku_id=sku_id,
        recipient_id=recipient.recipient_id,
    )
    first = await handler.handle(cmd)
    second = await handler.handle(cmd)

    assert first.order_id == second.order_id
    # On replay, sku_reader / recipient_lookup must NOT be touched —
    # short-circuit happens at the idempotency-store stage.
    assert reader.calls == 1
    assert len(repo.orders) == 1
    # authorize is called twice — once on first run, once on replay
    # to re-fetch the payment ticket for the front-end.
    assert payment.authorize_calls == 2


@pytest.mark.asyncio
async def test_replay_with_missing_order_raises_conflict() -> None:
    """idem store points at an order_id the repo no longer holds —
    likely an inconsistent reservation row (DB rollback gap) — must
    surface loudly as ``IdempotencyKeyConflictError`` so the customer
    retries with a fresh key instead of getting a 5xx."""
    identity_id = uuid.uuid4()
    sku_id = uuid.uuid4()
    recipient = _recipient(identity_id=identity_id)
    handler, _repo, _reader, *_, _payment, idem, _hist, _uow = _build_handler(
        sku_snapshots={sku_id: _snapshot(sku_id, price=5000)},
        recipient=recipient,
    )
    # Seed the idempotency store with a phantom resource_id that the
    # repo cannot resolve.
    phantom_order_id = uuid.uuid4()
    await idem.attach_result(
        key="phantom-key-12345",
        scope="order.create_buy_now",
        resource_id=phantom_order_id,
    )
    with pytest.raises(IdempotencyKeyConflictError):
        await handler.handle(
            _cmd(
                identity_id=identity_id,
                sku_id=sku_id,
                recipient_id=recipient.recipient_id,
                idempotency_key="phantom-key-12345",
            )
        )


@pytest.mark.asyncio
async def test_replay_with_missing_payment_intent_raises_conflict() -> None:
    """Existing order but ``payment_intent_id is None`` — replay cannot
    re-issue a ticket for an order that never got authorised."""
    identity_id = uuid.uuid4()
    sku_id = uuid.uuid4()
    recipient = _recipient(identity_id=identity_id)
    handler, repo, _reader, *_, _payment, idem, _hist, _uow = _build_handler(
        sku_snapshots={sku_id: _snapshot(sku_id, price=5000)},
        recipient=recipient,
    )
    # First call seeds a real order; manually wipe payment_intent_id
    # to simulate the post-rollback shape.
    first = await handler.handle(
        _cmd(
            identity_id=identity_id,
            sku_id=sku_id,
            recipient_id=recipient.recipient_id,
            idempotency_key="key-first",
        )
    )
    order = repo.orders[first.order_id]
    object.__setattr__(order, "payment_intent_id", None)

    # Reuse the same idempotency key by re-pointing the store at this
    # order_id under a fresh key.
    await idem.attach_result(
        key="replay-key-67890",
        scope="order.create_buy_now",
        resource_id=order.id,
    )
    with pytest.raises(IdempotencyKeyConflictError):
        await handler.handle(
            _cmd(
                identity_id=identity_id,
                sku_id=sku_id,
                recipient_id=recipient.recipient_id,
                idempotency_key="replay-key-67890",
            )
        )


@pytest.mark.asyncio
async def test_two_buy_now_calls_produce_distinct_phantom_cart_ids() -> None:
    """Each Buy Now invocation must mint a fresh phantom ``cart_id`` —
    regression to a hardcoded constant or zero UUID would let analytics
    misclassify the flow and break cart-based aggregations."""
    identity_id = uuid.uuid4()
    sku_id = uuid.uuid4()
    recipient = _recipient(identity_id=identity_id)
    handler, repo, *_ = _build_handler(
        sku_snapshots={sku_id: _snapshot(sku_id, price=5000)},
        recipient=recipient,
    )
    first = await handler.handle(
        _cmd(
            identity_id=identity_id,
            sku_id=sku_id,
            recipient_id=recipient.recipient_id,
            idempotency_key="key-A-12345678",
        )
    )
    second = await handler.handle(
        _cmd(
            identity_id=identity_id,
            sku_id=sku_id,
            recipient_id=recipient.recipient_id,
            idempotency_key="key-B-12345678",
        )
    )
    order_a = repo.orders[first.order_id]
    order_b = repo.orders[second.order_id]
    assert order_a.cart_id != order_b.cart_id
    assert order_a.cart_id != uuid.UUID(int=0)
    assert order_b.cart_id != uuid.UUID(int=0)
