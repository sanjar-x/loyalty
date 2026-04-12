"""
Unit tests for Cart command handlers — add_item, remove_item, update_quantity, clear.
"""

import uuid

import pytest

from src.modules.cart.application.commands.add_item import (
    AddItemCommand,
    AddItemHandler,
)
from src.modules.cart.application.commands.clear_cart import (
    ClearCartCommand,
    ClearCartHandler,
)
from src.modules.cart.application.commands.remove_item import (
    RemoveItemCommand,
    RemoveItemHandler,
)
from src.modules.cart.application.commands.update_quantity import (
    UpdateQuantityCommand,
    UpdateQuantityHandler,
)
from src.modules.cart.domain.exceptions import (
    CartItemNotFoundError,
    CartNotFoundError,
    SkuNotAvailableError,
)
from tests.factories.cart_builder import CartBuilder, CartItemBuilder
from tests.factories.sku_mothers import SkuSnapshotMother
from tests.fakes.cart_fakes import (
    CartFakeUnitOfWork,
    FakeCartRepository,
    FakeSkuReadService,
)
from tests.unit.cart.helpers import make_cart_logger

# ---------------------------------------------------------------------------
# AddItemHandler
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAddItemHandler:
    async def test_add_item_creates_cart_for_new_user(self) -> None:
        repo = FakeCartRepository()
        sku_service = FakeSkuReadService()
        snap = SkuSnapshotMother.active()
        sku_service.seed(snap)
        uow = CartFakeUnitOfWork()

        handler = AddItemHandler(repo, sku_service, uow, make_cart_logger())
        result = await handler.handle(
            AddItemCommand(sku_id=snap.sku_id, quantity=2, identity_id=uuid.uuid4())
        )

        assert result.quantity == 2
        assert uow.committed
        cart = await repo.get(result.cart_id)
        assert cart is not None
        assert len(cart.items) == 1

    async def test_add_item_to_existing_cart(self) -> None:
        repo = FakeCartRepository()
        sku_service = FakeSkuReadService()
        snap = SkuSnapshotMother.active()
        sku_service.seed(snap)
        uow = CartFakeUnitOfWork()

        identity_id = uuid.uuid4()
        existing = CartBuilder().with_identity(identity_id).build()
        await repo.add(existing)

        handler = AddItemHandler(repo, sku_service, uow, make_cart_logger())
        result = await handler.handle(
            AddItemCommand(sku_id=snap.sku_id, quantity=1, identity_id=identity_id)
        )
        assert result.cart_id == existing.id

    async def test_add_item_merges_quantity_for_duplicate_sku(self) -> None:
        repo = FakeCartRepository()
        sku_service = FakeSkuReadService()
        snap = SkuSnapshotMother.active()
        sku_service.seed(snap)

        identity_id = uuid.uuid4()
        item = CartItemBuilder().with_sku_id(snap.sku_id).with_quantity(2).build()
        existing = CartBuilder().with_identity(identity_id).with_items(item).build()
        await repo.add(existing)

        handler = AddItemHandler(
            repo, sku_service, CartFakeUnitOfWork(), make_cart_logger()
        )
        result = await handler.handle(
            AddItemCommand(sku_id=snap.sku_id, quantity=3, identity_id=identity_id)
        )
        assert result.quantity == 5

    async def test_add_item_sku_not_found_raises(self) -> None:
        repo = FakeCartRepository()
        sku_service = FakeSkuReadService()
        uow = CartFakeUnitOfWork()

        handler = AddItemHandler(repo, sku_service, uow, make_cart_logger())
        with pytest.raises(SkuNotAvailableError):
            await handler.handle(
                AddItemCommand(
                    sku_id=uuid.uuid4(), quantity=1, identity_id=uuid.uuid4()
                )
            )

    async def test_add_item_inactive_sku_raises(self) -> None:
        repo = FakeCartRepository()
        sku_service = FakeSkuReadService()
        snap = SkuSnapshotMother.inactive()
        sku_service.seed(snap)

        handler = AddItemHandler(
            repo, sku_service, CartFakeUnitOfWork(), make_cart_logger()
        )
        with pytest.raises(SkuNotAvailableError):
            await handler.handle(
                AddItemCommand(sku_id=snap.sku_id, quantity=1, identity_id=uuid.uuid4())
            )

    async def test_add_item_for_guest_cart(self) -> None:
        repo = FakeCartRepository()
        sku_service = FakeSkuReadService()
        snap = SkuSnapshotMother.active()
        sku_service.seed(snap)

        handler = AddItemHandler(
            repo, sku_service, CartFakeUnitOfWork(), make_cart_logger()
        )
        result = await handler.handle(
            AddItemCommand(sku_id=snap.sku_id, quantity=1, anonymous_token="guest-tok")
        )
        cart = await repo.get(result.cart_id)
        assert cart is not None
        assert cart.anonymous_token == "guest-tok"


