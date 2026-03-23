"""Unit tests for DeleteProductAttributeCommand and DeleteProductAttributeHandler.

Tests cover:
- Command dataclass field storage and immutability
- Handler happy path: PAV found by product+attribute, deleted and committed
- Handler not found: raises ProductAttributeValueNotFoundError, no commit
- UoW is used as async context manager
- Handler calls get_by_product_and_attribute and delete with correct arguments
"""

import uuid
from dataclasses import FrozenInstanceError
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.modules.catalog.application.commands.delete_product_attribute import (
    DeleteProductAttributeCommand,
    DeleteProductAttributeHandler,
)
from src.modules.catalog.domain.entities import ProductAttributeValue
from src.modules.catalog.domain.exceptions import ProductAttributeValueNotFoundError

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


def make_pav(
    product_id: uuid.UUID,
    attribute_id: uuid.UUID,
    attribute_value_id: uuid.UUID | None = None,
    pav_id: uuid.UUID | None = None,
) -> ProductAttributeValue:
    """Build a ProductAttributeValue domain entity for test fixtures."""
    return ProductAttributeValue.create(
        product_id=product_id,
        attribute_id=attribute_id,
        attribute_value_id=attribute_value_id or uuid.uuid4(),
        pav_id=pav_id,
    )


def make_pav_repo(
    get_by_product_and_attribute_return: ProductAttributeValue | None = None,
) -> AsyncMock:
    """Build a mocked IProductAttributeValueRepository.

    Args:
        get_by_product_and_attribute_return: Value to return from
            get_by_product_and_attribute(). None means "not found".

    Returns:
        Configured AsyncMock.
    """
    repo = AsyncMock()
    repo.get_by_product_and_attribute = AsyncMock(
        return_value=get_by_product_and_attribute_return,
    )
    repo.delete = AsyncMock()
    return repo


def make_command(
    product_id: uuid.UUID | None = None,
    attribute_id: uuid.UUID | None = None,
) -> DeleteProductAttributeCommand:
    """Build a minimal valid DeleteProductAttributeCommand."""
    return DeleteProductAttributeCommand(
        product_id=product_id or uuid.uuid4(),
        attribute_id=attribute_id or uuid.uuid4(),
    )


# ---------------------------------------------------------------------------
# DeleteProductAttributeCommand
# ---------------------------------------------------------------------------


class TestDeleteProductAttributeCommand:
    """Structural tests for the DeleteProductAttributeCommand DTO."""

    def test_fields_stored_correctly(self) -> None:
        """Both required fields are stored on the dataclass."""
        product_id = uuid.uuid4()
        attribute_id = uuid.uuid4()
        cmd = DeleteProductAttributeCommand(
            product_id=product_id,
            attribute_id=attribute_id,
        )
        assert cmd.product_id == product_id
        assert cmd.attribute_id == attribute_id

    def test_command_is_frozen(self) -> None:
        """DeleteProductAttributeCommand is a frozen dataclass -- mutation must raise."""
        cmd = make_command()
        with pytest.raises(FrozenInstanceError):
            cmd.product_id = uuid.uuid4()  # type: ignore[misc]


# ---------------------------------------------------------------------------
# DeleteProductAttributeHandler -- happy path
# ---------------------------------------------------------------------------


