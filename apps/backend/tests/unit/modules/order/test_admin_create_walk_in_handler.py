"""Unit tests for ``AdminCreateWalkInOrderHandler`` (no DB; fake ports).

Covers:
* happy-path flow (identity provisioned, order created in PAID, no
  payment intent, override audit emitted only when overrides applied);
* idempotency replay (second call returns the same order_id without
  touching catalog / provisioner / repo);
* price-override validation (above-ratio, negative);
* SKU usability checks (missing / inactive / unpriced / currency
  mismatch all aggregate into one 422).
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any

import pytest

from src.modules.order.application.commands.admin_create_walk_in_order import (
    AdminCreateWalkInOrderCommand,
    AdminCreateWalkInOrderHandler,
    InlineRecipientInput,
    OfflinePaymentInput,
    WalkInItemInput,
)
from src.modules.order.application.ports import (
    CatalogSkuSnapshot,
    PriceOverrideAuditEntry,
    WalkInCustomerProfileInput,
    WalkInIdentityProvisioned,
)
from src.modules.order.domain.entities import Order
from src.modules.order.domain.exceptions import (
    OrderEmptyError,
    PriceOverrideValidationError,
)
from src.modules.order.domain.value_objects import (
    OfflinePaymentMethod,
    OrderStatus,
    PickupCarrier,
    PickupPointPreference,
)
from src.shared.exceptions import UnprocessableEntityError

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


class _FakeSkuReader:
    def __init__(self, snapshots: dict[uuid.UUID, CatalogSkuSnapshot]) -> None:
        self._snapshots = snapshots
        self.calls = 0

    async def get_many(
        self, sku_ids: Any, *, locale: str = "ru"
    ) -> dict[uuid.UUID, CatalogSkuSnapshot]:
        self.calls += 1
        return {sid: self._snapshots[sid] for sid in sku_ids if sid in self._snapshots}


class _FakeProvisioner:
    def __init__(self) -> None:
        self.calls = 0
        self.last_profile: WalkInCustomerProfileInput | None = None

    async def provision(
        self, profile: WalkInCustomerProfileInput
    ) -> WalkInIdentityProvisioned:
        self.calls += 1
        self.last_profile = profile
        return WalkInIdentityProvisioned(identity_id=uuid.uuid4())


class _FakeAuditWriter:
    def __init__(self) -> None:
        self.entries: list[PriceOverrideAuditEntry] = []

    async def write_many(self, entries: Any) -> None:
        self.entries.extend(entries)


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
        self.external_events: list[dict[str, Any]] = []

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
        self.external_events.append(kwargs)


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
    price: int = 5000,
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


def _recipient() -> InlineRecipientInput:
    return InlineRecipientInput(
        full_name_ru="Иван Иванов",
        full_name_lat="Ivan Ivanov",
        phone="+79108897762",
        email="ivan@example.com",
        passport_serial="1234",
        passport_number="567890",
        passport_issue_date=date(2015, 5, 22),
        birth_date=date(1990, 1, 1),
        inn="500100732272",
    )


def _profile() -> WalkInCustomerProfileInput:
    return WalkInCustomerProfileInput(
        full_name="Иван Иванов",
        phone="+79108897762",
        email="ivan@example.com",
    )


def _payment() -> OfflinePaymentInput:
    return OfflinePaymentInput(
        method=OfflinePaymentMethod.CASH,
        reference="POS-100",
        paid_at=datetime.now(UTC),
    )


def _build_handler(snapshots: dict[uuid.UUID, CatalogSkuSnapshot]) -> tuple:
    repo = _FakeOrderRepo()
    reader = _FakeSkuReader(snapshots)
    provisioner = _FakeProvisioner()
    audit = _FakeAuditWriter()
    idem = _FakeIdem()
    history = _FakeHistory()
    uow = _FakeUow()
    handler = AdminCreateWalkInOrderHandler(
        order_repo=repo,  # ty:ignore[invalid-argument-type]
        sku_reader=reader,  # ty:ignore[invalid-argument-type]
        identity_provisioner=provisioner,  # ty:ignore[invalid-argument-type]
        override_writer=audit,  # ty:ignore[invalid-argument-type]
        idempotency_store=idem,  # ty:ignore[invalid-argument-type]
        history_writer=history,  # ty:ignore[invalid-argument-type]
        uow=uow,  # ty:ignore[invalid-argument-type]
        logger=_FakeLogger(),
    )
    return handler, repo, reader, provisioner, audit, idem, history, uow


def _cmd(
    *,
    items: tuple[WalkInItemInput, ...],
    idempotency_key: str = "idemp-12345678",
) -> AdminCreateWalkInOrderCommand:
    return AdminCreateWalkInOrderCommand(
        admin_id=uuid.uuid4(),
        profile=_profile(),
        recipient=_recipient(),
        items=items,
        pickup_point=PickupPointPreference(
            carrier=PickupCarrier.CDEK, point_id="MSK-1"
        ),
        payment=_payment(),
        currency="RUB",
        idempotency_key=idempotency_key,
    )


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_happy_path_no_override() -> None:
    sku = uuid.uuid4()
    handler, repo, reader, provisioner, audit, _idem, _hist, uow = _build_handler(
        {sku: _snapshot(sku, price=5000)}
    )
    result = await handler.handle(
        _cmd(items=(WalkInItemInput(sku_id=sku, quantity=2),))
    )

    assert provisioner.calls == 1
    assert provisioner.last_profile is not None
    assert provisioner.last_profile.full_name == "Иван Иванов"
    assert isinstance(result.identity_id, uuid.UUID)
    assert reader.calls == 1
    assert len(repo.orders) == 1
    order = repo.orders[result.order_id]
    assert order.is_walk_in is True
    assert order.status is OrderStatus.PAID
    assert order.payment_intent_id is None
    assert order.total_amount == 10000
    assert audit.entries == []  # no override
    assert uow.committed is True


@pytest.mark.asyncio
async def test_empty_items_rejected() -> None:
    handler, *_ = _build_handler({})
    with pytest.raises(OrderEmptyError):
        await handler.handle(_cmd(items=()))


# ---------------------------------------------------------------------------
# Idempotency replay
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_idempotency_replay_returns_same_order() -> None:
    sku = uuid.uuid4()
    handler, repo, reader, provisioner, _audit, _idem, _hist, _uow = _build_handler(
        {sku: _snapshot(sku, price=2500)}
    )
    cmd = _cmd(items=(WalkInItemInput(sku_id=sku, quantity=1),))

    first = await handler.handle(cmd)
    second = await handler.handle(cmd)

    assert first.order_id == second.order_id
    assert provisioner.calls == 1, "second call must not re-provision identity"
    assert reader.calls == 1, "second call must not re-read catalog"
    assert len(repo.orders) == 1


# ---------------------------------------------------------------------------
# Price overrides
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_price_override_within_bounds_audited() -> None:
    sku = uuid.uuid4()
    handler, repo, _reader, _prov, audit, *_ = _build_handler(
        {sku: _snapshot(sku, price=1000)}
    )
    result = await handler.handle(
        _cmd(
            items=(
                WalkInItemInput(
                    sku_id=sku,
                    quantity=1,
                    unit_price_override_amount=2500,
                    override_reason="Customs surcharge",
                ),
            )
        )
    )
    assert len(audit.entries) == 1
    entry = audit.entries[0]
    assert entry.base_price_amount == 1000
    assert entry.override_price_amount == 2500
    assert entry.reason == "Customs surcharge"
    order = repo.orders[result.order_id]
    assert order.total_amount == 2500
    assert order.items[0].unit_price_amount == 2500


@pytest.mark.asyncio
async def test_price_override_above_max_ratio_rejected() -> None:
    sku = uuid.uuid4()
    # default max_ratio=10 → 1000 * 10 = 10000 ceiling
    handler, *_ = _build_handler({sku: _snapshot(sku, price=1000)})
    with pytest.raises(PriceOverrideValidationError):
        await handler.handle(
            _cmd(
                items=(
                    WalkInItemInput(
                        sku_id=sku,
                        quantity=1,
                        unit_price_override_amount=10_001,
                    ),
                )
            )
        )


@pytest.mark.asyncio
async def test_negative_override_rejected() -> None:
    sku = uuid.uuid4()
    handler, *_ = _build_handler({sku: _snapshot(sku, price=1000)})
    with pytest.raises(PriceOverrideValidationError):
        await handler.handle(
            _cmd(
                items=(
                    WalkInItemInput(
                        sku_id=sku, quantity=1, unit_price_override_amount=-1
                    ),
                )
            )
        )


# ---------------------------------------------------------------------------
# SKU usability checks
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_missing_sku_returns_422() -> None:
    sku = uuid.uuid4()
    handler, *_ = _build_handler({})  # snapshot reader returns nothing
    with pytest.raises(UnprocessableEntityError) as exc:
        await handler.handle(_cmd(items=(WalkInItemInput(sku_id=sku, quantity=1),)))
    assert exc.value.error_code == "WALK_IN_SKU_NOT_USABLE"
    assert str(sku) in exc.value.details["missing"]


@pytest.mark.asyncio
async def test_inactive_sku_returns_422() -> None:
    sku = uuid.uuid4()
    handler, *_ = _build_handler({sku: _snapshot(sku, active=False)})
    with pytest.raises(UnprocessableEntityError) as exc:
        await handler.handle(_cmd(items=(WalkInItemInput(sku_id=sku, quantity=1),)))
    assert str(sku) in exc.value.details["inactive"]


@pytest.mark.asyncio
async def test_unpriced_sku_returns_422() -> None:
    sku = uuid.uuid4()
    snap = _snapshot(sku)
    # Manually wipe selling_price to simulate ADR-005 status=legacy with
    # no recompute yet.
    snap = CatalogSkuSnapshot(
        sku_id=snap.sku_id,
        product_id=snap.product_id,
        variant_id=snap.variant_id,
        product_name=snap.product_name,
        variant_label=snap.variant_label,
        supplier_type=snap.supplier_type,
        selling_price_amount=None,
        currency=snap.currency,
        is_active=True,
    )
    handler, *_ = _build_handler({sku: snap})
    with pytest.raises(UnprocessableEntityError) as exc:
        await handler.handle(_cmd(items=(WalkInItemInput(sku_id=sku, quantity=1),)))
    assert str(sku) in exc.value.details["unpriced"]


@pytest.mark.asyncio
async def test_currency_mismatch_returns_422() -> None:
    sku = uuid.uuid4()
    handler, *_ = _build_handler({sku: _snapshot(sku, currency="USD")})
    with pytest.raises(UnprocessableEntityError) as exc:
        await handler.handle(_cmd(items=(WalkInItemInput(sku_id=sku, quantity=1),)))
    assert str(sku) in exc.value.details["currency_mismatch"]


# Suppress unused-import warnings for symbols kept for type clarity.
_ = (timedelta,)
