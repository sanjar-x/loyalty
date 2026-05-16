"""Unit tests for InviteStaffHandler.

Covers two CR fixes layered on top of the existing happy path:
* Role validation (CR — fail fast on customer-only roles).
* TTL pulled from settings (replaces the prior hard-coded 72h).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from src.bootstrap.config import settings
from src.modules.identity.application.commands.invite_staff import (
    InviteStaffCommand,
    InviteStaffHandler,
)
from src.modules.identity.domain.entities import Role, StaffInvitation
from src.modules.identity.domain.exceptions import (
    InvitationRoleAccountTypeMismatchError,
)
from src.modules.identity.domain.value_objects import AccountType

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


def _role(target: AccountType | None = AccountType.STAFF) -> Role:
    return Role(
        id=uuid.uuid4(),
        name=f"role-{uuid.uuid4().hex[:8]}",
        description="",
        is_system=False,
        target_account_type=target,
    )


class _FakeIdentityRepo:
    def __init__(self, email_taken: bool = False) -> None:
        self.email_taken = email_taken

    async def email_exists(self, email: str) -> bool:
        return self.email_taken


class _FakeRoleRepo:
    def __init__(self, roles: dict[uuid.UUID, Role] | None = None) -> None:
        self.roles = roles or {}

    async def get(self, role_id: uuid.UUID) -> Role | None:
        return self.roles.get(role_id)


class _FakeInvitationRepo:
    def __init__(self) -> None:
        self.added: list[StaffInvitation] = []

    async def get_pending_by_email(self, email: str) -> StaffInvitation | None:
        return None

    async def add(self, invitation: StaffInvitation) -> StaffInvitation:
        self.added.append(invitation)
        return invitation


class _FakeUow:
    def __init__(self) -> None:
        self.committed = False
        self.aggregates: list[Any] = []
        self.external_events: list[dict[str, Any]] = []

    async def __aenter__(self) -> _FakeUow:
        return self

    async def __aexit__(self, *args: Any) -> None:
        return None

    async def flush(self) -> None:
        pass

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        pass

    def register_aggregate(self, aggregate: Any) -> None:
        self.aggregates.append(aggregate)

    def enqueue_external_event(self, **kwargs: Any) -> None:
        self.external_events.append(kwargs)


class _FakeLogger:
    def bind(self, **_kwargs: Any) -> _FakeLogger:
        return self

    def info(self, *args: Any, **kwargs: Any) -> None:
        pass

    def warning(self, *args: Any, **kwargs: Any) -> None:
        pass


def _build(
    roles: list[Role],
    *,
    email_taken: bool = False,
) -> tuple[InviteStaffHandler, _FakeInvitationRepo]:
    invitation_repo = _FakeInvitationRepo()
    handler = InviteStaffHandler(
        identity_repo=_FakeIdentityRepo(email_taken=email_taken),  # ty:ignore[invalid-argument-type]
        role_repo=_FakeRoleRepo({r.id: r for r in roles}),  # ty:ignore[invalid-argument-type]
        invitation_repo=invitation_repo,  # ty:ignore[invalid-argument-type]
        uow=_FakeUow(),  # ty:ignore[invalid-argument-type]
        logger=_FakeLogger(),  # ty:ignore[invalid-argument-type]
    )
    return handler, invitation_repo


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRoleValidation:
    async def test_customer_role_rejected(self) -> None:
        role = _role(target=AccountType.CUSTOMER)
        handler, _ = _build([role])
        with pytest.raises(InvitationRoleAccountTypeMismatchError) as exc_info:
            await handler.handle(
                InviteStaffCommand(
                    email="x@example.com",
                    role_ids=[role.id],
                    invited_by=uuid.uuid4(),
                )
            )
        assert exc_info.value.details["role_id"] == str(role.id)

    async def test_staff_role_accepted(self) -> None:
        role = _role(target=AccountType.STAFF)
        handler, repo = _build([role])
        await handler.handle(
            InviteStaffCommand(
                email="x@example.com",
                role_ids=[role.id],
                invited_by=uuid.uuid4(),
            )
        )
        assert len(repo.added) == 1

    async def test_role_without_target_accepted(self) -> None:
        """Roles whose target is None (un-restricted) are allowed for staff invites."""
        role = _role(target=None)
        handler, repo = _build([role])
        await handler.handle(
            InviteStaffCommand(
                email="x@example.com",
                role_ids=[role.id],
                invited_by=uuid.uuid4(),
            )
        )
        assert len(repo.added) == 1


class TestTtlFromSettings:
    async def test_invitation_expires_at_uses_settings_ttl(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """``expires_at`` is ``created_at + STAFF_INVITATION_TTL_HOURS``.

        Asserts the TTL is pulled from settings rather than the prior
        hard-coded 72h default on the entity.
        """
        monkeypatch.setattr(settings, "STAFF_INVITATION_TTL_HOURS", 24)
        role = _role()
        handler, repo = _build([role])
        before = datetime.now(UTC)
        await handler.handle(
            InviteStaffCommand(
                email="x@example.com",
                role_ids=[role.id],
                invited_by=uuid.uuid4(),
            )
        )
        after = datetime.now(UTC)
        inv = repo.added[0]
        # expires_at falls within [before + 24h, after + 24h]
        assert before + timedelta(hours=24) <= inv.expires_at
        assert inv.expires_at <= after + timedelta(hours=24)
