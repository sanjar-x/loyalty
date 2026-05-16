"""Unit tests for ResendStaffInvitationHandler.

Covers the revoke-old + mint-new contract plus the re-validation
guards that prevent the resend from issuing an invite that the
acceptance flow would later reject.
"""

from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from src.modules.identity.application.commands.resend_staff_invitation import (
    ResendStaffInvitationCommand,
    ResendStaffInvitationHandler,
)
from src.modules.identity.domain.entities import Role, StaffInvitation
from src.modules.identity.domain.exceptions import (
    IdentityAlreadyExistsError,
    InvitationAlreadyAcceptedError,
    InvitationNotFoundError,
    InvitationRoleAccountTypeMismatchError,
)
from src.modules.identity.domain.value_objects import (
    AccountType,
    InvitationStatus,
)

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


def _invitation(
    *,
    status: InvitationStatus = InvitationStatus.PENDING,
    role_ids: list[uuid.UUID] | None = None,
    email: str = "x@example.com",
) -> StaffInvitation:
    inv = StaffInvitation.create(
        email=email,
        invited_by=uuid.uuid4(),
        role_ids=role_ids or [uuid.uuid4()],
        raw_token=secrets.token_urlsafe(16),
        ttl_hours=72,
    )
    # Force the requested status onto the fresh aggregate.
    if status is InvitationStatus.ACCEPTED:
        inv.status = InvitationStatus.ACCEPTED
        inv.accepted_at = datetime.now(UTC)
        inv.accepted_identity_id = uuid.uuid4()
    elif status is InvitationStatus.REVOKED:
        inv.status = InvitationStatus.REVOKED
    elif status is InvitationStatus.EXPIRED:
        inv.status = InvitationStatus.EXPIRED
        inv.expires_at = datetime.now(UTC) - timedelta(hours=1)
    inv.clear_domain_events()
    return inv


class _FakeIdentityRepo:
    def __init__(self, email_taken: bool = False) -> None:
        self.email_taken = email_taken

    async def email_exists(self, email: str) -> bool:
        return self.email_taken


class _FakeRoleRepo:
    def __init__(self, roles: dict[uuid.UUID, Role]) -> None:
        self.roles = roles

    async def get(self, role_id: uuid.UUID) -> Role | None:
        return self.roles.get(role_id)


class _FakeInvitationRepo:
    def __init__(self, source: StaffInvitation | None) -> None:
        self.source = source
        self.added: list[StaffInvitation] = []
        self.updated: list[StaffInvitation] = []

    async def get(self, invitation_id: uuid.UUID) -> StaffInvitation | None:
        if self.source is None or self.source.id != invitation_id:
            return None
        return self.source

    async def add(self, invitation: StaffInvitation) -> StaffInvitation:
        self.added.append(invitation)
        return invitation

    async def update(self, invitation: StaffInvitation) -> None:
        self.updated.append(invitation)


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
    source: StaffInvitation | None,
    *,
    roles: list[Role] | None = None,
    email_taken: bool = False,
) -> tuple[ResendStaffInvitationHandler, _FakeInvitationRepo]:
    invitation_repo = _FakeInvitationRepo(source)
    role_repo = _FakeRoleRepo({r.id: r for r in (roles or [])})
    handler = ResendStaffInvitationHandler(
        invitation_repo=invitation_repo,  # ty:ignore[invalid-argument-type]
        identity_repo=_FakeIdentityRepo(email_taken=email_taken),  # ty:ignore[invalid-argument-type]
        role_repo=role_repo,  # ty:ignore[invalid-argument-type]
        uow=_FakeUow(),  # ty:ignore[invalid-argument-type]
        logger=_FakeLogger(),  # ty:ignore[invalid-argument-type]
    )
    return handler, invitation_repo


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestResend:
    async def test_not_found(self) -> None:
        handler, _ = _build(None)
        with pytest.raises(InvitationNotFoundError):
            await handler.handle(
                ResendStaffInvitationCommand(
                    invitation_id=uuid.uuid4(),
                    requested_by=uuid.uuid4(),
                )
            )

    async def test_accepted_rejected(self) -> None:
        role = _role()
        inv = _invitation(status=InvitationStatus.ACCEPTED, role_ids=[role.id])
        handler, _ = _build(inv, roles=[role])
        with pytest.raises(InvitationAlreadyAcceptedError):
            await handler.handle(
                ResendStaffInvitationCommand(
                    invitation_id=inv.id,
                    requested_by=uuid.uuid4(),
                )
            )

    async def test_pending_revokes_and_creates_new(self) -> None:
        role = _role()
        inv = _invitation(role_ids=[role.id])
        original_token_hash = inv.token_hash
        handler, repo = _build(inv, roles=[role])

        result = await handler.handle(
            ResendStaffInvitationCommand(
                invitation_id=inv.id,
                requested_by=uuid.uuid4(),
            )
        )

        # Source flipped to REVOKED and was persisted.
        assert inv.status is InvitationStatus.REVOKED
        assert inv in repo.updated
        # Fresh invitation persisted, with a different id and token hash.
        assert len(repo.added) == 1
        fresh = repo.added[0]
        assert fresh.id != inv.id
        assert fresh.token_hash != original_token_hash
        assert fresh.email == inv.email
        assert fresh.role_ids == inv.role_ids
        assert fresh.status is InvitationStatus.PENDING
        assert result.invitation_id == fresh.id
        assert result.raw_token  # CSPRNG token returned

    async def test_revoked_source_no_double_revoke(self) -> None:
        """REVOKED / EXPIRED sources are simply superseded — no .revoke() call."""
        role = _role()
        inv = _invitation(status=InvitationStatus.REVOKED, role_ids=[role.id])
        handler, repo = _build(inv, roles=[role])
        await handler.handle(
            ResendStaffInvitationCommand(
                invitation_id=inv.id,
                requested_by=uuid.uuid4(),
            )
        )
        # The source was not touched (no second .revoke() that would raise
        # InvitationNotPendingError), only the new one was added.
        assert inv not in repo.updated
        assert len(repo.added) == 1

    async def test_email_now_registered_rejected(self) -> None:
        role = _role()
        inv = _invitation(role_ids=[role.id])
        handler, _ = _build(inv, roles=[role], email_taken=True)
        with pytest.raises(IdentityAlreadyExistsError):
            await handler.handle(
                ResendStaffInvitationCommand(
                    invitation_id=inv.id,
                    requested_by=uuid.uuid4(),
                )
            )

    async def test_role_retargeted_to_customer_rejected(self) -> None:
        """Role re-validation catches a role that was STAFF when the
        original invite went out but has since been re-targeted."""
        role = _role(target=AccountType.CUSTOMER)
        inv = _invitation(role_ids=[role.id])
        handler, _ = _build(inv, roles=[role])
        with pytest.raises(InvitationRoleAccountTypeMismatchError):
            await handler.handle(
                ResendStaffInvitationCommand(
                    invitation_id=inv.id,
                    requested_by=uuid.uuid4(),
                )
            )

    async def test_requested_by_recorded_on_new_invitation(self) -> None:
        role = _role()
        inv = _invitation(role_ids=[role.id])
        new_admin = uuid.uuid4()
        handler, repo = _build(inv, roles=[role])
        await handler.handle(
            ResendStaffInvitationCommand(
                invitation_id=inv.id,
                requested_by=new_admin,
            )
        )
        assert repo.added[0].invited_by == new_admin
