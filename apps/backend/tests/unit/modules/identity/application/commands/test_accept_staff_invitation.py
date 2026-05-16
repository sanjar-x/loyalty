"""Unit tests for ``AcceptStaffInvitationHandler``.

Primary purpose: regression coverage for the production FK-violation bug
(2026-05-16). The handler used to flush ``staff_invitations.accepted_identity_id``
*before* inserting the corresponding ``identities`` row, which caused
``ForeignKeyViolationError`` on the very first ``invitation_repo.update()``.
Tests pin the persistence ordering so a future re-shuffle of the steps
can't silently re-introduce the same bug.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from src.modules.identity.application.commands.accept_staff_invitation import (
    AcceptStaffInvitationCommand,
    AcceptStaffInvitationHandler,
)
from src.modules.identity.domain.entities import (
    Identity,
    LocalCredentials,
    Role,
    Session,
    StaffInvitation,
)
from src.modules.identity.domain.value_objects import AccountType, InvitationStatus

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Recording fakes — every mutating call appends a stable label to a shared
# ``trace`` list so tests can assert ordering directly.
# ---------------------------------------------------------------------------


class _FakeIdentityRepo:
    def __init__(self, trace: list[str]) -> None:
        self.trace = trace
        self.added_identities: list[Identity] = []
        self.added_credentials: list[LocalCredentials] = []

    async def add(self, identity: Identity) -> Identity:
        self.trace.append("identity.add")
        self.added_identities.append(identity)
        return identity

    async def add_credentials(self, credentials: LocalCredentials) -> LocalCredentials:
        self.trace.append("identity.add_credentials")
        self.added_credentials.append(credentials)
        return credentials


class _FakeInvitationRepo:
    def __init__(self, invitation: StaffInvitation, trace: list[str]) -> None:
        self._invitation = invitation
        self.trace = trace
        self.updates: list[StaffInvitation] = []

    async def get_by_token_hash(self, token_hash: str) -> StaffInvitation | None:
        self.trace.append("invitation.get_by_token_hash")
        return self._invitation

    async def update(self, invitation: StaffInvitation) -> StaffInvitation:
        self.trace.append("invitation.update")
        self.updates.append(invitation)
        return invitation


class _FakeRoleRepo:
    def __init__(self, roles: dict[uuid.UUID, Role], trace: list[str]) -> None:
        self._roles = roles
        self.trace = trace
        self.assigned: list[tuple[uuid.UUID, uuid.UUID]] = []

    async def get(self, role_id: uuid.UUID) -> Role | None:
        return self._roles.get(role_id)

    async def assign_to_identity(
        self, *, identity_id: uuid.UUID, role_id: uuid.UUID
    ) -> None:
        self.trace.append("role.assign_to_identity")
        self.assigned.append((identity_id, role_id))

    async def get_identity_role_ids(self, identity_id: uuid.UUID) -> list[uuid.UUID]:
        return [rid for _ident, rid in self.assigned if _ident == identity_id]


class _FakeSessionRepo:
    def __init__(self, trace: list[str]) -> None:
        self.trace = trace
        self.added_sessions: list[Session] = []
        self.session_roles: list[tuple[uuid.UUID, list[uuid.UUID]]] = []

    async def add(self, session: Session) -> Session:
        self.trace.append("session.add")
        self.added_sessions.append(session)
        return session

    async def add_session_roles(
        self, session_id: uuid.UUID, role_ids: list[uuid.UUID]
    ) -> None:
        self.trace.append("session.add_roles")
        self.session_roles.append((session_id, role_ids))


class _FakeUow:
    def __init__(self) -> None:
        self.committed = False
        self.aggregates: list[Any] = []

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
        pass


class _FakeHasher:
    def hash(self, password: str) -> str:
        return f"hashed:{password}"

    def verify(self, password: str, hash_: str) -> bool:
        return hash_ == f"hashed:{password}"


class _FakeTokenProvider:
    def create_refresh_token(self) -> tuple[str, str]:
        return ("refresh-raw", "refresh-hash")

    def create_access_token(self, *, payload_data: dict[str, Any]) -> str:
        return f"access:{payload_data['sub']}"


class _FakeLogger:
    def bind(self, **_kwargs: Any) -> _FakeLogger:
        return self

    def info(self, *args: Any, **kwargs: Any) -> None:
        pass

    def warning(self, *args: Any, **kwargs: Any) -> None:
        pass

    def error(self, *args: Any, **kwargs: Any) -> None:
        pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _invitation_with_token(raw_token: str, role_id: uuid.UUID) -> StaffInvitation:
    now = datetime.now(UTC)
    return StaffInvitation(
        id=uuid.uuid4(),
        email="new-staff@example.com",
        token_hash=StaffInvitation.hash_token(raw_token),
        role_ids=[role_id],
        invited_by=uuid.uuid4(),
        status=InvitationStatus.PENDING,
        accepted_identity_id=None,
        created_at=now,
        expires_at=now + timedelta(hours=72),
        accepted_at=None,
    )


def _build(
    role: Role,
) -> tuple[
    AcceptStaffInvitationHandler,
    list[str],
    _FakeIdentityRepo,
    _FakeInvitationRepo,
    StaffInvitation,
    str,
]:
    trace: list[str] = []
    raw_token = "test-token-" + uuid.uuid4().hex
    invitation = _invitation_with_token(raw_token, role.id)
    identity_repo = _FakeIdentityRepo(trace)
    invitation_repo = _FakeInvitationRepo(invitation, trace)
    role_repo = _FakeRoleRepo({role.id: role}, trace)
    session_repo = _FakeSessionRepo(trace)
    handler = AcceptStaffInvitationHandler(
        invitation_repo=invitation_repo,  # ty:ignore[invalid-argument-type]
        identity_repo=identity_repo,  # ty:ignore[invalid-argument-type]
        role_repo=role_repo,  # ty:ignore[invalid-argument-type]
        session_repo=session_repo,  # ty:ignore[invalid-argument-type]
        uow=_FakeUow(),  # ty:ignore[invalid-argument-type]
        hasher=_FakeHasher(),  # ty:ignore[invalid-argument-type]
        token_provider=_FakeTokenProvider(),  # ty:ignore[invalid-argument-type]
        logger=_FakeLogger(),  # ty:ignore[invalid-argument-type]
    )
    return handler, trace, identity_repo, invitation_repo, invitation, raw_token


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_identity_persisted_before_invitation_update() -> None:
    """Regression for the 2026-05-16 prod bug (FK violation).

    ``invitation_repo.update(invitation)`` sets ``accepted_identity_id``
    — a FK reference to ``identities(id)``. If ``identity_repo.add(identity)``
    runs *after* the invitation update, asyncpg raises
    ``ForeignKeyViolationError`` because the identity row does not yet
    exist in the session. The persistence order must therefore be:

        identity.add → identity.add_credentials → invitation.update

    This test pins that ordering against the fake repo trace.
    """
    role = Role(
        id=uuid.uuid4(),
        name="manager",
        description="",
        is_system=True,
        target_account_type=AccountType.STAFF,
    )
    handler, trace, identity_repo, invitation_repo, _inv, raw_token = _build(role)

    result = await handler.handle(
        AcceptStaffInvitationCommand(
            raw_token=raw_token,
            password="S3cure!Pass",
            first_name="Test",
            last_name="User",
            ip_address="127.0.0.1",
            user_agent="TestAgent/1.0",
        )
    )

    # Sanity checks.
    assert result.access_token.startswith("access:")
    assert len(identity_repo.added_identities) == 1
    assert len(invitation_repo.updates) == 1

    # The regression-critical assertion: identity insert must precede
    # the invitation update that carries the FK.
    identity_idx = trace.index("identity.add")
    invitation_update_idx = trace.index("invitation.update")
    assert identity_idx < invitation_update_idx, (
        f"identity.add must run before invitation.update — trace: {trace}"
    )
    # Credentials too — they share the same identity_id FK.
    credentials_idx = trace.index("identity.add_credentials")
    assert credentials_idx < invitation_update_idx, (
        f"identity.add_credentials must run before invitation.update — trace: {trace}"
    )


async def test_invitation_marked_accepted_with_new_identity_id() -> None:
    """``invitation.accept(identity.id)`` carries the freshly-minted UUID
    so the FK on ``staff_invitations.accepted_identity_id`` points to a
    row that will exist after commit."""
    role = Role(
        id=uuid.uuid4(),
        name="manager",
        description="",
        is_system=True,
        target_account_type=AccountType.STAFF,
    )
    handler, _trace, identity_repo, invitation_repo, _inv, raw_token = _build(role)

    await handler.handle(
        AcceptStaffInvitationCommand(
            raw_token=raw_token,
            password="S3cure!Pass",
            first_name="Test",
            last_name="User",
            ip_address="127.0.0.1",
            user_agent="TestAgent/1.0",
        )
    )

    persisted_identity = identity_repo.added_identities[0]
    updated_invitation = invitation_repo.updates[0]
    assert updated_invitation.accepted_identity_id == persisted_identity.id
    assert updated_invitation.status is InvitationStatus.ACCEPTED
