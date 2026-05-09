"""Integration tests for the cart freeze-expiry pipeline (D1.1).

Covers the chain on a real PostgreSQL session:

1. ``CartRepository.find_expired_frozen`` filters FROZEN carts whose
   ``frozen_until`` has elapsed and ignores everything else.
2. ``FreezeExpiryCanceller.run`` walks the result, unfreezes each cart
   inside its own UoW, and emits ``CartUnfrozenEvent`` with
   ``reason="freeze_ttl_expired"`` to the outbox.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.outbox import OutboxMessage
from src.infrastructure.database.uow import UnitOfWork
from src.modules.cart.domain.entities import Cart
from src.modules.cart.domain.value_objects import CartStatus
from src.modules.cart.infrastructure.repositories.cart_repository import CartRepository
from src.modules.cart.infrastructure.services.freeze_expiry_canceller import (
    UNFREEZE_REASON,
    FreezeExpiryCanceller,
)

pytestmark = pytest.mark.integration


class _NullLogger:
    def bind(self, **_: Any) -> _NullLogger:
        return self

    def info(self, *_: Any, **__: Any) -> None: ...
    def warning(self, *_: Any, **__: Any) -> None: ...
    def error(self, *_: Any, **__: Any) -> None: ...
    def critical(self, *_: Any, **__: Any) -> None: ...
    def debug(self, *_: Any, **__: Any) -> None: ...
    def exception(self, *_: Any, **__: Any) -> None: ...


async def _seed_cart(
    db_session: AsyncSession, *, status: CartStatus, frozen_until: datetime | None
) -> Cart:
    repo = CartRepository(db_session)
    cart = Cart.create(identity_id=uuid.uuid4())
    cart.clear_domain_events()
    await repo.add(cart)
    if status == CartStatus.FROZEN:
        # Bypass the FSM guard for direct setup — we want the row in
        # FROZEN with a specific frozen_until past timestamp.
        object.__setattr__(cart, "status", CartStatus.FROZEN)
    cart.frozen_until = frozen_until
    await repo.update(cart)
    await db_session.flush()
    return cart


async def test_selector_returns_only_expired_frozen(
    db_session: AsyncSession,
) -> None:
    repo = CartRepository(db_session)
    now = datetime.now(UTC)

    expired = await _seed_cart(
        db_session,
        status=CartStatus.FROZEN,
        frozen_until=now - timedelta(minutes=1),
    )
    fresh = await _seed_cart(
        db_session,
        status=CartStatus.FROZEN,
        frozen_until=now + timedelta(minutes=10),
    )
    active = await _seed_cart(db_session, status=CartStatus.ACTIVE, frozen_until=None)

    ids = await repo.find_expired_frozen(now=now, limit=10)

    assert expired.id in ids
    assert fresh.id not in ids
    assert active.id not in ids


async def test_canceller_unfreezes_and_emits_outbox_event(
    db_session: AsyncSession,
) -> None:
    now = datetime.now(UTC)
    cart = await _seed_cart(
        db_session,
        status=CartStatus.FROZEN,
        frozen_until=now - timedelta(minutes=1),
    )

    repo = CartRepository(db_session)
    canceller = FreezeExpiryCanceller(repo, UnitOfWork(db_session), _NullLogger())

    n = await canceller.run()

    assert n == 1
    refreshed = await repo.get(cart.id)
    assert refreshed is not None
    assert refreshed.status == CartStatus.ACTIVE
    assert refreshed.frozen_until is None

    # CartUnfrozenEvent landed in the outbox with the sentinel reason.
    rows = (
        (
            await db_session.execute(
                select(OutboxMessage).where(
                    OutboxMessage.aggregate_id == str(cart.id),
                    OutboxMessage.event_type == "CartUnfrozenEvent",
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == 1
    assert rows[0].payload["reason"] == UNFREEZE_REASON
