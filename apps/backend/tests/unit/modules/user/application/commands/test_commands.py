import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from _pytest.mark.structures import MarkDecorator

from src.modules.user.application.commands.update_profile import (
    UpdateProfileCommand,
    UpdateProfileHandler,
)
from src.modules.user.domain.exceptions import CustomerNotFoundError

pytestmark: MarkDecorator = pytest.mark.asyncio


def make_uow():
    uow = AsyncMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=False)
    uow.register_aggregate = MagicMock()
    return uow


def make_logger():
    logger = MagicMock()
    logger.bind = MagicMock(return_value=logger)
    return logger


# ── UpdateProfileHandler ─────────────────────────────────────────────


class TestUpdateProfileHandler:
    async def test_update_profile_success(self):
        """Customer found -> updates fields, commits."""
        customer = MagicMock()
        customer.update_profile = MagicMock()
        customer_repo = AsyncMock()
        customer_repo.get = AsyncMock(return_value=customer)
        uow = make_uow()
        logger = make_logger()

        handler = UpdateProfileHandler(
            customer_repo=customer_repo, uow=uow, logger=logger
        )
        customer_id = uuid.uuid4()
        command = UpdateProfileCommand(
            customer_id=customer_id,
            first_name="Alice",
            last_name="Smith",
            phone="+1234567890",
            profile_email="alice@example.com",
        )

        await handler.handle(command)

        customer.update_profile.assert_called_once_with(
            first_name="Alice",
            last_name="Smith",
            phone="+1234567890",
            profile_email="alice@example.com",
        )
        customer_repo.update.assert_awaited_once_with(customer)
        uow.commit.assert_awaited_once()

    async def test_update_profile_not_found(self):
        """Raises CustomerNotFoundError when customer does not exist."""
        customer_repo = AsyncMock()
        customer_repo.get = AsyncMock(return_value=None)
        uow = make_uow()
        logger = make_logger()

        handler = UpdateProfileHandler(
            customer_repo=customer_repo, uow=uow, logger=logger
        )
        customer_id = uuid.uuid4()
        command = UpdateProfileCommand(customer_id=customer_id, first_name="Bob")

        with pytest.raises(CustomerNotFoundError):
            await handler.handle(command)

    async def test_update_profile_no_updates(self):
        """All fields None -> still commits but no update call."""
        customer = MagicMock()
        customer.update_profile = MagicMock()
        customer_repo = AsyncMock()
        customer_repo.get = AsyncMock(return_value=customer)
        uow = make_uow()
        logger = make_logger()

        handler = UpdateProfileHandler(
            customer_repo=customer_repo, uow=uow, logger=logger
        )
        command = UpdateProfileCommand(customer_id=uuid.uuid4())

        await handler.handle(command)

        customer.update_profile.assert_not_called()
        customer_repo.update.assert_not_awaited()
        uow.commit.assert_awaited_once()

    async def test_update_profile_partial_fields(self):
        """Only first_name set -> updates with just that field."""
        customer = MagicMock()
        customer.update_profile = MagicMock()
        customer_repo = AsyncMock()
        customer_repo.get = AsyncMock(return_value=customer)
        uow = make_uow()
        logger = make_logger()

        handler = UpdateProfileHandler(
            customer_repo=customer_repo, uow=uow, logger=logger
        )
        command = UpdateProfileCommand(
            customer_id=uuid.uuid4(),
            first_name="Charlie",
        )

        await handler.handle(command)

        customer.update_profile.assert_called_once_with(first_name="Charlie")
        customer_repo.update.assert_awaited_once_with(customer)
        uow.commit.assert_awaited_once()
