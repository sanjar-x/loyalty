"""Unit tests for AssignProductAttributeCommand, AssignProductAttributeResult, and AssignProductAttributeHandler.

Tests cover:
- Command dataclass field storage and immutability
- Result dataclass field storage and immutability
- Handler happy path: product exists, no duplicate, PAV created and committed
- Handler product not found: raises ProductNotFoundError, no commit
- Handler duplicate attribute: raises DuplicateProductAttributeError, no commit
- UoW is used as async context manager
"""

import uuid
from dataclasses import FrozenInstanceError
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.modules.catalog.application.commands.assign_product_attribute import (
    AssignProductAttributeCommand,
    AssignProductAttributeHandler,
    AssignProductAttributeResult,
)
from src.modules.catalog.domain.entities import Product, ProductAttributeValue
from src.modules.catalog.domain.exceptions import (
    DuplicateProductAttributeError,
    ProductNotFoundError,
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


def make_product_repo(product_exists: bool = True) -> AsyncMock:
    """Build a mocked IProductRepository.

    Args:
        product_exists: When True, get() returns a mock product; when False, returns None.

    Returns:
        Configured AsyncMock.
    """
    repo = AsyncMock()
    if product_exists:
        product = MagicMock(spec=Product)
        product.id = uuid.uuid4()
        repo.get = AsyncMock(return_value=product)
    else:
        repo.get = AsyncMock(return_value=None)
    return repo


def make_pav_repo(already_exists: bool = False) -> AsyncMock:
    """Build a mocked IProductAttributeValueRepository.

    Args:
        already_exists: Return value for exists() -- True means duplicate.

    Returns:
        Configured AsyncMock.
    """
    repo = AsyncMock()
    repo.exists = AsyncMock(return_value=already_exists)
    repo.add = AsyncMock(side_effect=lambda pav: pav)
    return repo


def make_command(
    product_id: uuid.UUID | None = None,
    attribute_id: uuid.UUID | None = None,
    attribute_value_id: uuid.UUID | None = None,
) -> AssignProductAttributeCommand:
    """Build a minimal valid AssignProductAttributeCommand."""
    return AssignProductAttributeCommand(
        product_id=product_id or uuid.uuid4(),
        attribute_id=attribute_id or uuid.uuid4(),
        attribute_value_id=attribute_value_id or uuid.uuid4(),
    )


# ---------------------------------------------------------------------------
# AssignProductAttributeCommand
# ---------------------------------------------------------------------------


class TestAssignProductAttributeCommand:
    """Structural tests for the AssignProductAttributeCommand DTO."""

    def test_fields_stored_correctly(self) -> None:
        """All three required fields are stored on the dataclass."""
        product_id = uuid.uuid4()
        attribute_id = uuid.uuid4()
        attribute_value_id = uuid.uuid4()
        cmd = AssignProductAttributeCommand(
            product_id=product_id,
            attribute_id=attribute_id,
            attribute_value_id=attribute_value_id,
        )
        assert cmd.product_id == product_id
        assert cmd.attribute_id == attribute_id
        assert cmd.attribute_value_id == attribute_value_id

    def test_command_is_frozen(self) -> None:
        """AssignProductAttributeCommand is a frozen dataclass -- mutation must raise."""
        cmd = make_command()
        with pytest.raises(FrozenInstanceError):
            cmd.product_id = uuid.uuid4()  # type: ignore[misc]


# ---------------------------------------------------------------------------
# AssignProductAttributeResult
# ---------------------------------------------------------------------------


class TestAssignProductAttributeResult:
    """Structural tests for the AssignProductAttributeResult DTO."""

    def test_stores_pav_id(self) -> None:
        """pav_id is stored as supplied."""
        pav_id = uuid.uuid4()
        result = AssignProductAttributeResult(pav_id=pav_id)
        assert result.pav_id == pav_id

    def test_result_is_frozen(self) -> None:
        """AssignProductAttributeResult is a frozen dataclass -- mutation must raise."""
        result = AssignProductAttributeResult(pav_id=uuid.uuid4())
        with pytest.raises(FrozenInstanceError):
            result.pav_id = uuid.uuid4()  # type: ignore[misc]


# ---------------------------------------------------------------------------
# AssignProductAttributeHandler -- happy path
# ---------------------------------------------------------------------------


class TestAssignProductAttributeHandlerHappyPath:
    """Handler tests when product exists and attribute is not yet assigned."""

    async def test_returns_result_with_pav_id(self) -> None:
        """Handler returns AssignProductAttributeResult whose pav_id is a UUID."""
        product_repo = make_product_repo(product_exists=True)
        pav_repo = make_pav_repo(already_exists=False)
        uow = make_uow()
        handler = AssignProductAttributeHandler(
            product_repo=product_repo,
            pav_repo=pav_repo,
            uow=uow,
        )

        result = await handler.handle(make_command())

        assert isinstance(result, AssignProductAttributeResult)
        assert isinstance(result.pav_id, uuid.UUID)

    async def test_calls_product_repo_get(self) -> None:
        """Handler calls product_repo.get() with the command's product_id."""
        product_repo = make_product_repo(product_exists=True)
        pav_repo = make_pav_repo(already_exists=False)
        uow = make_uow()
        handler = AssignProductAttributeHandler(
            product_repo=product_repo,
            pav_repo=pav_repo,
            uow=uow,
        )

        product_id = uuid.uuid4()
        cmd = make_command(product_id=product_id)
        await handler.handle(cmd)

        product_repo.get.assert_awaited_once_with(product_id)

    async def test_checks_duplicate_with_correct_args(self) -> None:
        """Handler calls pav_repo.exists() with product_id and attribute_id."""
        product_repo = make_product_repo(product_exists=True)
        pav_repo = make_pav_repo(already_exists=False)
        uow = make_uow()
        handler = AssignProductAttributeHandler(
            product_repo=product_repo,
            pav_repo=pav_repo,
            uow=uow,
        )

        product_id = uuid.uuid4()
        attribute_id = uuid.uuid4()
        cmd = make_command(product_id=product_id, attribute_id=attribute_id)
        await handler.handle(cmd)

        pav_repo.exists.assert_awaited_once_with(product_id, attribute_id)

    async def test_calls_pav_repo_add(self) -> None:
        """Handler calls pav_repo.add() exactly once with a ProductAttributeValue."""
        product_repo = make_product_repo(product_exists=True)
        pav_repo = make_pav_repo(already_exists=False)
        uow = make_uow()
        handler = AssignProductAttributeHandler(
            product_repo=product_repo,
            pav_repo=pav_repo,
            uow=uow,
        )

        await handler.handle(make_command())

        pav_repo.add.assert_awaited_once()
        added_pav = pav_repo.add.call_args[0][0]
        assert isinstance(added_pav, ProductAttributeValue)

    async def test_pav_fields_match_command(self) -> None:
        """The created PAV carries the correct product_id, attribute_id, and attribute_value_id."""
        product_repo = make_product_repo(product_exists=True)
        pav_repo = make_pav_repo(already_exists=False)
        uow = make_uow()
        handler = AssignProductAttributeHandler(
            product_repo=product_repo,
            pav_repo=pav_repo,
            uow=uow,
        )

        product_id = uuid.uuid4()
        attribute_id = uuid.uuid4()
        attribute_value_id = uuid.uuid4()
        cmd = make_command(
            product_id=product_id,
            attribute_id=attribute_id,
            attribute_value_id=attribute_value_id,
        )
        await handler.handle(cmd)

        added_pav = pav_repo.add.call_args[0][0]
        assert added_pav.product_id == product_id
        assert added_pav.attribute_id == attribute_id
        assert added_pav.attribute_value_id == attribute_value_id

    async def test_calls_uow_commit_once(self) -> None:
        """Handler commits the UoW exactly once on success."""
        product_repo = make_product_repo(product_exists=True)
        pav_repo = make_pav_repo(already_exists=False)
        uow = make_uow()
        handler = AssignProductAttributeHandler(
            product_repo=product_repo,
            pav_repo=pav_repo,
            uow=uow,
        )

        await handler.handle(make_command())

        uow.commit.assert_awaited_once()

    async def test_uow_used_as_context_manager(self) -> None:
        """Handler enters and exits the UoW async context manager."""
        product_repo = make_product_repo(product_exists=True)
        pav_repo = make_pav_repo(already_exists=False)
        uow = make_uow()
        handler = AssignProductAttributeHandler(
            product_repo=product_repo,
            pav_repo=pav_repo,
            uow=uow,
        )

        await handler.handle(make_command())

        uow.__aenter__.assert_awaited_once()
        uow.__aexit__.assert_awaited_once()

    async def test_result_pav_id_matches_created_entity(self) -> None:
        """The pav_id in the result matches the id of the persisted PAV."""
        product_repo = make_product_repo(product_exists=True)
        pav_repo = make_pav_repo(already_exists=False)
        uow = make_uow()
        handler = AssignProductAttributeHandler(
            product_repo=product_repo,
            pav_repo=pav_repo,
            uow=uow,
        )

        result = await handler.handle(make_command())

        added_pav = pav_repo.add.call_args[0][0]
        assert result.pav_id == added_pav.id


# ---------------------------------------------------------------------------
# AssignProductAttributeHandler -- product not found
# ---------------------------------------------------------------------------


class TestAssignProductAttributeHandlerProductNotFound:
    """Handler tests when the product does not exist."""

    async def test_raises_product_not_found_error(self) -> None:
        """Handler raises ProductNotFoundError when product_repo.get() returns None."""
        product_repo = make_product_repo(product_exists=False)
        pav_repo = make_pav_repo(already_exists=False)
        uow = make_uow()
        handler = AssignProductAttributeHandler(
            product_repo=product_repo,
            pav_repo=pav_repo,
            uow=uow,
        )

        with pytest.raises(ProductNotFoundError):
            await handler.handle(make_command())

    async def test_error_contains_product_id(self) -> None:
        """Raised exception includes the missing product's UUID."""
        product_repo = make_product_repo(product_exists=False)
        pav_repo = make_pav_repo(already_exists=False)
        uow = make_uow()
        handler = AssignProductAttributeHandler(
            product_repo=product_repo,
            pav_repo=pav_repo,
            uow=uow,
        )

        product_id = uuid.uuid4()
        cmd = make_command(product_id=product_id)
        with pytest.raises(ProductNotFoundError) as exc_info:
            await handler.handle(cmd)

        assert str(product_id) in str(exc_info.value)

    async def test_pav_repo_not_called(self) -> None:
        """When product is not found, pav_repo.exists() and add() are not called."""
        product_repo = make_product_repo(product_exists=False)
        pav_repo = make_pav_repo(already_exists=False)
        uow = make_uow()
        handler = AssignProductAttributeHandler(
            product_repo=product_repo,
            pav_repo=pav_repo,
            uow=uow,
        )

        with pytest.raises(ProductNotFoundError):
            await handler.handle(make_command())

        pav_repo.exists.assert_not_awaited()
        pav_repo.add.assert_not_awaited()

    async def test_commit_not_called(self) -> None:
        """When product is not found, uow.commit must not be called."""
        product_repo = make_product_repo(product_exists=False)
        pav_repo = make_pav_repo(already_exists=False)
        uow = make_uow()
        handler = AssignProductAttributeHandler(
            product_repo=product_repo,
            pav_repo=pav_repo,
            uow=uow,
        )

        with pytest.raises(ProductNotFoundError):
            await handler.handle(make_command())

        uow.commit.assert_not_awaited()


# ---------------------------------------------------------------------------
# AssignProductAttributeHandler -- duplicate attribute
# ---------------------------------------------------------------------------


class TestAssignProductAttributeHandlerDuplicate:
    """Handler tests when the attribute is already assigned to the product."""

    async def test_raises_duplicate_product_attribute_error(self) -> None:
        """Handler raises DuplicateProductAttributeError when pav_repo.exists() is True."""
        product_repo = make_product_repo(product_exists=True)
        pav_repo = make_pav_repo(already_exists=True)
        uow = make_uow()
        handler = AssignProductAttributeHandler(
            product_repo=product_repo,
            pav_repo=pav_repo,
            uow=uow,
        )

        with pytest.raises(DuplicateProductAttributeError):
            await handler.handle(make_command())

    async def test_error_contains_product_and_attribute_ids(self) -> None:
        """Raised exception details include both product_id and attribute_id."""
        product_repo = make_product_repo(product_exists=True)
        pav_repo = make_pav_repo(already_exists=True)
        uow = make_uow()
        handler = AssignProductAttributeHandler(
            product_repo=product_repo,
            pav_repo=pav_repo,
            uow=uow,
        )

        product_id = uuid.uuid4()
        attribute_id = uuid.uuid4()
        cmd = make_command(product_id=product_id, attribute_id=attribute_id)
        with pytest.raises(DuplicateProductAttributeError) as exc_info:
            await handler.handle(cmd)

        assert exc_info.value.details["product_id"] == str(product_id)
        assert exc_info.value.details["attribute_id"] == str(attribute_id)

    async def test_pav_repo_add_not_called(self) -> None:
        """When duplicate detected, pav_repo.add() must not be called."""
        product_repo = make_product_repo(product_exists=True)
        pav_repo = make_pav_repo(already_exists=True)
        uow = make_uow()
        handler = AssignProductAttributeHandler(
            product_repo=product_repo,
            pav_repo=pav_repo,
            uow=uow,
        )

        with pytest.raises(DuplicateProductAttributeError):
            await handler.handle(make_command())

        pav_repo.add.assert_not_awaited()

    async def test_commit_not_called_on_duplicate(self) -> None:
        """When duplicate detected, uow.commit must not be called."""
        product_repo = make_product_repo(product_exists=True)
        pav_repo = make_pav_repo(already_exists=True)
        uow = make_uow()
        handler = AssignProductAttributeHandler(
            product_repo=product_repo,
            pav_repo=pav_repo,
            uow=uow,
        )

        with pytest.raises(DuplicateProductAttributeError):
            await handler.handle(make_command())

        uow.commit.assert_not_awaited()
