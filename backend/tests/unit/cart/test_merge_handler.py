"""Unit tests for MergeCartsHandler."""

import uuid
from unittest.mock import MagicMock

import pytest

from src.modules.cart.application.commands.merge_carts import (
    MergeCartsCommand,
    MergeCartsHandler,
)
from src.modules.cart.domain.exceptions import CartNotFoundError
from src.modules.cart.domain.value_objects import CartStatus
from tests.factories.cart_builder import CartBuilder, CartItemBuilder
from tests.fakes.cart_fakes import FakeCartRepository
from tests.unit.cart.test_crud_handlers import CartFakeUnitOfWork


def make_logger():
    logger = MagicMock()
    logger.bind = MagicMock(return_value=logger)
    return logger


@pytest.mark.unit
class TestMergeCartsHandler:
    async def test_merge_into_existing_auth_cart(self) -> None:
        repo = FakeCartRepository()
        identity_id = uuid.uuid4()

        target = CartBuilder().with_identity(identity_id).build()
        source_item = CartItemBuilder().build()
        source = CartBuilder().as_guest("guest-tok").with_items(source_item).build()
        await repo.add(target)
        await repo.add(source)

        handler = MergeCartsHandler(repo, CartFakeUnitOfWork(), make_logger())
        result = await handler.handle(
            MergeCartsCommand(identity_id=identity_id, anonymous_token="guest-tok")
        )
        assert result.target_cart_id == target.id
        assert result.items_transferred == 1
        assert source.status == CartStatus.MERGED

    async def test_merge_reassigns_when_no_auth_cart(self) -> None:
        repo = FakeCartRepository()
        identity_id = uuid.uuid4()

        source_item = CartItemBuilder().build()
        source = CartBuilder().as_guest("guest-tok").with_items(source_item).build()
        await repo.add(source)

        handler = MergeCartsHandler(repo, CartFakeUnitOfWork(), make_logger())
        result = await handler.handle(
            MergeCartsCommand(identity_id=identity_id, anonymous_token="guest-tok")
        )
        assert result.target_cart_id == source.id
        assert source.identity_id == identity_id
        assert source.anonymous_token is None

    async def test_merge_no_guest_cart_raises(self) -> None:
        repo = FakeCartRepository()
        handler = MergeCartsHandler(repo, CartFakeUnitOfWork(), make_logger())
        with pytest.raises(CartNotFoundError):
            await handler.handle(
                MergeCartsCommand(identity_id=uuid.uuid4(), anonymous_token="no-such-token")
            )

    async def test_merge_sums_quantities_for_same_sku(self) -> None:
        repo = FakeCartRepository()
        identity_id = uuid.uuid4()
        sku_id = uuid.uuid4()

        target_item = CartItemBuilder().with_sku_id(sku_id).with_quantity(2).build()
        target = CartBuilder().with_identity(identity_id).with_items(target_item).build()

        source_item = CartItemBuilder().with_sku_id(sku_id).with_quantity(3).build()
        source = CartBuilder().as_guest("g").with_items(source_item).build()

        await repo.add(target)
        await repo.add(source)

        handler = MergeCartsHandler(repo, CartFakeUnitOfWork(), make_logger())
        result = await handler.handle(
            MergeCartsCommand(identity_id=identity_id, anonymous_token="g")
        )
        assert result.items_transferred == 1
        assert target_item.quantity == 5
