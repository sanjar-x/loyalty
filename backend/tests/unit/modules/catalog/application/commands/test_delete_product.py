"""Unit tests for DeleteProductCommand and DeleteProductHandler.

Tests cover:
- Command dataclass field storage and immutability
- Handler happy path: product found, soft-deleted, updated, committed
- Handler not-found path: raises ProductNotFoundError, no commit
- UoW is used as async context manager
- repo.update is called with the soft-deleted product
"""

import uuid
from dataclasses import FrozenInstanceError
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.modules.catalog.application.commands.delete_product import (
    DeleteProductCommand,
    DeleteProductHandler,
)
from src.modules.catalog.domain.exceptions import ProductNotFoundError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_uow() -> AsyncMock:
    """Build a fully-mocked IUnitOfWork that works as an async context manager."""
    uow = AsyncMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=False)
    uow.commit = AsyncMock()
    uow.register_aggregate = MagicMock()
    return uow


def _make_product(product_id: uuid.UUID | None = None) -> MagicMock:
    """Build a lightweight mock Product with a soft_delete method."""
    product = MagicMock()
    product.id = product_id or uuid.uuid4()
    product.deleted_at = None
    product.soft_delete = MagicMock()
    return product


def make_product_repo(
    product: MagicMock | None = None,
    *,
    returns_none: bool = False,
) -> AsyncMock:
    """Build a mocked IProductRepository.

    Args:
        product: The product to return from get(). Ignored if returns_none.
        returns_none: If True, get() returns None (not found).

    Returns:
        Configured AsyncMock.
    """
    repo = AsyncMock()
    if returns_none:
        repo.get = AsyncMock(return_value=None)
    else:
        repo.get = AsyncMock(return_value=product or _make_product())
    repo.update = AsyncMock()
    return repo


# ---------------------------------------------------------------------------
# DeleteProductCommand
# ---------------------------------------------------------------------------


class TestDeleteProductCommand:
    """Structural tests for the DeleteProductCommand DTO."""

    def test_stores_product_id(self) -> None:
        """product_id is stored as supplied."""
        pid = uuid.uuid4()
        cmd = DeleteProductCommand(product_id=pid)
        assert cmd.product_id == pid

    def test_command_is_frozen(self) -> None:
        """DeleteProductCommand is a frozen dataclass -- mutation must raise."""
        cmd = DeleteProductCommand(product_id=uuid.uuid4())
        with pytest.raises(FrozenInstanceError):
            cmd.product_id = uuid.uuid4()  # type: ignore[misc]


# ---------------------------------------------------------------------------
# DeleteProductHandler -- happy path
# ---------------------------------------------------------------------------


