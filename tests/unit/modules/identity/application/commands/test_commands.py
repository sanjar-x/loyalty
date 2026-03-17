"""Unit tests for all identity module command handlers."""

import hashlib
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.modules.identity.application.commands.assign_role import (
    AssignRoleCommand,
    AssignRoleHandler,
)
from src.modules.identity.application.commands.create_role import (
    CreateRoleCommand,
    CreateRoleHandler,
    CreateRoleResult,
)
from src.modules.identity.application.commands.deactivate_identity import (
    DeactivateIdentityCommand,
    DeactivateIdentityHandler,
)
from src.modules.identity.application.commands.delete_role import (
    DeleteRoleCommand,
    DeleteRoleHandler,
)
from src.modules.identity.application.commands.login_oidc import (
    LoginOIDCCommand,
    LoginOIDCHandler,
    LoginOIDCResult,
)
from src.modules.identity.application.commands.logout import (
    LogoutCommand,
    LogoutHandler,
)
from src.modules.identity.application.commands.logout_all import (
    LogoutAllCommand,
    LogoutAllHandler,
)
from src.modules.identity.application.commands.refresh_token import (
    RefreshTokenCommand,
    RefreshTokenHandler,
    RefreshTokenResult,
)
from src.modules.identity.application.commands.revoke_role import (
    RevokeRoleCommand,
    RevokeRoleHandler,
)
from src.modules.identity.domain.entities import (
    Identity,
    LinkedAccount,
    Role,
    Session,
)
from src.modules.identity.domain.events import (
    IdentityRegisteredEvent,
    RoleAssignmentChangedEvent,
)
from src.modules.identity.domain.exceptions import (
    IdentityDeactivatedError,
    InvalidCredentialsError,
    RefreshTokenReuseError,
    SessionExpiredError,
    SystemRoleModificationError,
)
from src.modules.identity.domain.value_objects import IdentityType
from src.shared.exceptions import ConflictError, NotFoundError
from src.shared.interfaces.security import OIDCUserInfo

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_uow():
    uow = AsyncMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=False)
    # register_aggregate is synchronous in the real UoW, so use MagicMock
    uow.register_aggregate = MagicMock()
    return uow


def make_logger():
    logger = MagicMock()
    logger.bind = MagicMock(return_value=logger)
    logger.info = MagicMock()
    logger.warning = MagicMock()
    return logger


