import uuid
from collections.abc import Callable
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock

import pytest
from _pytest.mark.structures import MarkDecorator

from src.modules.user.application.consumers.identity_events import (
    anonymize_user_on_identity_deactivated,
    create_user_on_identity_registered,
)

pytestmark: MarkDecorator = pytest.mark.asyncio


def _unwrap_dishka_task(task: Any) -> Callable[..., Any]:
    return cast(Callable[..., Any], getattr(task.original_func, "__dishka_orig_func__"))


_create_user_fn = _unwrap_dishka_task(create_user_on_identity_registered)
_anonymize_user_fn = _unwrap_dishka_task(anonymize_user_on_identity_deactivated)


def make_uow():
    uow = AsyncMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=False)
    uow.register_aggregate = MagicMock()
    return uow


# ── create_user_on_identity_registered ───────────────────────────────


class TestCreateUserOnIdentityRegistered:
    async def test_creates_user_on_registration(self):
        """No existing user -> creates user, commits, returns success."""
        user_repo = AsyncMock()
        user_repo.get = AsyncMock(return_value=None)
        uow = make_uow()

        identity_id = str(uuid.uuid4())
        result = await _create_user_fn(
            identity_id=identity_id,
            email="test@example.com",
            user_repo=user_repo,
            uow=uow,
        )

        assert result == {"status": "success"}
        user_repo.add.assert_awaited_once()
        created_user = user_repo.add.call_args[0][0]
        assert created_user.id == uuid.UUID(identity_id)
        assert created_user.profile_email == "test@example.com"
        uow.commit.assert_awaited_once()

    async def test_skips_existing_user(self):
        """User exists -> returns skipped status."""
        existing_user = MagicMock()
        user_repo = AsyncMock()
        user_repo.get = AsyncMock(return_value=existing_user)
        uow = make_uow()

        result = await _create_user_fn(
            identity_id=str(uuid.uuid4()),
            email="existing@example.com",
            user_repo=user_repo,
            uow=uow,
        )

        assert result == {"status": "skipped", "reason": "already_exists"}
        user_repo.add.assert_not_awaited()
        uow.commit.assert_not_awaited()


# ── anonymize_user_on_identity_deactivated ───────────────────────────


class TestAnonymizeUserOnIdentityDeactivated:
    async def test_anonymizes_user_on_deactivation(self):
        """User found -> anonymizes, commits, returns success."""
        user = MagicMock()
        user.anonymize = MagicMock()
        user_repo = AsyncMock()
        user_repo.get = AsyncMock(return_value=user)
        uow = make_uow()

        identity_id = str(uuid.uuid4())
        result = await _anonymize_user_fn(
            identity_id=identity_id,
            user_repo=user_repo,
            uow=uow,
        )

        assert result == {"status": "success"}
        user.anonymize.assert_called_once()
        user_repo.update.assert_awaited_once_with(user)
        uow.commit.assert_awaited_once()

    async def test_skips_missing_user(self):
        """No user -> returns skipped status."""
        user_repo = AsyncMock()
        user_repo.get = AsyncMock(return_value=None)
        uow = make_uow()

        result = await _anonymize_user_fn(
            identity_id=str(uuid.uuid4()),
            user_repo=user_repo,
            uow=uow,
        )

        assert result == {"status": "skipped", "reason": "user_not_found"}
        user_repo.update.assert_not_awaited()
        uow.commit.assert_not_awaited()
