"""Unit tests for DeleteSKUCommand and DeleteSKUHandler.

Tests cover:
- Command dataclass field storage and immutability
- Handler happy path: product found, SKU removed, repo.update + uow.commit called
- Handler raises ProductNotFoundError when product does not exist
- Handler raises SKUNotFoundError when SKU not found in product (domain raises)
- UoW is used as async context manager
- No commit on error paths
"""

import uuid
from dataclasses import FrozenInstanceError
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.modules.catalog.application.commands.delete_sku import (
    DeleteSKUCommand,
    DeleteSKUHandler,
)
from src.modules.catalog.domain.exceptions import (
    ProductNotFoundError,
    SKUNotFoundError,
)

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


def make_product_repo(product: object | None = None) -> AsyncMock:
    """Build a mocked IProductRepository.

    Args:
        product: The value returned by get_with_skus. None simulates not-found.

    Returns:
        Configured AsyncMock.
    """
    repo = AsyncMock()
    repo.get_with_skus = AsyncMock(return_value=product)
    repo.update = AsyncMock()
    return repo


def make_product(sku_ids: list[uuid.UUID] | None = None) -> MagicMock:
    """Build a mocked Product aggregate with optional SKU IDs.

    Args:
        sku_ids: List of SKU UUIDs that the product owns. If None, a single
            random SKU is created.

    Returns:
        MagicMock that behaves like a Product for the handler's purposes.
    """
    product = MagicMock()
    product.id = uuid.uuid4()
    product.remove_sku = MagicMock()
    return product


def make_command(
    product_id: uuid.UUID | None = None,
    sku_id: uuid.UUID | None = None,
) -> DeleteSKUCommand:
    """Build a minimal valid DeleteSKUCommand.

    Args:
        product_id: Product UUID; generates one if None.
        sku_id: SKU UUID; generates one if None.

    Returns:
        A ready-to-use command instance.
    """
    return DeleteSKUCommand(
        product_id=product_id or uuid.uuid4(),
        sku_id=sku_id or uuid.uuid4(),
    )


# ---------------------------------------------------------------------------
# DeleteSKUCommand
# ---------------------------------------------------------------------------


class TestDeleteSKUCommand:
    """Structural tests for the DeleteSKUCommand DTO."""

    def test_required_fields_stored_correctly(self) -> None:
        """Both product_id and sku_id are stored on the dataclass."""
        product_id = uuid.uuid4()
        sku_id = uuid.uuid4()
        cmd = DeleteSKUCommand(product_id=product_id, sku_id=sku_id)
        assert cmd.product_id == product_id
        assert cmd.sku_id == sku_id

    def test_command_is_frozen(self) -> None:
        """DeleteSKUCommand is a frozen dataclass -- mutation must raise."""
        cmd = make_command()
        with pytest.raises(FrozenInstanceError):
            cmd.product_id = uuid.uuid4()  # type: ignore[misc]

    def test_command_sku_id_is_frozen(self) -> None:
        """DeleteSKUCommand sku_id field is also immutable."""
        cmd = make_command()
        with pytest.raises(FrozenInstanceError):
            cmd.sku_id = uuid.uuid4()  # type: ignore[misc]


# ---------------------------------------------------------------------------
# DeleteSKUHandler -- happy path
# ---------------------------------------------------------------------------


class TestDeleteSKUHandlerHappyPath:
    """Handler tests when product and SKU both exist."""

    async def test_calls_get_with_skus_with_product_id(self) -> None:
        """Handler calls get_with_skus exactly once with the command's product_id."""
        product_id = uuid.uuid4()
        product = make_product()
        repo = make_product_repo(product=product)
        uow = make_uow()
        handler = DeleteSKUHandler(product_repo=repo, uow=uow)

        cmd = make_command(product_id=product_id)
        await handler.handle(cmd)

        repo.get_with_skus.assert_awaited_once_with(product_id)

    async def test_calls_remove_sku_with_sku_id(self) -> None:
        """Handler delegates soft-delete to product.remove_sku with the command's sku_id."""
        sku_id = uuid.uuid4()
        product = make_product()
        repo = make_product_repo(product=product)
        uow = make_uow()
        handler = DeleteSKUHandler(product_repo=repo, uow=uow)

        cmd = make_command(sku_id=sku_id)
        await handler.handle(cmd)

        product.remove_sku.assert_called_once_with(sku_id)

    async def test_calls_repo_update_with_product(self) -> None:
        """Handler calls repo.update exactly once with the product aggregate."""
        product = make_product()
        repo = make_product_repo(product=product)
        uow = make_uow()
        handler = DeleteSKUHandler(product_repo=repo, uow=uow)

        await handler.handle(make_command())

        repo.update.assert_awaited_once_with(product)

    async def test_calls_uow_commit_once(self) -> None:
        """Handler commits the UoW exactly once on success."""
        product = make_product()
        repo = make_product_repo(product=product)
        uow = make_uow()
        handler = DeleteSKUHandler(product_repo=repo, uow=uow)

        await handler.handle(make_command())

        uow.commit.assert_awaited_once()

    async def test_returns_none(self) -> None:
        """Handler returns None (void command)."""
        product = make_product()
        repo = make_product_repo(product=product)
        uow = make_uow()
        handler = DeleteSKUHandler(product_repo=repo, uow=uow)

        result = await handler.handle(make_command())

        assert result is None

    async def test_uow_used_as_context_manager(self) -> None:
        """Handler enters and exits the UoW async context manager."""
        product = make_product()
        repo = make_product_repo(product=product)
        uow = make_uow()
        handler = DeleteSKUHandler(product_repo=repo, uow=uow)

        await handler.handle(make_command())

        uow.__aenter__.assert_awaited_once()
        uow.__aexit__.assert_awaited_once()

    async def test_update_called_before_commit(self) -> None:
        """repo.update must be called before uow.commit (order matters)."""
        call_order: list[str] = []
        product = make_product()

        repo = AsyncMock()
        repo.get_with_skus = AsyncMock(return_value=product)
        repo.update = AsyncMock(side_effect=lambda *_: call_order.append("update"))

        uow = make_uow()
        uow.commit = AsyncMock(side_effect=lambda: call_order.append("commit"))

        handler = DeleteSKUHandler(product_repo=repo, uow=uow)
        await handler.handle(make_command())

        assert call_order == ["update", "commit"]