def make_identity(
    identity_id: uuid.UUID | None = None,
    is_active: bool = True,
    identity_type: IdentityType = IdentityType.LOCAL,
) -> Identity:
    iid = identity_id or uuid.uuid4()
    identity = Identity(
        id=iid,
        type=identity_type,
        is_active=is_active,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    return identity


def make_session(
    session_id: uuid.UUID | None = None,
    identity_id: uuid.UUID | None = None,
    is_revoked: bool = False,
    is_expired: bool = False,
    refresh_token_hash: str = "somehash",
) -> Session:
    sid = session_id or uuid.uuid4()
    iid = identity_id or uuid.uuid4()
    now = datetime.now(UTC)
    expires_at = now - timedelta(days=1) if is_expired else now + timedelta(days=30)
    return Session(
        id=sid,
        identity_id=iid,
        refresh_token_hash=refresh_token_hash,
        ip_address="127.0.0.1",
        user_agent="test",
        is_revoked=is_revoked,
        created_at=now,
        expires_at=expires_at,
        activated_roles=[],
    )


def make_role(
    role_id: uuid.UUID | None = None,
    name: str = "admin",
    is_system: bool = False,
) -> Role:
    return Role(
        id=role_id or uuid.uuid4(),
        name=name,
        description=None,
        is_system=is_system,
    )


# ===========================================================================
# 1. LogoutHandler
# ===========================================================================


class TestLogoutHandler:
    async def test_logout_revokes_session_and_invalidates_cache(self):
        session_id = uuid.uuid4()
        identity_id = uuid.uuid4()
        session = make_session(session_id=session_id, identity_id=identity_id, is_revoked=False)

        session_repo = AsyncMock()
        session_repo.get.return_value = session
        uow = make_uow()
        permission_resolver = AsyncMock()
        logger = make_logger()

        handler = LogoutHandler(
            session_repo=session_repo,
            uow=uow,
            permission_resolver=permission_resolver,
            logger=logger,
        )

        await handler.handle(LogoutCommand(session_id=session_id))

        # Session should have been revoked and updated
        assert session.is_revoked is True
        session_repo.update.assert_awaited_once_with(session)
        uow.commit.assert_awaited_once()
        permission_resolver.invalidate.assert_awaited_once_with(session_id)

    async def test_logout_skips_already_revoked_session(self):
        session_id = uuid.uuid4()
        session = make_session(session_id=session_id, is_revoked=True)

        session_repo = AsyncMock()
        session_repo.get.return_value = session
        uow = make_uow()
        permission_resolver = AsyncMock()
        logger = make_logger()

        handler = LogoutHandler(
            session_repo=session_repo,
            uow=uow,
            permission_resolver=permission_resolver,
            logger=logger,
        )

        await handler.handle(LogoutCommand(session_id=session_id))

        # No update call because session was already revoked
        session_repo.update.assert_not_awaited()
        # Still invalidates cache
        permission_resolver.invalidate.assert_awaited_once_with(session_id)

    async def test_logout_handles_missing_session(self):
        session_id = uuid.uuid4()

        session_repo = AsyncMock()
        session_repo.get.return_value = None
        uow = make_uow()
        permission_resolver = AsyncMock()
        logger = make_logger()

        handler = LogoutHandler(
            session_repo=session_repo,
            uow=uow,
            permission_resolver=permission_resolver,
            logger=logger,
        )

        # Should not raise
        await handler.handle(LogoutCommand(session_id=session_id))

        session_repo.update.assert_not_awaited()
        permission_resolver.invalidate.assert_awaited_once_with(session_id)


# ===========================================================================
# 2. LogoutAllHandler
# ===========================================================================


class TestLogoutAllHandler:
    async def test_logout_all_revokes_and_invalidates_all(self):
        identity_id = uuid.uuid4()
        revoked_ids = [uuid.uuid4(), uuid.uuid4(), uuid.uuid4()]

        session_repo = AsyncMock()
        session_repo.revoke_all_for_identity.return_value = revoked_ids
        uow = make_uow()
        permission_resolver = AsyncMock()
        logger = make_logger()

        handler = LogoutAllHandler(
            session_repo=session_repo,
            uow=uow,
            permission_resolver=permission_resolver,
            logger=logger,
        )

        await handler.handle(LogoutAllCommand(identity_id=identity_id))

        session_repo.revoke_all_for_identity.assert_awaited_once_with(identity_id)
        uow.commit.assert_awaited_once()
        assert permission_resolver.invalidate.await_count == 3
        for sid in revoked_ids:
            permission_resolver.invalidate.assert_any_await(sid)

    async def test_logout_all_no_sessions(self):
        identity_id = uuid.uuid4()

        session_repo = AsyncMock()
        session_repo.revoke_all_for_identity.return_value = []
        uow = make_uow()
        permission_resolver = AsyncMock()
        logger = make_logger()

        handler = LogoutAllHandler(
            session_repo=session_repo,
            uow=uow,
            permission_resolver=permission_resolver,
            logger=logger,
        )

        await handler.handle(LogoutAllCommand(identity_id=identity_id))

        uow.commit.assert_awaited_once()
        permission_resolver.invalidate.assert_not_awaited()


# ===========================================================================
# 3. RefreshTokenHandler
# ===========================================================================


class TestRefreshTokenHandler:
    async def test_refresh_token_success(self):
        raw_token = "original-refresh-token"
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        identity_id = uuid.uuid4()
        session = make_session(
            identity_id=identity_id,
            refresh_token_hash=token_hash,
        )
        identity = make_identity(identity_id=identity_id, is_active=True)

        session_repo = AsyncMock()
        session_repo.get_by_refresh_token_hash.return_value = session
        identity_repo = AsyncMock()
        identity_repo.get.return_value = identity
        uow = make_uow()
        token_provider = MagicMock()
        token_provider.create_refresh_token.return_value = ("new-raw-token", "new-hash")
        token_provider.create_access_token.return_value = "new-access-token"
        permission_resolver = AsyncMock()
        logger = make_logger()

        handler = RefreshTokenHandler(
            session_repo=session_repo,
            identity_repo=identity_repo,
            uow=uow,
            token_provider=token_provider,
            permission_resolver=permission_resolver,
            logger=logger,
        )

        result = await handler.handle(
            RefreshTokenCommand(
                refresh_token=raw_token,
                ip_address="127.0.0.1",
                user_agent="test",
            )
        )

        assert isinstance(result, RefreshTokenResult)
        assert result.access_token == "new-access-token"
        assert result.refresh_token == "new-raw-token"
        session_repo.update.assert_awaited_once_with(session)
        uow.commit.assert_awaited_once()

    async def test_refresh_token_reuse_detected(self):
        raw_token = "reused-token"
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

        session_repo = AsyncMock()
        session_repo.get_by_refresh_token_hash.return_value = None
        identity_repo = AsyncMock()
        uow = make_uow()
        token_provider = MagicMock()
        permission_resolver = AsyncMock()
        logger = make_logger()

        handler = RefreshTokenHandler(
            session_repo=session_repo,
            identity_repo=identity_repo,
            uow=uow,
            token_provider=token_provider,
            permission_resolver=permission_resolver,
            logger=logger,
        )

        with pytest.raises(RefreshTokenReuseError):
            await handler.handle(
                RefreshTokenCommand(
                    refresh_token=raw_token,
                    ip_address="127.0.0.1",
                    user_agent="test",
                )
            )

    async def test_refresh_token_expired_session(self):
        raw_token = "expired-session-token"
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        session = make_session(
            refresh_token_hash=token_hash,
            is_expired=True,
        )

        session_repo = AsyncMock()
        session_repo.get_by_refresh_token_hash.return_value = session
        identity_repo = AsyncMock()
        uow = make_uow()
        token_provider = MagicMock()
        permission_resolver = AsyncMock()
        logger = make_logger()

        handler = RefreshTokenHandler(
            session_repo=session_repo,
            identity_repo=identity_repo,
            uow=uow,
            token_provider=token_provider,
            permission_resolver=permission_resolver,
            logger=logger,
        )

        with pytest.raises(SessionExpiredError):
            await handler.handle(
                RefreshTokenCommand(
                    refresh_token=raw_token,
                    ip_address="127.0.0.1",
                    user_agent="test",
                )
            )

    async def test_refresh_token_deactivated_identity(self):
        raw_token = "deactivated-token"
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        identity_id = uuid.uuid4()
        session = make_session(
            identity_id=identity_id,
            refresh_token_hash=token_hash,
        )
        identity = make_identity(identity_id=identity_id, is_active=False)

        session_repo = AsyncMock()
        session_repo.get_by_refresh_token_hash.return_value = session
        identity_repo = AsyncMock()
        identity_repo.get.return_value = identity
        uow = make_uow()
        token_provider = MagicMock()
        permission_resolver = AsyncMock()
        logger = make_logger()

        handler = RefreshTokenHandler(
            session_repo=session_repo,
            identity_repo=identity_repo,
            uow=uow,
            token_provider=token_provider,
            permission_resolver=permission_resolver,
            logger=logger,
        )

        with pytest.raises(IdentityDeactivatedError):
            await handler.handle(
                RefreshTokenCommand(
                    refresh_token=raw_token,
                    ip_address="127.0.0.1",
                    user_agent="test",
                )
            )


# ===========================================================================
# 4. AssignRoleHandler
# ===========================================================================


class TestAssignRoleHandler:
    async def test_assign_role_success(self):
        identity_id = uuid.uuid4()
        role_id = uuid.uuid4()
        assigned_by = uuid.uuid4()
        identity = make_identity(identity_id=identity_id)
        role = make_role(role_id=role_id, name="editor")
        active_session_ids = [uuid.uuid4(), uuid.uuid4()]

        identity_repo = AsyncMock()
        identity_repo.get.return_value = identity
        role_repo = AsyncMock()
        role_repo.get.return_value = role
        session_repo = AsyncMock()
        session_repo.get_active_session_ids.return_value = active_session_ids
        uow = make_uow()
        logger = make_logger()

        handler = AssignRoleHandler(
            identity_repo=identity_repo,
            role_repo=role_repo,
            session_repo=session_repo,
            uow=uow,
            logger=logger,
        )

        await handler.handle(
            AssignRoleCommand(
                identity_id=identity_id,
                role_id=role_id,
                assigned_by=assigned_by,
            )
        )

        # Verify role assignment
        role_repo.assign_to_identity.assert_awaited_once_with(
            identity_id=identity_id,
            role_id=role_id,
            assigned_by=assigned_by,
        )

        # Session roles updated for each active session
        assert session_repo.add_session_roles.await_count == 2
        for sid in active_session_ids:
            session_repo.add_session_roles.assert_any_await(sid, [role_id])

        # Domain event emitted
        events = identity.domain_events
        assert len(events) == 1
        assert isinstance(events[0], RoleAssignmentChangedEvent)
        assert events[0].action == "assigned"
        assert events[0].identity_id == identity_id
        assert events[0].role_id == role_id

        # Aggregate registered and committed
        uow.register_aggregate.assert_called_once_with(identity)
        uow.commit.assert_awaited_once()

    async def test_assign_role_identity_not_found(self):
        identity_id = uuid.uuid4()
        role_id = uuid.uuid4()

        identity_repo = AsyncMock()
        identity_repo.get.return_value = None
        role_repo = AsyncMock()
        session_repo = AsyncMock()
        uow = make_uow()
        logger = make_logger()

        handler = AssignRoleHandler(
            identity_repo=identity_repo,
            role_repo=role_repo,
            session_repo=session_repo,
            uow=uow,
            logger=logger,
        )

        with pytest.raises(NotFoundError) as exc_info:
            await handler.handle(AssignRoleCommand(identity_id=identity_id, role_id=role_id))

        assert exc_info.value.error_code == "IDENTITY_NOT_FOUND"

    async def test_assign_role_role_not_found(self):
        identity_id = uuid.uuid4()
        role_id = uuid.uuid4()
        identity = make_identity(identity_id=identity_id)

        identity_repo = AsyncMock()
        identity_repo.get.return_value = identity
        role_repo = AsyncMock()
        role_repo.get.return_value = None
        session_repo = AsyncMock()
        uow = make_uow()
        logger = make_logger()

        handler = AssignRoleHandler(
            identity_repo=identity_repo,
            role_repo=role_repo,
            session_repo=session_repo,
            uow=uow,
            logger=logger,
        )

        with pytest.raises(NotFoundError) as exc_info:
            await handler.handle(AssignRoleCommand(identity_id=identity_id, role_id=role_id))

        assert exc_info.value.error_code == "ROLE_NOT_FOUND"


# ===========================================================================
# 5. CreateRoleHandler
# ===========================================================================


class TestCreateRoleHandler:
    async def test_create_role_success(self):
        role_repo = AsyncMock()
        role_repo.get_by_name.return_value = None
        uow = make_uow()
        logger = make_logger()

        handler = CreateRoleHandler(
            role_repo=role_repo,
            uow=uow,
            logger=logger,
        )

        result = await handler.handle(
            CreateRoleCommand(name="editor", description="Can edit content")
        )

        assert isinstance(result, CreateRoleResult)
        assert isinstance(result.role_id, uuid.UUID)
        role_repo.add.assert_awaited_once()
        added_role = role_repo.add.call_args[0][0]
        assert added_role.name == "editor"
        assert added_role.description == "Can edit content"
        assert added_role.is_system is False
        uow.commit.assert_awaited_once()

    async def test_create_role_duplicate_name(self):
        existing_role = make_role(name="editor")

        role_repo = AsyncMock()
        role_repo.get_by_name.return_value = existing_role
        uow = make_uow()
        logger = make_logger()

        handler = CreateRoleHandler(
            role_repo=role_repo,
            uow=uow,
            logger=logger,
        )

        with pytest.raises(ConflictError) as exc_info:
            await handler.handle(CreateRoleCommand(name="editor"))

        assert exc_info.value.error_code == "ROLE_ALREADY_EXISTS"


# ===========================================================================
# 6. DeleteRoleHandler
# ===========================================================================


class TestDeleteRoleHandler:
    async def test_delete_role_success(self):
        role_id = uuid.uuid4()
        role = make_role(role_id=role_id, name="temp-role", is_system=False)

        role_repo = AsyncMock()
        role_repo.get.return_value = role
        uow = make_uow()
        logger = make_logger()

        handler = DeleteRoleHandler(
            role_repo=role_repo,
            uow=uow,
            logger=logger,
        )

        await handler.handle(DeleteRoleCommand(role_id=role_id))

        role_repo.delete.assert_awaited_once_with(role_id)
        uow.commit.assert_awaited_once()

    async def test_delete_role_not_found(self):
        role_id = uuid.uuid4()

        role_repo = AsyncMock()
        role_repo.get.return_value = None
        uow = make_uow()
        logger = make_logger()

        handler = DeleteRoleHandler(
            role_repo=role_repo,
            uow=uow,
            logger=logger,
        )

        with pytest.raises(NotFoundError) as exc_info:
            await handler.handle(DeleteRoleCommand(role_id=role_id))

        assert exc_info.value.error_code == "ROLE_NOT_FOUND"

    async def test_delete_role_system_role(self):
        role_id = uuid.uuid4()
        role = make_role(role_id=role_id, name="super_admin", is_system=True)

        role_repo = AsyncMock()
        role_repo.get.return_value = role
        uow = make_uow()
        logger = make_logger()

        handler = DeleteRoleHandler(
            role_repo=role_repo,
            uow=uow,
            logger=logger,
        )

        with pytest.raises(SystemRoleModificationError):
            await handler.handle(DeleteRoleCommand(role_id=role_id))

        # Should NOT have called delete
        role_repo.delete.assert_not_awaited()


# ===========================================================================
# 7. RevokeRoleHandler
# ===========================================================================


class TestRevokeRoleHandler:
    async def test_revoke_role_success(self):
        identity_id = uuid.uuid4()
        role_id = uuid.uuid4()
        identity = make_identity(identity_id=identity_id)
        active_session_ids = [uuid.uuid4(), uuid.uuid4()]

        identity_repo = AsyncMock()
        identity_repo.get.return_value = identity
        role_repo = AsyncMock()
        session_repo = AsyncMock()
        session_repo.get_active_session_ids.return_value = active_session_ids
        uow = make_uow()
        logger = make_logger()

        handler = RevokeRoleHandler(
            identity_repo=identity_repo,
            role_repo=role_repo,
            session_repo=session_repo,
            uow=uow,
            logger=logger,
        )

        await handler.handle(RevokeRoleCommand(identity_id=identity_id, role_id=role_id))

        # Role revoked from identity
        role_repo.revoke_from_identity.assert_awaited_once_with(
            identity_id=identity_id,
            role_id=role_id,
        )

        # Session roles removed for each active session
        assert session_repo.remove_session_role.await_count == 2
        for sid in active_session_ids:
            session_repo.remove_session_role.assert_any_await(sid, role_id)

        # Domain event emitted
        events = identity.domain_events
        assert len(events) == 1
        assert isinstance(events[0], RoleAssignmentChangedEvent)
        assert events[0].action == "revoked"
        assert events[0].identity_id == identity_id
        assert events[0].role_id == role_id

        uow.register_aggregate.assert_called_once_with(identity)
        uow.commit.assert_awaited_once()

    async def test_revoke_role_identity_not_found_returns_silently(self):
        identity_id = uuid.uuid4()
        role_id = uuid.uuid4()

        identity_repo = AsyncMock()
        identity_repo.get.return_value = None
        role_repo = AsyncMock()
        session_repo = AsyncMock()
        uow = make_uow()
        logger = make_logger()

        handler = RevokeRoleHandler(
            identity_repo=identity_repo,
            role_repo=role_repo,
            session_repo=session_repo,
            uow=uow,
            logger=logger,
        )

        # Should return silently without error
        await handler.handle(RevokeRoleCommand(identity_id=identity_id, role_id=role_id))

        role_repo.revoke_from_identity.assert_not_awaited()
        uow.commit.assert_not_awaited()


# ===========================================================================
# 8. DeactivateIdentityHandler
# ===========================================================================


class TestDeactivateIdentityHandler:
    async def test_deactivate_success(self):
        identity_id = uuid.uuid4()
        identity = make_identity(identity_id=identity_id, is_active=True)
        revoked_ids = [uuid.uuid4(), uuid.uuid4()]

        identity_repo = AsyncMock()
        identity_repo.get.return_value = identity
        session_repo = AsyncMock()
        session_repo.revoke_all_for_identity.return_value = revoked_ids
        uow = make_uow()
        permission_resolver = AsyncMock()
        logger = make_logger()

        handler = DeactivateIdentityHandler(
            identity_repo=identity_repo,
            session_repo=session_repo,
            uow=uow,
            permission_resolver=permission_resolver,
            logger=logger,
        )

        await handler.handle(
            DeactivateIdentityCommand(identity_id=identity_id, reason="admin_action")
        )

        # Identity deactivated
        assert identity.is_active is False

        # Sessions revoked
        session_repo.revoke_all_for_identity.assert_awaited_once_with(identity_id)

        # Aggregate registered and committed
        uow.register_aggregate.assert_called_once_with(identity)
        uow.commit.assert_awaited_once()

        # Permissions cache invalidated for all revoked sessions
        assert permission_resolver.invalidate.await_count == 2
        for sid in revoked_ids:
            permission_resolver.invalidate.assert_any_await(sid)

    async def test_deactivate_identity_not_found_returns_silently(self):
        identity_id = uuid.uuid4()

        identity_repo = AsyncMock()
        identity_repo.get.return_value = None
        session_repo = AsyncMock()
        uow = make_uow()
        permission_resolver = AsyncMock()
        logger = make_logger()

        handler = DeactivateIdentityHandler(
            identity_repo=identity_repo,
            session_repo=session_repo,
            uow=uow,
            permission_resolver=permission_resolver,
            logger=logger,
        )

        # Should return silently
        await handler.handle(DeactivateIdentityCommand(identity_id=identity_id))

        session_repo.revoke_all_for_identity.assert_not_awaited()
        uow.commit.assert_not_awaited()
        permission_resolver.invalidate.assert_not_awaited()


# ===========================================================================
# 9. LoginOIDCHandler
# ===========================================================================


class TestLoginOIDCHandler:
    def _make_handler(
        self,
        oidc_provider=None,
        identity_repo=None,
        linked_account_repo=None,
        session_repo=None,
        role_repo=None,
        uow=None,
        token_provider=None,
        logger=None,
    ):
        return LoginOIDCHandler(
            oidc_provider=oidc_provider or AsyncMock(),
            identity_repo=identity_repo or AsyncMock(),
            linked_account_repo=linked_account_repo or AsyncMock(),
            session_repo=session_repo or AsyncMock(),
            role_repo=role_repo or AsyncMock(),
            uow=uow or make_uow(),
            token_provider=token_provider or MagicMock(),
            logger=logger or make_logger(),
        )

    async def test_login_oidc_existing_identity(self):
        identity_id = uuid.uuid4()
        identity = make_identity(
            identity_id=identity_id, is_active=True, identity_type=IdentityType.OIDC
        )
        linked = LinkedAccount(
            id=uuid.uuid4(),
            identity_id=identity_id,
            provider="google",
            provider_sub_id="google-sub-123",
            provider_email="user@example.com",
        )
        user_info = OIDCUserInfo(provider="google", sub="google-sub-123", email="user@example.com")
        role_ids = [uuid.uuid4()]

        oidc_provider = AsyncMock()
        oidc_provider.validate_token.return_value = user_info
        identity_repo = AsyncMock()
        identity_repo.get.return_value = identity
        linked_account_repo = AsyncMock()
        linked_account_repo.get_by_provider.return_value = linked
        session_repo = AsyncMock()
        role_repo = AsyncMock()
        role_repo.get_identity_role_ids.return_value = role_ids
        uow = make_uow()
        token_provider = MagicMock()
        token_provider.create_refresh_token.return_value = (
            "raw-refresh",
            "refresh-hash",
        )
        token_provider.create_access_token.return_value = "access-token-123"
        logger = make_logger()

        handler = self._make_handler(
            oidc_provider=oidc_provider,
            identity_repo=identity_repo,
            linked_account_repo=linked_account_repo,
            session_repo=session_repo,
            role_repo=role_repo,
            uow=uow,
            token_provider=token_provider,
            logger=logger,
        )

        result = await handler.handle(
            LoginOIDCCommand(
                provider_token="oidc-token",
                ip_address="10.0.0.1",
                user_agent="browser",
            )
        )

        assert isinstance(result, LoginOIDCResult)
        assert result.access_token == "access-token-123"
        assert result.refresh_token == "raw-refresh"
        assert result.identity_id == identity_id
        assert result.is_new_identity is False

        # Should NOT create new identity or linked account
        identity_repo.add.assert_not_awaited()
        linked_account_repo.add.assert_not_awaited()

        # Session created
        session_repo.add.assert_awaited_once()
        session_repo.add_session_roles.assert_awaited_once()
        uow.commit.assert_awaited_once()

    async def test_login_oidc_new_identity(self):
        user_info = OIDCUserInfo(provider="google", sub="new-sub-456", email="new@example.com")
        customer_role = make_role(name="customer")
        role_ids = [customer_role.id]

        oidc_provider = AsyncMock()
        oidc_provider.validate_token.return_value = user_info
        identity_repo = AsyncMock()
        linked_account_repo = AsyncMock()
        linked_account_repo.get_by_provider.return_value = None
        session_repo = AsyncMock()
        role_repo = AsyncMock()
        role_repo.get_by_name.return_value = customer_role
        role_repo.get_identity_role_ids.return_value = role_ids
        uow = make_uow()
        token_provider = MagicMock()
        token_provider.create_refresh_token.return_value = (
            "raw-refresh",
            "refresh-hash",
        )
        token_provider.create_access_token.return_value = "access-token-new"
        logger = make_logger()

        handler = self._make_handler(
            oidc_provider=oidc_provider,
            identity_repo=identity_repo,
            linked_account_repo=linked_account_repo,
            session_repo=session_repo,
            role_repo=role_repo,
            uow=uow,
            token_provider=token_provider,
            logger=logger,
        )

        result = await handler.handle(
            LoginOIDCCommand(
                provider_token="oidc-token",
                ip_address="10.0.0.1",
                user_agent="browser",
            )
        )

        assert isinstance(result, LoginOIDCResult)
        assert result.is_new_identity is True
        assert result.access_token == "access-token-new"
        assert result.refresh_token == "raw-refresh"

        # New identity created
        identity_repo.add.assert_awaited_once()
        created_identity = identity_repo.add.call_args[0][0]
        assert isinstance(created_identity, Identity)
        assert created_identity.type == IdentityType.OIDC
        assert created_identity.is_active is True

        # Linked account created
        linked_account_repo.add.assert_awaited_once()
        created_linked = linked_account_repo.add.call_args[0][0]
        assert isinstance(created_linked, LinkedAccount)
        assert created_linked.provider == "google"
        assert created_linked.provider_sub_id == "new-sub-456"
        assert created_linked.provider_email == "new@example.com"

        # Customer role assigned
        role_repo.assign_to_identity.assert_awaited_once()

        # IdentityRegisteredEvent emitted
        events = created_identity.domain_events
        assert len(events) == 1
        assert isinstance(events[0], IdentityRegisteredEvent)
        assert events[0].email == "new@example.com"

        # Aggregate registered
        uow.register_aggregate.assert_called_once_with(created_identity)
        uow.commit.assert_awaited_once()

    async def test_login_oidc_existing_identity_deactivated(self):
        identity_id = uuid.uuid4()
        identity = make_identity(
            identity_id=identity_id, is_active=False, identity_type=IdentityType.OIDC
        )
        linked = LinkedAccount(
            id=uuid.uuid4(),
            identity_id=identity_id,
            provider="google",
            provider_sub_id="sub-deactivated",
            provider_email="deactivated@example.com",
        )
        user_info = OIDCUserInfo(
            provider="google", sub="sub-deactivated", email="deactivated@example.com"
        )

        oidc_provider = AsyncMock()
        oidc_provider.validate_token.return_value = user_info
        identity_repo = AsyncMock()
        identity_repo.get.return_value = identity
        linked_account_repo = AsyncMock()
        linked_account_repo.get_by_provider.return_value = linked
        uow = make_uow()
        logger = make_logger()

        handler = self._make_handler(
            oidc_provider=oidc_provider,
            identity_repo=identity_repo,
            linked_account_repo=linked_account_repo,
            uow=uow,
            logger=logger,
        )

        with pytest.raises(IdentityDeactivatedError):
            await handler.handle(
                LoginOIDCCommand(
                    provider_token="oidc-token",
                    ip_address="10.0.0.1",
                    user_agent="browser",
                )
            )

    async def test_login_oidc_linked_but_identity_missing(self):
        identity_id = uuid.uuid4()
        linked = LinkedAccount(
            id=uuid.uuid4(),
            identity_id=identity_id,
            provider="google",
            provider_sub_id="sub-orphan",
            provider_email="orphan@example.com",
        )
        user_info = OIDCUserInfo(provider="google", sub="sub-orphan", email="orphan@example.com")

        oidc_provider = AsyncMock()
        oidc_provider.validate_token.return_value = user_info
        identity_repo = AsyncMock()
        identity_repo.get.return_value = None  # Identity missing
        linked_account_repo = AsyncMock()
        linked_account_repo.get_by_provider.return_value = linked
        uow = make_uow()
        logger = make_logger()

        handler = self._make_handler(
            oidc_provider=oidc_provider,
            identity_repo=identity_repo,
            linked_account_repo=linked_account_repo,
            uow=uow,
            logger=logger,
        )

        with pytest.raises(InvalidCredentialsError):
            await handler.handle(
                LoginOIDCCommand(
                    provider_token="oidc-token",
                    ip_address="10.0.0.1",
                    user_agent="browser",
                )
            )
