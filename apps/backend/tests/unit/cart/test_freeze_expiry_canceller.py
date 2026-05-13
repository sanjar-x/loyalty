"""Unit tests for ``FreezeExpiryCanceller`` (D1.1)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import pytest

from src.modules.cart.domain.entities import Cart, CartStatus
from src.modules.cart.infrastructure.services.freeze_expiry_canceller import (
    UNFREEZE_REASON,
    FreezeExpiryCanceller,
)
from tests.factories.cart_builder import CartBuilder

pytestmark = pytest.mark.unit


class _FakeRepo:
    def __init__(
        self,
        carts: dict[uuid.UUID, Cart] | None = None,
        expired_ids: list[uuid.UUID] | None = None,
    ) -> None:
        self._carts = carts or {}
        self._expired_ids = expired_ids or []
        self.find_calls: list[tuple[datetime, int]] = []
        self.update_calls: list[uuid.UUID] = []

    async def find_expired_frozen(
        self, *, now: datetime, limit: int = 100
    ) -> list[uuid.UUID]:
        self.find_calls.append((now, limit))
        return list(self._expired_ids)

    async def get_for_update(self, cart_id: uuid.UUID) -> Cart | None:
        return self._carts.get(cart_id)

    async def update(self, cart: Cart) -> Cart:
        self.update_calls.append(cart.id)
        cart.version += 1
        return cart


class _NullLogger:
    def bind(self, **_: Any) -> _NullLogger:
        return self

    def info(self, *_: Any, **__: Any) -> None: ...
    def warning(self, *_: Any, **__: Any) -> None: ...
    def error(self, *_: Any, **__: Any) -> None: ...
    def critical(self, *_: Any, **__: Any) -> None: ...
    def debug(self, *_: Any, **__: Any) -> None: ...
    def exception(self, *_: Any, **__: Any) -> None: ...


class _FakeUow:
    def __init__(self) -> None:
        self.commits = 0
        self.aggregates: list[Any] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_: Any) -> None:
        return None

    async def flush(self) -> None: ...
    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None: ...

    def register_aggregate(self, aggregate: Any) -> None:
        self.aggregates.append(aggregate)

    def enqueue_external_event(self, **_: Any) -> None: ...


def _frozen_cart() -> Cart:
    cart = (
        CartBuilder().with_identity(uuid.uuid4()).with_status(CartStatus.FROZEN).build()
    )
    cart.frozen_until = datetime(2026, 5, 1, 10, tzinfo=UTC)
    cart.clear_domain_events()
    return cart


def _make(
    expired_ids: list[uuid.UUID] | None = None,
    carts: dict[uuid.UUID, Cart] | None = None,
):
    repo = _FakeRepo(carts=carts, expired_ids=expired_ids)
    uow = _FakeUow()
    return (
        FreezeExpiryCanceller(repo, uow, _NullLogger()),  # ty: ignore[invalid-argument-type]
        repo,
        uow,
    )


async def test_empty_batch_returns_zero() -> None:
    canceller, repo, uow = _make(expired_ids=[])
    n = await canceller.run()
    assert n == 0
    assert repo.update_calls == []
    assert uow.commits == 0


async def test_unfreezes_each_expired_cart_with_reason() -> None:
    cart_a = _frozen_cart()
    cart_b = _frozen_cart()
    canceller, repo, uow = _make(
        expired_ids=[cart_a.id, cart_b.id],
        carts={cart_a.id: cart_a, cart_b.id: cart_b},
    )
    n = await canceller.run()
    assert n == 2
    assert sorted(repo.update_calls) == sorted([cart_a.id, cart_b.id])
    assert cart_a.status == CartStatus.ACTIVE
    assert cart_b.status == CartStatus.ACTIVE
    # Reason rides on the CartUnfrozenEvent emitted by the aggregate.
    from src.modules.cart.domain.events import CartUnfrozenEvent

    aggregate_reasons: set[str] = set()
    for agg in uow.aggregates:
        for ev in agg.domain_events:
            if isinstance(ev, CartUnfrozenEvent):
                aggregate_reasons.add(ev.reason)
    assert aggregate_reasons == {UNFREEZE_REASON}


async def test_skips_cart_no_longer_frozen() -> None:
    """Race: selector saw FROZEN but a concurrent unfreeze already
    flipped the cart back to ACTIVE — drop silently, don't error."""
    cart = _frozen_cart()
    cart.unfreeze("cancelled")  # concurrent unfreeze
    canceller, repo, _uow = _make(expired_ids=[cart.id], carts={cart.id: cart})
    n = await canceller.run()
    assert n == 0
    assert repo.update_calls == []


async def test_not_found_does_not_poison_batch() -> None:
    cart = _frozen_cart()
    bogus_id = uuid.uuid4()
    canceller, repo, _uow = _make(
        expired_ids=[bogus_id, cart.id], carts={cart.id: cart}
    )
    n = await canceller.run()
    # First id missing → CartNotFoundError → logged + skipped.
    # Second succeeds.
    assert n == 1
    assert repo.update_calls == [cart.id]