class TestDeleteProductAttributeHandlerHappyPath:
    """Handler tests when the target PAV is found and deleted."""

    async def test_returns_none(self) -> None:
        """Handler returns None on successful deletion."""
        product_id = uuid.uuid4()
        attribute_id = uuid.uuid4()
        pav = make_pav(product_id=product_id, attribute_id=attribute_id)

        pav_repo = make_pav_repo(get_by_product_and_attribute_return=pav)
        uow = make_uow()
        handler = DeleteProductAttributeHandler(
            pav_repo=pav_repo,
            uow=uow,
        )

        result = await handler.handle(
            make_command(product_id=product_id, attribute_id=attribute_id)
        )

        assert result is None

    async def test_calls_get_by_product_and_attribute(self) -> None:
        """Handler calls pav_repo.get_by_product_and_attribute() with the command IDs."""
        product_id = uuid.uuid4()
        attribute_id = uuid.uuid4()
        pav = make_pav(product_id=product_id, attribute_id=attribute_id)

        pav_repo = make_pav_repo(get_by_product_and_attribute_return=pav)
        uow = make_uow()
        handler = DeleteProductAttributeHandler(
            pav_repo=pav_repo,
            uow=uow,
        )

        await handler.handle(make_command(product_id=product_id, attribute_id=attribute_id))

        pav_repo.get_by_product_and_attribute.assert_awaited_once_with(
            product_id,
            attribute_id,
        )

    async def test_calls_delete_with_correct_pav_id(self) -> None:
        """Handler calls pav_repo.delete() with the id of the matching PAV."""
        product_id = uuid.uuid4()
        attribute_id = uuid.uuid4()
        pav = make_pav(product_id=product_id, attribute_id=attribute_id)

        pav_repo = make_pav_repo(get_by_product_and_attribute_return=pav)
        uow = make_uow()
        handler = DeleteProductAttributeHandler(
            pav_repo=pav_repo,
            uow=uow,
        )

        await handler.handle(make_command(product_id=product_id, attribute_id=attribute_id))

        pav_repo.delete.assert_awaited_once_with(pav.id)

    async def test_calls_uow_commit_once(self) -> None:
        """Handler commits the UoW exactly once on success."""
        product_id = uuid.uuid4()
        attribute_id = uuid.uuid4()
        pav = make_pav(product_id=product_id, attribute_id=attribute_id)

        pav_repo = make_pav_repo(get_by_product_and_attribute_return=pav)
        uow = make_uow()
        handler = DeleteProductAttributeHandler(
            pav_repo=pav_repo,
            uow=uow,
        )

        await handler.handle(make_command(product_id=product_id, attribute_id=attribute_id))

        uow.commit.assert_awaited_once()

    async def test_uow_used_as_context_manager(self) -> None:
        """Handler enters and exits the UoW async context manager."""
        product_id = uuid.uuid4()
        attribute_id = uuid.uuid4()
        pav = make_pav(product_id=product_id, attribute_id=attribute_id)

        pav_repo = make_pav_repo(get_by_product_and_attribute_return=pav)
        uow = make_uow()
        handler = DeleteProductAttributeHandler(
            pav_repo=pav_repo,
            uow=uow,
        )

        await handler.handle(make_command(product_id=product_id, attribute_id=attribute_id))

        uow.__aenter__.assert_awaited_once()
        uow.__aexit__.assert_awaited_once()


# ---------------------------------------------------------------------------
# DeleteProductAttributeHandler -- not found
# ---------------------------------------------------------------------------


class TestDeleteProductAttributeHandlerNotFound:
    """Handler tests when the PAV is not found."""

    async def test_raises_not_found_error_when_no_pav(self) -> None:
        """Handler raises ProductAttributeValueNotFoundError when no matching PAV exists."""
        pav_repo = make_pav_repo(get_by_product_and_attribute_return=None)
        uow = make_uow()
        handler = DeleteProductAttributeHandler(
            pav_repo=pav_repo,
            uow=uow,
        )

        with pytest.raises(ProductAttributeValueNotFoundError):
            await handler.handle(make_command())

    async def test_error_contains_product_id(self) -> None:
        """Raised exception includes the product_id in its details."""
        pav_repo = make_pav_repo(get_by_product_and_attribute_return=None)
        uow = make_uow()
        handler = DeleteProductAttributeHandler(
            pav_repo=pav_repo,
            uow=uow,
        )

        product_id = uuid.uuid4()
        cmd = make_command(product_id=product_id)
        with pytest.raises(ProductAttributeValueNotFoundError) as exc_info:
            await handler.handle(cmd)

        assert exc_info.value.details["product_id"] == str(product_id)

    async def test_delete_not_called_when_not_found(self) -> None:
        """When PAV is not found, pav_repo.delete() must not be called."""
        pav_repo = make_pav_repo(get_by_product_and_attribute_return=None)
        uow = make_uow()
        handler = DeleteProductAttributeHandler(
            pav_repo=pav_repo,
            uow=uow,
        )

        with pytest.raises(ProductAttributeValueNotFoundError):
            await handler.handle(make_command())

        pav_repo.delete.assert_not_awaited()

    async def test_commit_not_called_when_not_found(self) -> None:
        """When PAV is not found, uow.commit must not be called."""
        pav_repo = make_pav_repo(get_by_product_and_attribute_return=None)
        uow = make_uow()
        handler = DeleteProductAttributeHandler(
            pav_repo=pav_repo,
            uow=uow,
        )

        with pytest.raises(ProductAttributeValueNotFoundError):
            await handler.handle(make_command())

        uow.commit.assert_not_awaited()
