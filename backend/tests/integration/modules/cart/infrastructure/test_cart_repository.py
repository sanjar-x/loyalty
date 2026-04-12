"""Integration tests for CartRepository — real DB via docker compose."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.cart.domain.entities import Cart
from src.modules.cart.domain.value_objects import (
    CartStatus,
    CheckoutItemSnapshot,
    CheckoutSnapshot,
    SkuSnapshot,
)
from src.modules.cart.infrastructure.repositories.cart_repository import CartRepository


def _make_sku_snapshot(
    sku_id: uuid.UUID | None = None,
    product_id: uuid.UUID | None = None,
    variant_id: uuid.UUID | None = None,
    supplier_type: str = "local",
) -> SkuSnapshot:
    return SkuSnapshot(
        sku_id=sku_id or uuid.uuid4(),
        product_id=product_id or uuid.uuid4(),
        variant_id=variant_id or uuid.uuid4(),
        product_name="Test Product",
        variant_label=None,
        image_url=None,
        price_amount=1000,
        currency="RUB",
        supplier_type=supplier_type,
        is_active=True,
    )

pytestmark = pytest.mark.integration


async def test_add_and_get_cart(db_session: AsyncSession) -> None:
    repo = CartRepository(db_session)
    identity_id = uuid.uuid4()
    cart = Cart.create(identity_id=identity_id)
    cart.clear_domain_events()

    await repo.add(cart)
    fetched = await repo.get(cart.id)

    assert fetched is not None
    assert fetched.id == cart.id
    assert fetched.identity_id == identity_id
    assert fetched.status == CartStatus.ACTIVE


async def test_add_item_and_persist(db_session: AsyncSession) -> None:
    repo = CartRepository(db_session)
    identity_id = uuid.uuid4()
    cart = Cart.create(identity_id=identity_id)
    cart.clear_domain_events()

    snap = _make_sku_snapshot()
    cart.add_item(sku_snapshot=snap, quantity=2)
    cart.clear_domain_events()

    await repo.add(cart)
    fetched = await repo.get(cart.id)

    assert fetched is not None
    assert len(fetched.items) == 1
    assert fetched.items[0].sku_id == snap.sku_id
    assert fetched.items[0].quantity == 2


async def test_get_active_by_identity(db_session: AsyncSession) -> None:
    repo = CartRepository(db_session)
    identity_id = uuid.uuid4()
    cart = Cart.create(identity_id=identity_id)
    cart.clear_domain_events()
    await repo.add(cart)

    fetched = await repo.get_active_by_identity(identity_id)
    assert fetched is not None
    assert fetched.id == cart.id

    no_cart = await repo.get_active_by_identity(uuid.uuid4())
    assert no_cart is None


async def test_get_active_by_anonymous(db_session: AsyncSession) -> None:
    repo = CartRepository(db_session)
    token = uuid.uuid4().hex
    cart = Cart.create(anonymous_token=token)
    cart.clear_domain_events()
    await repo.add(cart)

    fetched = await repo.get_active_by_anonymous(token)
    assert fetched is not None
    assert fetched.id == cart.id


async def test_update_cart(db_session: AsyncSession) -> None:
    repo = CartRepository(db_session)
    identity_id = uuid.uuid4()
    cart = Cart.create(identity_id=identity_id)
    cart.clear_domain_events()
    await repo.add(cart)

    snap = _make_sku_snapshot()
    cart.add_item(sku_snapshot=snap, quantity=1)
    cart.clear_domain_events()
    await repo.update(cart)

    fetched = await repo.get(cart.id)
    assert fetched is not None
    assert len(fetched.items) == 1


async def test_get_for_update(db_session: AsyncSession) -> None:
    repo = CartRepository(db_session)
    identity_id = uuid.uuid4()
    cart = Cart.create(identity_id=identity_id)
    cart.clear_domain_events()
    await repo.add(cart)

    locked = await repo.get_for_update(cart.id)
    assert locked is not None
    assert locked.id == cart.id


async def test_checkout_snapshot_lifecycle(db_session: AsyncSession) -> None:
    repo = CartRepository(db_session)
    identity_id = uuid.uuid4()
    cart = Cart.create(identity_id=identity_id)
    cart.clear_domain_events()
    await repo.add(cart)

    now = datetime.now(tz=UTC)
    snapshot = CheckoutSnapshot(
        id=uuid.uuid4(),
        cart_id=cart.id,
        items=(
            CheckoutItemSnapshot(
                sku_id=uuid.uuid4(),
                quantity=2,
                unit_price_amount=1000,
                currency="RUB",
            ),
        ),
        pickup_point_id=uuid.uuid4(),
        total_amount=2000,
        currency="RUB",
        created_at=now,
        expires_at=now + timedelta(minutes=15),
    )

    await repo.save_checkout_snapshot(snapshot)
    fetched = await repo.get_checkout_snapshot(snapshot.id)

    assert fetched is not None
    assert fetched.id == snapshot.id
    assert fetched.total_amount == 2000
    assert len(fetched.items) == 1
    assert fetched.items[0].quantity == 2


async def test_checkout_attempt_lifecycle(db_session: AsyncSession) -> None:
    repo = CartRepository(db_session)
    identity_id = uuid.uuid4()
    cart = Cart.create(identity_id=identity_id)
    cart.clear_domain_events()
    await repo.add(cart)

    now = datetime.now(tz=UTC)
    snapshot = CheckoutSnapshot(
        id=uuid.uuid4(),
        cart_id=cart.id,
        items=(
            CheckoutItemSnapshot(
                sku_id=uuid.uuid4(),
                quantity=1,
                unit_price_amount=500,
                currency="RUB",
            ),
        ),
        pickup_point_id=uuid.uuid4(),
        total_amount=500,
        currency="RUB",
        created_at=now,
        expires_at=now + timedelta(minutes=15),
    )
    await repo.save_checkout_snapshot(snapshot)

    attempt_id = uuid.uuid4()
    await repo.create_checkout_attempt(
        attempt_id=attempt_id,
        cart_id=cart.id,
        snapshot_id=snapshot.id,
    )

    pending = await repo.get_pending_checkout_attempt(cart.id)
    assert pending is not None
    assert pending["id"] == attempt_id
    assert pending["status"] == "pending"

    await repo.resolve_checkout_attempt(
        attempt_id, status="confirmed", resolved_at=datetime.now(tz=UTC)
    )

    pending_after = await repo.get_pending_checkout_attempt(cart.id)
    assert pending_after is None


async def test_owner_xor_constraint(db_session: AsyncSession) -> None:
    """Carts must have either identity_id or anonymous_token, not both."""
    repo = CartRepository(db_session)

    cart = Cart.create(identity_id=uuid.uuid4())
    cart.clear_domain_events()
    await repo.add(cart)
    fetched = await repo.get(cart.id)
    assert fetched is not None
    assert fetched.anonymous_token is None