# ---------------------------------------------------------------------------
# DeleteSKUHandler -- product not found
# ---------------------------------------------------------------------------


class TestDeleteSKUHandlerProductNotFound:
    """Handler tests when the product does not exist."""

    async def test_raises_product_not_found_error(self) -> None:
        """Handler raises ProductNotFoundError when get_with_skus returns None."""
        repo = make_product_repo(product=None)
        uow = make_uow()
        handler = DeleteSKUHandler(product_repo=repo, uow=uow)

        with pytest.raises(ProductNotFoundError):
            await handler.handle(make_command())

    async def test_error_contains_product_id(self) -> None:
        """Raised exception details include the product_id."""
        product_id = uuid.uuid4()
        repo = make_product_repo(product=None)
        uow = make_uow()
        handler = DeleteSKUHandler(product_repo=repo, uow=uow)

        with pytest.raises(ProductNotFoundError) as exc_info:
            await handler.handle(make_command(product_id=product_id))

        assert str(product_id) in str(exc_info.value)

    async def test_repo_update_not_called(self) -> None:
        """When product not found, repo.update must not be called."""
        repo = make_product_repo(product=None)
        uow = make_uow()
        handler = DeleteSKUHandler(product_repo=repo, uow=uow)

        with pytest.raises(ProductNotFoundError):
            await handler.handle(make_command())

        repo.update.assert_not_awaited()

    async def test_commit_not_called(self) -> None:
        """When product not found, uow.commit must not be called."""
        repo = make_product_repo(product=None)
        uow = make_uow()
        handler = DeleteSKUHandler(product_repo=repo, uow=uow)

        with pytest.raises(ProductNotFoundError):
            await handler.handle(make_command())

        uow.commit.assert_not_awaited()


# ---------------------------------------------------------------------------
# DeleteSKUHandler -- SKU not found in product
# ---------------------------------------------------------------------------


class TestDeleteSKUHandlerSKUNotFound:
    """Handler tests when the SKU does not exist within the product."""

    async def test_raises_sku_not_found_error(self) -> None:
        """Handler propagates SKUNotFoundError raised by product.remove_sku."""
        sku_id = uuid.uuid4()
        product = make_product()
        product.remove_sku.side_effect = SKUNotFoundError(sku_id=sku_id)

        repo = make_product_repo(product=product)
        uow = make_uow()
        handler = DeleteSKUHandler(product_repo=repo, uow=uow)

        with pytest.raises(SKUNotFoundError):
            await handler.handle(make_command(sku_id=sku_id))

    async def test_error_contains_sku_id(self) -> None:
        """Raised SKUNotFoundError contains the sku_id in its message."""
        sku_id = uuid.uuid4()
        product = make_product()
        product.remove_sku.side_effect = SKUNotFoundError(sku_id=sku_id)

        repo = make_product_repo(product=product)
        uow = make_uow()
        handler = DeleteSKUHandler(product_repo=repo, uow=uow)

        with pytest.raises(SKUNotFoundError) as exc_info:
            await handler.handle(make_command(sku_id=sku_id))

        assert str(sku_id) in str(exc_info.value)

    async def test_repo_update_not_called_when_sku_missing(self) -> None:
        """When SKU not found, repo.update must not be called."""
        product = make_product()
        product.remove_sku.side_effect = SKUNotFoundError(sku_id=uuid.uuid4())

        repo = make_product_repo(product=product)
        uow = make_uow()
        handler = DeleteSKUHandler(product_repo=repo, uow=uow)

        with pytest.raises(SKUNotFoundError):
            await handler.handle(make_command())

        repo.update.assert_not_awaited()

    async def test_commit_not_called_when_sku_missing(self) -> None:
        """When SKU not found, uow.commit must not be called."""
        product = make_product()
        product.remove_sku.side_effect = SKUNotFoundError(sku_id=uuid.uuid4())

        repo = make_product_repo(product=product)
        uow = make_uow()
        handler = DeleteSKUHandler(product_repo=repo, uow=uow)

        with pytest.raises(SKUNotFoundError):
            await handler.handle(make_command())

        uow.commit.assert_not_awaited()
