"""
Unit tests for checkout command handlers — initiate, confirm, cancel.
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from src.modules.cart.application.commands.cancel_checkout import (
    CancelCheckoutCommand,
    CancelCheckoutHandler,
)
from src.modules.cart.application.commands.confirm_checkout import (
    ConfirmCheckoutCommand,
    ConfirmCheckoutHandler,
)
from src.modules.cart.application.commands.initiate_checkout import (
    InitiateCheckoutCommand,
    InitiateCheckoutHandler,
)
from src.modules.cart.domain.exceptions import (
    CartEmptyError,
    CartNotFoundError,
    CheckoutPriceChangedError,
    CheckoutSnapshotExpiredError,
    DuplicateCheckoutAttemptError,
    SkuNotAvailableError,
)
from src.modules.cart.domain.value_objects import CartStatus
from tests.factories.cart_builder import CartBuilder, CartItemBuilder
from tests.factories.sku_mothers import SkuSnapshotMother
from tests.fakes.cart_fakes import (
    CartFakeUnitOfWork,
    FakeCartRepository,
    FakePickupPointReadService,
    FakeSkuReadService,
)
from tests.unit.cart.helpers import make_cart_logger

# ---------------------------------------------------------------------------
# InitiateCheckoutHandler
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestInitiateCheckoutHandler:
    async def test_happy_path(self) -> None:
        repo = FakeCartRepository()
        sku_service = FakeSkuReadService()
        snap = SkuSnapshotMother.active(price_amount=5000)
        sku_service.seed(snap)

        identity_id = uuid.uuid4()
        item = CartItemBuilder().with_sku_id(snap.sku_id).with_quantity(2).build()
        cart = CartBuilder().with_identity(identity_id).with_items(item).build()
        await repo.add(cart)

        handler = InitiateCheckoutHandler(
            repo,
            sku_service,
            FakePickupPointReadService(),
            CartFakeUnitOfWork(),
            make_cart_logger(),
        )
        result = await handler.handle(
            InitiateCheckoutCommand(
                identity_id=identity_id, pickup_point_id=uuid.uuid4()
            )
        )

        assert result.total_amount == 10000
        assert cart.status == CartStatus.FROZEN
        assert result.snapshot_id is not None

    async def test_empty_cart_raises(self) -> None:
        repo = FakeCartRepository()
        identity_id = uuid.uuid4()
        cart = CartBuilder().with_identity(identity_id).build()
        await repo.add(cart)

        handler = InitiateCheckoutHandler(
            repo,
            FakeSkuReadService(),
            FakePickupPointReadService(),
            CartFakeUnitOfWork(),
            make_cart_logger(),
        )
        with pytest.raises(CartEmptyError):
            await handler.handle(
                InitiateCheckoutCommand(
                    identity_id=identity_id, pickup_point_id=uuid.uuid4()
                )
            )

    async def test_missing_cart_raises(self) -> None:
        handler = InitiateCheckoutHandler(
            FakeCartRepository(),
            FakeSkuReadService(),
            FakePickupPointReadService(),
            CartFakeUnitOfWork(),
            make_cart_logger(),
        )
        with pytest.raises(CartNotFoundError):
            await handler.handle(
                InitiateCheckoutCommand(
                    identity_id=uuid.uuid4(), pickup_point_id=uuid.uuid4()
                )
            )

    async def test_duplicate_attempt_raises(self) -> None:
        repo = FakeCartRepository()
        sku_service = FakeSkuReadService()
        snap = SkuSnapshotMother.active()
        sku_service.seed(snap)

        identity_id = uuid.uuid4()
        item = CartItemBuilder().with_sku_id(snap.sku_id).build()
        cart = CartBuilder().with_identity(identity_id).with_items(item).build()
        await repo.add(cart)

        # Create a pending attempt
        await repo.create_checkout_attempt(
            attempt_id=uuid.uuid4(), cart_id=cart.id, snapshot_id=uuid.uuid4()
        )

        handler = InitiateCheckoutHandler(
            repo,
            sku_service,
            FakePickupPointReadService(),
            CartFakeUnitOfWork(),
            make_cart_logger(),
        )
        with pytest.raises(DuplicateCheckoutAttemptError):
            await handler.handle(
                InitiateCheckoutCommand(
                    identity_id=identity_id, pickup_point_id=uuid.uuid4()
                )
            )

    async def test_inactive_sku_raises(self) -> None:
        repo = FakeCartRepository()
        sku_service = FakeSkuReadService()
        snap = SkuSnapshotMother.inactive()
        sku_service.seed(snap)

        identity_id = uuid.uuid4()
        item = CartItemBuilder().with_sku_id(snap.sku_id).build()
        cart = CartBuilder().with_identity(identity_id).with_items(item).build()
        await repo.add(cart)

        handler = InitiateCheckoutHandler(
            repo,
            sku_service,
            FakePickupPointReadService(),
            CartFakeUnitOfWork(),
            make_cart_logger(),
        )
        with pytest.raises(SkuNotAvailableError):
            await handler.handle(
                InitiateCheckoutCommand(
                    identity_id=identity_id, pickup_point_id=uuid.uuid4()
                )
            )


# ---------------------------------------------------------------------------
# ConfirmCheckoutHandler
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestConfirmCheckoutHandler:
    async def _setup_checkout(self):
        """Helper: creates a cart with one item and initiates checkout."""
        repo = FakeCartRepository()
        sku_service = FakeSkuReadService()
        snap = SkuSnapshotMother.active(price_amount=5000)
        sku_service.seed(snap)

        identity_id = uuid.uuid4()
        item = CartItemBuilder().with_sku_id(snap.sku_id).with_quantity(2).build()
        cart = CartBuilder().with_identity(identity_id).with_items(item).build()
        await repo.add(cart)

        initiate_handler = InitiateCheckoutHandler(
            repo,
            sku_service,
            FakePickupPointReadService(),
            CartFakeUnitOfWork(),
            make_cart_logger(),
        )
        result = await initiate_handler.handle(
            InitiateCheckoutCommand(
                identity_id=identity_id, pickup_point_id=uuid.uuid4()
            )
        )
        return repo, sku_service, cart, result

    async def test_confirm_happy_path(self) -> None:
        repo, sku_service, cart, initiate_result = await self._setup_checkout()

        handler = ConfirmCheckoutHandler(
            repo, sku_service, CartFakeUnitOfWork(), make_cart_logger()
        )
        result = await handler.handle(
            ConfirmCheckoutCommand(
                identity_id=cart.identity_id, attempt_id=initiate_result.attempt_id
            )
        )
        assert cart.status == CartStatus.ORDERED
        assert result.total_amount == 10000

    async def test_confirm_expired_snapshot_unfreezes(self) -> None:
        repo, sku_service, cart, initiate_result = await self._setup_checkout()

        # Expire the snapshot by replacing it
        snapshot = await repo.get_checkout_snapshot(initiate_result.snapshot_id)
        from src.modules.cart.domain.value_objects import CheckoutSnapshot

        expired = CheckoutSnapshot(
            id=snapshot.id,
            cart_id=snapshot.cart_id,
            items=snapshot.items,
            pickup_point_id=snapshot.pickup_point_id,
            total_amount=snapshot.total_amount,
            currency=snapshot.currency,
            created_at=snapshot.created_at,
            expires_at=datetime.now(UTC) - timedelta(minutes=1),
        )
        repo._snapshots[snapshot.id] = expired

        handler = ConfirmCheckoutHandler(
            repo, sku_service, CartFakeUnitOfWork(), make_cart_logger()
        )
        with pytest.raises(CheckoutSnapshotExpiredError):
            await handler.handle(
                ConfirmCheckoutCommand(
                    identity_id=cart.identity_id, attempt_id=initiate_result.attempt_id
                )
            )
        assert cart.status == CartStatus.ACTIVE

    async def test_confirm_price_up_unfreezes(self) -> None:
        repo, sku_service, cart, initiate_result = await self._setup_checkout()

        # Increase price
        sku_id = cart.items[0].sku_id
        old_snap = sku_service._store[sku_id]
        from src.modules.cart.domain.value_objects import SkuSnapshot

        sku_service._store[sku_id] = SkuSnapshot(
            sku_id=old_snap.sku_id,
            product_id=old_snap.product_id,
            variant_id=old_snap.variant_id,
            product_name=old_snap.product_name,
            variant_label=old_snap.variant_label,
            image_url=old_snap.image_url,
            price_amount=old_snap.price_amount + 1000,
            currency=old_snap.currency,
            supplier_type=old_snap.supplier_type,
            is_active=True,
        )

        handler = ConfirmCheckoutHandler(
            repo, sku_service, CartFakeUnitOfWork(), make_cart_logger()
        )
        with pytest.raises(CheckoutPriceChangedError):
            await handler.handle(
                ConfirmCheckoutCommand(
                    identity_id=cart.identity_id, attempt_id=initiate_result.attempt_id
                )
            )
        assert cart.status == CartStatus.ACTIVE

    async def test_confirm_price_down_succeeds_silently(self) -> None:
        repo, sku_service, cart, initiate_result = await self._setup_checkout()

        # Decrease price
        sku_id = cart.items[0].sku_id
        old_snap = sku_service._store[sku_id]
        from src.modules.cart.domain.value_objects import SkuSnapshot

        sku_service._store[sku_id] = SkuSnapshot(
            sku_id=old_snap.sku_id,
            product_id=old_snap.product_id,
            variant_id=old_snap.variant_id,
            product_name=old_snap.product_name,
            variant_label=old_snap.variant_label,
            image_url=old_snap.image_url,
            price_amount=old_snap.price_amount - 1000,
            currency=old_snap.currency,
            supplier_type=old_snap.supplier_type,
            is_active=True,
        )

        handler = ConfirmCheckoutHandler(
            repo, sku_service, CartFakeUnitOfWork(), make_cart_logger()
        )
        result = await handler.handle(
            ConfirmCheckoutCommand(
                identity_id=cart.identity_id, attempt_id=initiate_result.attempt_id
            )
        )
        assert cart.status == CartStatus.ORDERED
        assert result.total_amount == 8000  # (5000-1000) * 2

    async def test_confirm_price_down_persists_updated_snapshot(self) -> None:
        repo, sku_service, cart, initiate_result = await self._setup_checkout()

        sku_id = cart.items[0].sku_id
        old_snap = sku_service._store[sku_id]
        from src.modules.cart.domain.value_objects import SkuSnapshot

        sku_service._store[sku_id] = SkuSnapshot(
            sku_id=old_snap.sku_id,
            product_id=old_snap.product_id,
            variant_id=old_snap.variant_id,
            product_name=old_snap.product_name,
            variant_label=old_snap.variant_label,
            image_url=old_snap.image_url,
            price_amount=3000,
            currency=old_snap.currency,
            supplier_type=old_snap.supplier_type,
            is_active=True,
        )

        handler = ConfirmCheckoutHandler(
            repo, sku_service, CartFakeUnitOfWork(), make_cart_logger()
        )
        await handler.handle(
            ConfirmCheckoutCommand(
                identity_id=cart.identity_id, attempt_id=initiate_result.attempt_id
            )
        )

        # Verify snapshot was updated with new prices
        updated_snapshot = await repo.get_checkout_snapshot(initiate_result.snapshot_id)
        assert updated_snapshot is not None
        assert updated_snapshot.total_amount == 6000  # 3000 * 2
        assert updated_snapshot.items[0].unit_price_amount == 3000


# ---------------------------------------------------------------------------
# CancelCheckoutHandler
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCancelCheckoutHandler:
    async def test_cancel_unfreezes_cart(self) -> None:
        repo = FakeCartRepository()
        sku_service = FakeSkuReadService()
        snap = SkuSnapshotMother.active()
        sku_service.seed(snap)

        identity_id = uuid.uuid4()
        item = CartItemBuilder().with_sku_id(snap.sku_id).build()
        cart = CartBuilder().with_identity(identity_id).with_items(item).build()
        await repo.add(cart)

        initiate_handler = InitiateCheckoutHandler(
            repo,
            sku_service,
            FakePickupPointReadService(),
            CartFakeUnitOfWork(),
            make_cart_logger(),
        )
        await initiate_handler.handle(
            InitiateCheckoutCommand(
                identity_id=identity_id, pickup_point_id=uuid.uuid4()
            )
        )

        handler = CancelCheckoutHandler(repo, CartFakeUnitOfWork(), make_cart_logger())
        await handler.handle(CancelCheckoutCommand(identity_id=identity_id))
        assert cart.status == CartStatus.ACTIVE
