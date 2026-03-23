import uuid
from collections.abc import Callable
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock

import pytest
from _pytest.mark.structures import MarkDecorator

from src.modules.user.application.consumers.identity_events import (
    anonymize_customer_on_identity_deactivated,
    create_profile_on_identity_registered,
)

pytestmark: MarkDecorator = pytest.mark.asyncio


def _unwrap_dishka_task(task: Any) -> Callable[..., Any]:
    return cast(Callable[..., Any], task.original_func.__dishka_orig_func__)


_create_profile_fn = _unwrap_dishka_task(create_profile_on_identity_registered)
_anonymize_customer_fn = _unwrap_dishka_task(anonymize_customer_on_identity_deactivated)


def make_uow():
    uow = AsyncMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=False)
    uow.register_aggregate = MagicMock()
    return uow


# ── create_profile_on_identity_registered ────────────────────────────


class TestCreateProfileOnIdentityRegistered:
    async def test_creates_customer_on_registration(self):
        """No existing customer -> creates customer, commits, returns success."""
        customer_repo = AsyncMock()
        customer_repo.get = AsyncMock(return_value=None)
        staff_repo = AsyncMock()
        uow = make_uow()

        identity_id = str(uuid.uuid4())
        result = await _create_profile_fn(
            identity_id=identity_id,
            email="test@example.com",
            customer_repo=customer_repo,
            staff_repo=staff_repo,
            uow=uow,
        )

        assert result["status"] == "success"
        customer_repo.add.assert_awaited_once()
        created_customer = customer_repo.add.call_args[0][0]
        assert created_customer.id == uuid.UUID(identity_id)
        uow.commit.assert_awaited_once()

    async def test_skips_existing_customer(self):
        """Customer exists -> returns skipped status."""
        existing_customer = MagicMock()
        customer_repo = AsyncMock()
        customer_repo.get = AsyncMock(return_value=existing_customer)
        staff_repo = AsyncMock()
        uow = make_uow()

        result = await _create_profile_fn(
            identity_id=str(uuid.uuid4()),
            email="existing@example.com",
            customer_repo=customer_repo,
            staff_repo=staff_repo,
            uow=uow,
        )

        assert result == {"status": "skipped", "reason": "already_exists"}
        customer_repo.add.assert_not_awaited()
        uow.commit.assert_not_awaited()


# ── anonymize_customer_on_identity_deactivated ───────────────────────


class TestAnonymizeCustomerOnIdentityDeactivated:
    async def test_anonymizes_customer_on_deactivation(self):
        """Customer found -> anonymizes, commits, returns success."""
        customer = MagicMock()
        customer.anonymize = MagicMock()
        customer_repo = AsyncMock()
        customer_repo.get = AsyncMock(return_value=customer)
        uow = make_uow()

        identity_id = str(uuid.uuid4())
        result = await _anonymize_customer_fn(
            identity_id=identity_id,
            customer_repo=customer_repo,
            uow=uow,
        )

        assert result["status"] == "success"
        customer.anonymize.assert_called_once()
        customer_repo.update.assert_awaited_once_with(customer)
        uow.commit.assert_awaited_once()

    async def test_skips_missing_customer(self):
        """No customer -> returns skipped status."""
        customer_repo = AsyncMock()
        customer_repo.get = AsyncMock(return_value=None)
        uow = make_uow()

        result = await _anonymize_customer_fn(
            identity_id=str(uuid.uuid4()),
            customer_repo=customer_repo,
            uow=uow,
        )

        assert result == {"status": "skipped", "reason": "not_found"}
        customer_repo.update.assert_not_awaited()
        uow.commit.assert_not_awaited()