class TestDeleteProductHandlerHappyPath:
    """Handler tests when the product exists."""

    async def test_calls_repo_get_with_correct_id(self) -> None:
        """Handler calls repo.get exactly once with the command's product_id."""
        pid = uuid.uuid4()
        product = _make_product(pid)
        repo = make_product_repo(product=product)
        uow = make_uow()
        handler = DeleteProductHandler(product_repo=repo, uow=uow)

        await handler.handle(DeleteProductCommand(product_id=pid))

        repo.get.assert_awaited_once_with(pid)

    async def test_calls_soft_delete_on_product(self) -> None:
        """Handler calls product.soft_delete() once."""
        product = _make_product()
        repo = make_product_repo(product=product)
        uow = make_uow()
        handler = DeleteProductHandler(product_repo=repo, uow=uow)

        await handler.handle(DeleteProductCommand(product_id=product.id))

        product.soft_delete.assert_called_once()

    async def test_calls_repo_update_with_product(self) -> None:
        """Handler calls repo.update with the soft-deleted product."""
        product = _make_product()
        repo = make_product_repo(product=product)
        uow = make_uow()
        handler = DeleteProductHandler(product_repo=repo, uow=uow)

        await handler.handle(DeleteProductCommand(product_id=product.id))

        repo.update.assert_awaited_once_with(product)

    async def test_calls_uow_commit_once(self) -> None:
        """Handler commits the UoW exactly once on success."""
        product = _make_product()
        repo = make_product_repo(product=product)
        uow = make_uow()
        handler = DeleteProductHandler(product_repo=repo, uow=uow)

        await handler.handle(DeleteProductCommand(product_id=product.id))

        uow.commit.assert_awaited_once()

    async def test_returns_none(self) -> None:
        """Handler returns None (no result DTO for deletes)."""
        product = _make_product()
        repo = make_product_repo(product=product)
        uow = make_uow()
        handler = DeleteProductHandler(product_repo=repo, uow=uow)

        result = await handler.handle(DeleteProductCommand(product_id=product.id))

        assert result is None

    async def test_uow_used_as_context_manager(self) -> None:
        """Handler enters and exits the UoW async context manager."""
        product = _make_product()
        repo = make_product_repo(product=product)
        uow = make_uow()
        handler = DeleteProductHandler(product_repo=repo, uow=uow)

        await handler.handle(DeleteProductCommand(product_id=product.id))

        uow.__aenter__.assert_awaited_once()
        uow.__aexit__.assert_awaited_once()

    async def test_soft_delete_called_before_update(self) -> None:
        """soft_delete() must be called before repo.update() -- ordering check."""
        call_order: list[str] = []
        product = _make_product()
        product.soft_delete = MagicMock(side_effect=lambda: call_order.append("soft_delete"))

        repo = AsyncMock()
        repo.get = AsyncMock(return_value=product)
        repo.update = AsyncMock(side_effect=lambda *_: call_order.append("update"))
        uow = make_uow()
        handler = DeleteProductHandler(product_repo=repo, uow=uow)

        await handler.handle(DeleteProductCommand(product_id=product.id))

        assert call_order == ["soft_delete", "update"]

    async def test_update_called_before_commit(self) -> None:
        """repo.update() must be called before uow.commit() -- ordering check."""
        call_order: list[str] = []

        product = _make_product()
        repo = AsyncMock()
        repo.get = AsyncMock(return_value=product)
        repo.update = AsyncMock(side_effect=lambda *_: call_order.append("update"))
        uow = make_uow()
        uow.commit = AsyncMock(side_effect=lambda: call_order.append("commit"))
        handler = DeleteProductHandler(product_repo=repo, uow=uow)

        await handler.handle(DeleteProductCommand(product_id=product.id))

        assert call_order == ["update", "commit"]


# ---------------------------------------------------------------------------
# DeleteProductHandler -- not found
# ---------------------------------------------------------------------------


class TestDeleteProductHandlerNotFound:
    """Handler tests when the product does not exist."""

    async def test_raises_product_not_found_error(self) -> None:
        """Handler raises ProductNotFoundError when repo.get returns None."""
        repo = make_product_repo(returns_none=True)
        uow = make_uow()
        handler = DeleteProductHandler(product_repo=repo, uow=uow)

        with pytest.raises(ProductNotFoundError):
            await handler.handle(DeleteProductCommand(product_id=uuid.uuid4()))

    async def test_error_contains_product_id(self) -> None:
        """Raised exception details include the missing product_id."""
        pid = uuid.uuid4()
        repo = make_product_repo(returns_none=True)
        uow = make_uow()
        handler = DeleteProductHandler(product_repo=repo, uow=uow)

        with pytest.raises(ProductNotFoundError) as exc_info:
            await handler.handle(DeleteProductCommand(product_id=pid))

        assert str(pid) in str(exc_info.value)

    async def test_repo_update_not_called(self) -> None:
        """When product not found, repo.update must not be called."""
        repo = make_product_repo(returns_none=True)
        uow = make_uow()
        handler = DeleteProductHandler(product_repo=repo, uow=uow)

        with pytest.raises(ProductNotFoundError):
            await handler.handle(DeleteProductCommand(product_id=uuid.uuid4()))

        repo.update.assert_not_awaited()

    async def test_commit_not_called(self) -> None:
        """When product not found, uow.commit must not be called."""
        repo = make_product_repo(returns_none=True)
        uow = make_uow()
        handler = DeleteProductHandler(product_repo=repo, uow=uow)

        with pytest.raises(ProductNotFoundError):
            await handler.handle(DeleteProductCommand(product_id=uuid.uuid4()))

        uow.commit.assert_not_awaited()
