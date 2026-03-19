import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from _pytest.mark.structures import MarkDecorator

from src.modules.user.application.commands.anonymize_user import (
    AnonymizeUserCommand,
    AnonymizeUserHandler,
)
from src.modules.user.application.commands.create_user import (
    CreateUserCommand,
    CreateUserHandler,
)
from src.modules.user.application.commands.update_profile import (
    UpdateProfileCommand,
    UpdateProfileHandler,
)
from src.modules.user.domain.exceptions import UserNotFoundError

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


# ── CreateUserHandler ────────────────────────────────────────────────


class TestCreateUserHandler:
    async def test_create_user_success(self):
        """No existing user -> creates User via User.create_from_identity, commits."""
        user_repo = AsyncMock()
        user_repo.get = AsyncMock(return_value=None)
        uow = make_uow()
        logger = make_logger()

        handler = CreateUserHandler(user_repo=user_repo, uow=uow, logger=logger)
        identity_id = uuid.uuid4()
        command = CreateUserCommand(identity_id=identity_id, profile_email="new@example.com")

        await handler.handle(command)

        user_repo.get.assert_awaited_once_with(identity_id)
        user_repo.add.assert_awaited_once()
        created_user = user_repo.add.call_args[0][0]
        assert created_user.id == identity_id
        assert created_user.profile_email == "new@example.com"
        uow.commit.assert_awaited_once()

    async def test_create_user_idempotent_skip(self):
        """Existing user found -> returns without creating."""
        existing_user = MagicMock()
        user_repo = AsyncMock()
        user_repo.get = AsyncMock(return_value=existing_user)
        uow = make_uow()
        logger = make_logger()

        handler = CreateUserHandler(user_repo=user_repo, uow=uow, logger=logger)
        command = CreateUserCommand(identity_id=uuid.uuid4())

        await handler.handle(command)

        user_repo.add.assert_not_awaited()
        uow.commit.assert_not_awaited()


# ── AnonymizeUserHandler ─────────────────────────────────────────────


class TestAnonymizeUserHandler:
    async def test_anonymize_user_success(self):
        """User found -> calls user.anonymize(), updates, commits."""
        user = MagicMock()
        user.anonymize = MagicMock()
        user_repo = AsyncMock()
        user_repo.get = AsyncMock(return_value=user)
        uow = make_uow()
        logger = make_logger()

        handler = AnonymizeUserHandler(user_repo=user_repo, uow=uow, logger=logger)
        user_id = uuid.uuid4()
        command = AnonymizeUserCommand(user_id=user_id)

        await handler.handle(command)

        user_repo.get.assert_awaited_once_with(user_id)
        user.anonymize.assert_called_once()
        user_repo.update.assert_awaited_once_with(user)
        uow.commit.assert_awaited_once()

    async def test_anonymize_user_not_found_returns_silently(self):
        """No user -> returns without error."""
        user_repo = AsyncMock()
        user_repo.get = AsyncMock(return_value=None)
        uow = make_uow()
        logger = make_logger()

        handler = AnonymizeUserHandler(user_repo=user_repo, uow=uow, logger=logger)
        command = AnonymizeUserCommand(user_id=uuid.uuid4())

        await handler.handle(command)

        user_repo.update.assert_not_awaited()
        uow.commit.assert_not_awaited()


# ── UpdateProfileHandler ─────────────────────────────────────────────


class TestUpdateProfileHandler:
    async def test_update_profile_success(self):
        """User found -> updates fields, commits."""
        user = MagicMock()
        user.update_profile = MagicMock()
        user_repo = AsyncMock()
        user_repo.get = AsyncMock(return_value=user)
        uow = make_uow()
        logger = make_logger()

        handler = UpdateProfileHandler(user_repo=user_repo, uow=uow, logger=logger)
        user_id = uuid.uuid4()
        command = UpdateProfileCommand(
            user_id=user_id,
            first_name="Alice",
            last_name="Smith",
            phone="+1234567890",
            profile_email="alice@example.com",
        )

        await handler.handle(command)

        user.update_profile.assert_called_once_with(
            first_name="Alice",
            last_name="Smith",
            phone="+1234567890",
            profile_email="alice@example.com",
        )
        user_repo.update.assert_awaited_once_with(user)
        uow.commit.assert_awaited_once()

    async def test_update_profile_not_found(self):
        """Raises UserNotFoundError when user does not exist."""
        user_repo = AsyncMock()
        user_repo.get = AsyncMock(return_value=None)
        uow = make_uow()
        logger = make_logger()

        handler = UpdateProfileHandler(user_repo=user_repo, uow=uow, logger=logger)
        user_id = uuid.uuid4()
        command = UpdateProfileCommand(user_id=user_id, first_name="Bob")

        with pytest.raises(UserNotFoundError):
            await handler.handle(command)

    async def test_update_profile_no_updates(self):
        """All fields None -> still commits but no update call."""
        user = MagicMock()
        user.update_profile = MagicMock()
        user_repo = AsyncMock()
        user_repo.get = AsyncMock(return_value=user)
        uow = make_uow()
        logger = make_logger()

        handler = UpdateProfileHandler(user_repo=user_repo, uow=uow, logger=logger)
        command = UpdateProfileCommand(user_id=uuid.uuid4())

        await handler.handle(command)

        user.update_profile.assert_not_called()
        user_repo.update.assert_not_awaited()
        uow.commit.assert_awaited_once()

    async def test_update_profile_partial_fields(self):
        """Only first_name set -> updates with just that field."""
        user = MagicMock()
        user.update_profile = MagicMock()
        user_repo = AsyncMock()
        user_repo.get = AsyncMock(return_value=user)
        uow = make_uow()
        logger = make_logger()

        handler = UpdateProfileHandler(user_repo=user_repo, uow=uow, logger=logger)
        command = UpdateProfileCommand(
            user_id=uuid.uuid4(),
            first_name="Charlie",
        )

        await handler.handle(command)

        user.update_profile.assert_called_once_with(first_name="Charlie")
        user_repo.update.assert_awaited_once_with(user)
        uow.commit.assert_awaited_once()