# ---------------------------------------------------------------------------
# RemoveItemHandler
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRemoveItemHandler:
    async def test_remove_existing_item(self) -> None:
        repo = FakeCartRepository()
        identity_id = uuid.uuid4()
        item = CartItemBuilder().build()
        cart = CartBuilder().with_identity(identity_id).with_items(item).build()
        await repo.add(cart)
        uow = CartFakeUnitOfWork()

        handler = RemoveItemHandler(repo, uow, make_cart_logger())
        await handler.handle(
            RemoveItemCommand(sku_id=item.sku_id, identity_id=identity_id)
        )
        assert uow.committed
        assert len(cart.items) == 0

    async def test_remove_from_missing_cart_raises(self) -> None:
        repo = FakeCartRepository()
        handler = RemoveItemHandler(repo, CartFakeUnitOfWork(), make_cart_logger())
        with pytest.raises(CartNotFoundError):
            await handler.handle(
                RemoveItemCommand(sku_id=uuid.uuid4(), identity_id=uuid.uuid4())
            )

    async def test_remove_nonexistent_item_raises(self) -> None:
        repo = FakeCartRepository()
        identity_id = uuid.uuid4()
        cart = CartBuilder().with_identity(identity_id).build()
        await repo.add(cart)
        handler = RemoveItemHandler(repo, CartFakeUnitOfWork(), make_cart_logger())
        with pytest.raises(CartItemNotFoundError):
            await handler.handle(
                RemoveItemCommand(sku_id=uuid.uuid4(), identity_id=identity_id)
            )


# ---------------------------------------------------------------------------
# UpdateQuantityHandler
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestUpdateQuantityHandler:
    async def test_update_quantity(self) -> None:
        repo = FakeCartRepository()
        identity_id = uuid.uuid4()
        item = CartItemBuilder().with_quantity(1).build()
        cart = CartBuilder().with_identity(identity_id).with_items(item).build()
        await repo.add(cart)

        handler = UpdateQuantityHandler(repo, CartFakeUnitOfWork(), make_cart_logger())
        await handler.handle(
            UpdateQuantityCommand(
                sku_id=item.sku_id, quantity=5, identity_id=identity_id
            )
        )
        assert item.quantity == 5

    async def test_update_to_zero_removes(self) -> None:
        repo = FakeCartRepository()
        identity_id = uuid.uuid4()
        item = CartItemBuilder().build()
        cart = CartBuilder().with_identity(identity_id).with_items(item).build()
        await repo.add(cart)

        handler = UpdateQuantityHandler(repo, CartFakeUnitOfWork(), make_cart_logger())
        await handler.handle(
            UpdateQuantityCommand(
                sku_id=item.sku_id, quantity=0, identity_id=identity_id
            )
        )
        assert len(cart.items) == 0


# ---------------------------------------------------------------------------
# ClearCartHandler
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestClearCartHandler:
    async def test_clear_removes_all(self) -> None:
        repo = FakeCartRepository()
        identity_id = uuid.uuid4()
        items = [CartItemBuilder().build() for _ in range(3)]
        cart = CartBuilder().with_identity(identity_id).with_items(*items).build()
        await repo.add(cart)

        handler = ClearCartHandler(repo, CartFakeUnitOfWork(), make_cart_logger())
        await handler.handle(ClearCartCommand(identity_id=identity_id))
        assert len(cart.items) == 0

    async def test_clear_missing_cart_raises(self) -> None:
        repo = FakeCartRepository()
        handler = ClearCartHandler(repo, CartFakeUnitOfWork(), make_cart_logger())
        with pytest.raises(CartNotFoundError):
            await handler.handle(ClearCartCommand(identity_id=uuid.uuid4()))
