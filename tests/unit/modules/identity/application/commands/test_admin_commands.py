"""Unit tests for admin RBAC command handlers.

Tests cover AdminDeactivateIdentityHandler, ReactivateIdentityHandler,
UpdateRoleHandler, and SetRolePermissionsHandler with all security guards.
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.modules.identity.application.commands.admin_deactivate_identity import (
    AdminDeactivateIdentityCommand,
    AdminDeactivateIdentityHandler,
)
from src.modules.identity.application.commands.reactivate_identity import (
    ReactivateIdentityCommand,
    ReactivateIdentityHandler,
)
from src.modules.identity.application.commands.set_role_permissions import (
    SetRolePermissionsCommand,
    SetRolePermissionsHandler,
)
from src.modules.identity.application.commands.update_role import (
    UpdateRoleCommand,
    UpdateRoleHandler,
)
from src.modules.identity.domain.entities import Identity, Permission, Role
from src.modules.identity.domain.events import (
    IdentityDeactivatedEvent,
    IdentityReactivatedEvent,
)
from src.modules.identity.domain.exceptions import (
    IdentityAlreadyActiveError,
    IdentityAlreadyDeactivatedError,
    LastAdminProtectionError,
    PrivilegeEscalationError,
    SelfDeactivationError,
    SystemRoleModificationError,
)
from src.modules.identity.domain.value_objects import IdentityType
from src.shared.exceptions import ConflictError, NotFoundError

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_uow() -> AsyncMock:
    uow = AsyncMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=False)
    uow.register_aggregate = MagicMock()
    return uow


def make_logger() -> MagicMock:
    logger = MagicMock()
    logger.bind = MagicMock(return_value=logger)
    logger.info = MagicMock()
    logger.warning = MagicMock()
    return logger


def make_identity(
    identity_id: uuid.UUID | None = None,
    is_active: bool = True,
) -> Identity:
    iid = identity_id or uuid.uuid4()
    return Identity(
        id=iid,
        type=IdentityType.LOCAL,
        is_active=is_active,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def make_role(
    role_id: uuid.UUID | None = None,
    name: str = "editor",
    is_system: bool = False,
    description: str | None = None,
) -> Role:
    return Role(
        id=role_id or uuid.uuid4(),
        name=name,
        description=description,
        is_system=is_system,
    )


def make_permission(
    permission_id: uuid.UUID | None = None,
    codename: str = "brands:create",
    resource: str = "brands",
    action: str = "create",
) -> Permission:
    return Permission(
        id=permission_id or uuid.uuid4(),
        codename=codename,
        resource=resource,
        action=action,
    )


# ===========================================================================
# AdminDeactivateIdentityHandler
# ===========================================================================


class TestAdminDeactivateIdentityHandler:
    def _make_handler(
        self,
        identity_repo: AsyncMock | None = None,
        role_repo: AsyncMock | None = None,
        session_repo: AsyncMock | None = None,
        uow: AsyncMock | None = None,
        permission_resolver: AsyncMock | None = None,
        logger: MagicMock | None = None,
    ) -> AdminDeactivateIdentityHandler:
        return AdminDeactivateIdentityHandler(
            identity_repo=identity_repo or AsyncMock(),
            role_repo=role_repo or AsyncMock(),
            session_repo=session_repo or AsyncMock(),
            uow=uow or make_uow(),
            permission_resolver=permission_resolver or AsyncMock(),
            logger=logger or make_logger(),
        )

    async def test_admin_deactivate_success(self) -> None:
        identity_id = uuid.uuid4()
        admin_id = uuid.uuid4()
        identity = make_identity(identity_id=identity_id, is_active=True)
        revoked_ids = [uuid.uuid4(), uuid.uuid4()]

        identity_repo = AsyncMock()
        identity_repo.get.return_value = identity
        role_repo = AsyncMock()
        role_repo.get_identity_role_ids.return_value = []
        session_repo = AsyncMock()
        session_repo.revoke_all_for_identity.return_value = revoked_ids
        uow = make_uow()
        permission_resolver = AsyncMock()
        logger = make_logger()

        handler = self._make_handler(
            identity_repo=identity_repo,
            role_repo=role_repo,
            session_repo=session_repo,
            uow=uow,
            permission_resolver=permission_resolver,
            logger=logger,
        )

        command = AdminDeactivateIdentityCommand(
            identity_id=identity_id,
            reason="policy violation",
            deactivated_by=admin_id,
        )
        await handler.handle(command)

        assert identity.is_active is False
        assert identity.deactivated_by == admin_id
        assert identity.deactivated_at is not None
        identity_repo.update.assert_awaited_once_with(identity)
        session_repo.revoke_all_for_identity.assert_awaited_once_with(identity_id)
        uow.register_aggregate.assert_called_once_with(identity)
        uow.commit.assert_awaited_once()
        assert permission_resolver.invalidate.await_count == 2

    async def test_admin_deactivate_identity_not_found(self) -> None:
        identity_repo = AsyncMock()
        identity_repo.get.return_value = None

        handler = self._make_handler(identity_repo=identity_repo, uow=make_uow())

        with pytest.raises(NotFoundError) as exc_info:
            await handler.handle(
                AdminDeactivateIdentityCommand(
                    identity_id=uuid.uuid4(),
                    reason="test",
                    deactivated_by=uuid.uuid4(),
                )
            )

        assert exc_info.value.error_code == "IDENTITY_NOT_FOUND"

    async def test_admin_deactivate_already_deactivated(self) -> None:
        identity = make_identity(is_active=False)

        identity_repo = AsyncMock()
        identity_repo.get.return_value = identity

        handler = self._make_handler(identity_repo=identity_repo, uow=make_uow())

        with pytest.raises(IdentityAlreadyDeactivatedError):
            await handler.handle(
                AdminDeactivateIdentityCommand(
                    identity_id=identity.id,
                    reason="test",
                    deactivated_by=uuid.uuid4(),
                )
            )

    async def test_admin_deactivate_self(self) -> None:
        identity_id = uuid.uuid4()
        identity = make_identity(identity_id=identity_id, is_active=True)

        identity_repo = AsyncMock()
        identity_repo.get.return_value = identity

        handler = self._make_handler(identity_repo=identity_repo, uow=make_uow())

        with pytest.raises(SelfDeactivationError):
            await handler.handle(
                AdminDeactivateIdentityCommand(
                    identity_id=identity_id,
                    reason="test",
                    deactivated_by=identity_id,
                )
            )

    async def test_admin_deactivate_last_admin(self) -> None:
        identity_id = uuid.uuid4()
        identity = make_identity(identity_id=identity_id, is_active=True)
        admin_role = make_role(name="admin", is_system=True)

        identity_repo = AsyncMock()
        identity_repo.get.return_value = identity
        role_repo = AsyncMock()
        role_repo.get_identity_role_ids.return_value = [admin_role.id]
        role_repo.get.return_value = admin_role
        role_repo.count_identities_with_role.return_value = 1

        handler = self._make_handler(
            identity_repo=identity_repo,
            role_repo=role_repo,
            uow=make_uow(),
        )

        with pytest.raises(LastAdminProtectionError):
            await handler.handle(
                AdminDeactivateIdentityCommand(
                    identity_id=identity_id,
                    reason="test",
                    deactivated_by=uuid.uuid4(),
                )
            )

    async def test_admin_deactivate_not_last_admin_succeeds(self) -> None:
        """If there are 2+ admins, deactivation is allowed."""
        identity_id = uuid.uuid4()
        identity = make_identity(identity_id=identity_id, is_active=True)
        admin_role = make_role(name="admin", is_system=True)

        identity_repo = AsyncMock()
        identity_repo.get.return_value = identity
        role_repo = AsyncMock()
        role_repo.get_identity_role_ids.return_value = [admin_role.id]
        role_repo.get.return_value = admin_role
        role_repo.count_identities_with_role.return_value = 3
        session_repo = AsyncMock()
        session_repo.revoke_all_for_identity.return_value = []

        handler = self._make_handler(
            identity_repo=identity_repo,
            role_repo=role_repo,
            session_repo=session_repo,
            uow=make_uow(),
        )

        await handler.handle(
            AdminDeactivateIdentityCommand(
                identity_id=identity_id,
                reason="test",
                deactivated_by=uuid.uuid4(),
            )
        )

        assert identity.is_active is False

    async def test_admin_deactivate_revokes_sessions_and_invalidates_cache(self) -> None:
        identity_id = uuid.uuid4()
        identity = make_identity(identity_id=identity_id, is_active=True)
        revoked_ids = [uuid.uuid4(), uuid.uuid4(), uuid.uuid4()]

        identity_repo = AsyncMock()
        identity_repo.get.return_value = identity
        role_repo = AsyncMock()
        role_repo.get_identity_role_ids.return_value = []
        session_repo = AsyncMock()
        session_repo.revoke_all_for_identity.return_value = revoked_ids
        permission_resolver = AsyncMock()

        handler = self._make_handler(
            identity_repo=identity_repo,
            role_repo=role_repo,
            session_repo=session_repo,
            permission_resolver=permission_resolver,
            uow=make_uow(),
        )

        await handler.handle(
            AdminDeactivateIdentityCommand(
                identity_id=identity_id,
                reason="test",
                deactivated_by=uuid.uuid4(),
            )
        )

        assert permission_resolver.invalidate.await_count == 3
        for sid in revoked_ids:
            permission_resolver.invalidate.assert_any_await(sid)

    async def test_admin_deactivate_emits_event_with_deactivated_by(self) -> None:
        identity_id = uuid.uuid4()
        admin_id = uuid.uuid4()
        identity = make_identity(identity_id=identity_id, is_active=True)

        identity_repo = AsyncMock()
        identity_repo.get.return_value = identity
        role_repo = AsyncMock()
        role_repo.get_identity_role_ids.return_value = []
        session_repo = AsyncMock()
        session_repo.revoke_all_for_identity.return_value = []

        handler = self._make_handler(
            identity_repo=identity_repo,
            role_repo=role_repo,
            session_repo=session_repo,
            uow=make_uow(),
        )

        await handler.handle(
            AdminDeactivateIdentityCommand(
                identity_id=identity_id,
                reason="policy",
                deactivated_by=admin_id,
            )
        )

        events = identity.domain_events
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, IdentityDeactivatedEvent)
        assert event.deactivated_by == admin_id
        assert event.identity_id == identity_id
        assert event.reason == "policy"


# ===========================================================================
# ReactivateIdentityHandler
# ===========================================================================


class TestReactivateIdentityHandler:
    def _make_handler(
        self,
        identity_repo: AsyncMock | None = None,
        uow: AsyncMock | None = None,
        logger: MagicMock | None = None,
    ) -> ReactivateIdentityHandler:
        return ReactivateIdentityHandler(
            identity_repo=identity_repo or AsyncMock(),
            uow=uow or make_uow(),
            logger=logger or make_logger(),
        )

    async def test_reactivate_success(self) -> None:
        identity_id = uuid.uuid4()
        admin_id = uuid.uuid4()
        identity = make_identity(identity_id=identity_id, is_active=False)

        identity_repo = AsyncMock()
        identity_repo.get.return_value = identity
        uow = make_uow()

        handler = self._make_handler(identity_repo=identity_repo, uow=uow)

        await handler.handle(
            ReactivateIdentityCommand(identity_id=identity_id, reactivated_by=admin_id)
        )

        assert identity.is_active is True
        assert identity.deactivated_at is None
        assert identity.deactivated_by is None
        identity_repo.update.assert_awaited_once_with(identity)
        uow.register_aggregate.assert_called_once_with(identity)
        uow.commit.assert_awaited_once()

    async def test_reactivate_identity_not_found(self) -> None:
        identity_repo = AsyncMock()
        identity_repo.get.return_value = None

        handler = self._make_handler(identity_repo=identity_repo, uow=make_uow())

        with pytest.raises(NotFoundError) as exc_info:
            await handler.handle(
                ReactivateIdentityCommand(identity_id=uuid.uuid4(), reactivated_by=uuid.uuid4())
            )

        assert exc_info.value.error_code == "IDENTITY_NOT_FOUND"

    async def test_reactivate_already_active(self) -> None:
        identity = make_identity(is_active=True)

        identity_repo = AsyncMock()
        identity_repo.get.return_value = identity

        handler = self._make_handler(identity_repo=identity_repo, uow=make_uow())

        with pytest.raises(IdentityAlreadyActiveError):
            await handler.handle(
                ReactivateIdentityCommand(identity_id=identity.id, reactivated_by=uuid.uuid4())
            )

    async def test_reactivate_emits_event(self) -> None:
        identity = make_identity(is_active=False)

        identity_repo = AsyncMock()
        identity_repo.get.return_value = identity

        handler = self._make_handler(identity_repo=identity_repo, uow=make_uow())

        await handler.handle(
            ReactivateIdentityCommand(identity_id=identity.id, reactivated_by=uuid.uuid4())
        )

        events = identity.domain_events
        assert len(events) == 1
        assert isinstance(events[0], IdentityReactivatedEvent)
        assert events[0].identity_id == identity.id


# ===========================================================================
# UpdateRoleHandler
# ===========================================================================


class TestUpdateRoleHandler:
    def _make_handler(
        self,
        role_repo: AsyncMock | None = None,
        uow: AsyncMock | None = None,
        logger: MagicMock | None = None,
    ) -> UpdateRoleHandler:
        return UpdateRoleHandler(
            role_repo=role_repo or AsyncMock(),
            uow=uow or make_uow(),
            logger=logger or make_logger(),
        )

    async def test_update_name_success(self) -> None:
        role = make_role(name="old_name", is_system=False)

        role_repo = AsyncMock()
        role_repo.get.return_value = role
        role_repo.get_by_name.return_value = None
        uow = make_uow()

        handler = self._make_handler(role_repo=role_repo, uow=uow)

        result = await handler.handle(UpdateRoleCommand(role_id=role.id, name="new_name"))

        assert role.name == "new_name"
        assert result.role_id == role.id
        role_repo.update.assert_awaited_once_with(role)
        uow.commit.assert_awaited_once()

    async def test_update_description_success(self) -> None:
        role = make_role(name="editor", description="Old desc")

        role_repo = AsyncMock()
        role_repo.get.return_value = role
        uow = make_uow()

        handler = self._make_handler(role_repo=role_repo, uow=uow)

        result = await handler.handle(
            UpdateRoleCommand(role_id=role.id, description="New description")
        )

        assert role.description == "New description"
        assert result.role_id == role.id
        role_repo.update.assert_awaited_once_with(role)

    async def test_update_role_not_found(self) -> None:
        role_repo = AsyncMock()
        role_repo.get.return_value = None

        handler = self._make_handler(role_repo=role_repo, uow=make_uow())

        with pytest.raises(NotFoundError) as exc_info:
            await handler.handle(UpdateRoleCommand(role_id=uuid.uuid4(), name="test"))

        assert exc_info.value.error_code == "ROLE_NOT_FOUND"

    async def test_update_system_role_name(self) -> None:
        role = make_role(name="admin", is_system=True)

        role_repo = AsyncMock()
        role_repo.get.return_value = role

        handler = self._make_handler(role_repo=role_repo, uow=make_uow())

        with pytest.raises(SystemRoleModificationError):
            await handler.handle(UpdateRoleCommand(role_id=role.id, name="new_name"))

    async def test_update_system_role_description_allowed(self) -> None:
        role = make_role(name="admin", is_system=True)

        role_repo = AsyncMock()
        role_repo.get.return_value = role
        uow = make_uow()

        handler = self._make_handler(role_repo=role_repo, uow=uow)

        result = await handler.handle(
            UpdateRoleCommand(role_id=role.id, description="Updated system role desc")
        )

        assert role.description == "Updated system role desc"
        assert result.role_id == role.id
        role_repo.update.assert_awaited_once()

    async def test_update_duplicate_name(self) -> None:
        role = make_role(name="editor")
        existing = make_role(name="admin")  # different role with the target name

        role_repo = AsyncMock()
        role_repo.get.return_value = role
        role_repo.get_by_name.return_value = existing

        handler = self._make_handler(role_repo=role_repo, uow=make_uow())

        with pytest.raises(ConflictError) as exc_info:
            await handler.handle(UpdateRoleCommand(role_id=role.id, name="admin"))

        assert exc_info.value.error_code == "ROLE_ALREADY_EXISTS"

    async def test_update_same_name_allowed(self) -> None:
        """Updating a role with the same name it already has should succeed."""
        role = make_role(name="editor")

        role_repo = AsyncMock()
        role_repo.get.return_value = role
        role_repo.get_by_name.return_value = role  # same role

        handler = self._make_handler(role_repo=role_repo, uow=make_uow())

        result = await handler.handle(UpdateRoleCommand(role_id=role.id, name="editor"))

        assert result.role_id == role.id


# ===========================================================================
# SetRolePermissionsHandler
# ===========================================================================


class TestSetRolePermissionsHandler:
    def _make_handler(
        self,
        role_repo: AsyncMock | None = None,
        permission_repo: AsyncMock | None = None,
        session_repo: AsyncMock | None = None,
        uow: AsyncMock | None = None,
        permission_resolver: AsyncMock | None = None,
        logger: MagicMock | None = None,
    ) -> SetRolePermissionsHandler:
        return SetRolePermissionsHandler(
            role_repo=role_repo or AsyncMock(),
            permission_repo=permission_repo or AsyncMock(),
            session_repo=session_repo or AsyncMock(),
            uow=uow or make_uow(),
            permission_resolver=permission_resolver or AsyncMock(),
            logger=logger or make_logger(),
        )

    async def test_set_permissions_success(self) -> None:
        role = make_role()
        perm1 = make_permission(codename="brands:create", resource="brands", action="create")
        perm2 = make_permission(codename="brands:read", resource="brands", action="read")
        admin_session_id = uuid.uuid4()

        role_repo = AsyncMock()
        role_repo.get.return_value = role
        role_repo.get_identity_ids_with_role.return_value = []
        permission_repo = AsyncMock()
        permission_repo.get_by_ids.return_value = [perm1, perm2]
        permission_resolver = AsyncMock()
        permission_resolver.get_permissions.return_value = frozenset(
            {"brands:create", "brands:read", "roles:manage"}
        )
        uow = make_uow()

        handler = self._make_handler(
            role_repo=role_repo,
            permission_repo=permission_repo,
            permission_resolver=permission_resolver,
            uow=uow,
        )

        await handler.handle(
            SetRolePermissionsCommand(
                role_id=role.id,
                permission_ids=[perm1.id, perm2.id],
                session_id=admin_session_id,
            )
        )

        role_repo.set_permissions.assert_awaited_once_with(role.id, [perm1.id, perm2.id])
        uow.commit.assert_awaited_once()

    async def test_set_permissions_role_not_found(self) -> None:
        role_repo = AsyncMock()
        role_repo.get.return_value = None

        handler = self._make_handler(role_repo=role_repo, uow=make_uow())

        with pytest.raises(NotFoundError) as exc_info:
            await handler.handle(
                SetRolePermissionsCommand(
                    role_id=uuid.uuid4(),
                    permission_ids=[uuid.uuid4()],
                    session_id=uuid.uuid4(),
                )
            )

        assert exc_info.value.error_code == "ROLE_NOT_FOUND"

    async def test_set_permissions_permission_not_found(self) -> None:
        role = make_role()
        perm1 = make_permission()
        missing_id = uuid.uuid4()

        role_repo = AsyncMock()
        role_repo.get.return_value = role
        permission_repo = AsyncMock()
        permission_repo.get_by_ids.return_value = [perm1]  # Only 1 of 2 found

        handler = self._make_handler(
            role_repo=role_repo,
            permission_repo=permission_repo,
            uow=make_uow(),
        )

        with pytest.raises(NotFoundError) as exc_info:
            await handler.handle(
                SetRolePermissionsCommand(
                    role_id=role.id,
                    permission_ids=[perm1.id, missing_id],
                    session_id=uuid.uuid4(),
                )
            )

        assert exc_info.value.error_code == "PERMISSION_NOT_FOUND"
        assert str(missing_id) in exc_info.value.details["missing_ids"]

    async def test_set_permissions_privilege_escalation(self) -> None:
        role = make_role()
        perm_admin_only = make_permission(
            codename="identities:manage", resource="identities", action="manage"
        )

        role_repo = AsyncMock()
        role_repo.get.return_value = role
        permission_repo = AsyncMock()
        permission_repo.get_by_ids.return_value = [perm_admin_only]
        permission_resolver = AsyncMock()
        # Admin only has brands:create, not identities:manage
        permission_resolver.get_permissions.return_value = frozenset({"brands:create"})

        handler = self._make_handler(
            role_repo=role_repo,
            permission_repo=permission_repo,
            permission_resolver=permission_resolver,
            uow=make_uow(),
        )

        with pytest.raises(PrivilegeEscalationError):
            await handler.handle(
                SetRolePermissionsCommand(
                    role_id=role.id,
                    permission_ids=[perm_admin_only.id],
                    session_id=uuid.uuid4(),
                )
            )

    async def test_set_permissions_invalidates_cache_for_affected_sessions(self) -> None:
        role = make_role()
        perm = make_permission(codename="brands:create")
        identity_id_1 = uuid.uuid4()
        identity_id_2 = uuid.uuid4()
        session_ids_1 = [uuid.uuid4()]
        session_ids_2 = [uuid.uuid4(), uuid.uuid4()]

        role_repo = AsyncMock()
        role_repo.get.return_value = role
        role_repo.get_identity_ids_with_role.return_value = [identity_id_1, identity_id_2]
        permission_repo = AsyncMock()
        permission_repo.get_by_ids.return_value = [perm]
        session_repo = AsyncMock()
        session_repo.get_active_session_ids.side_effect = [session_ids_1, session_ids_2]
        permission_resolver = AsyncMock()
        permission_resolver.get_permissions.return_value = frozenset({"brands:create"})
        uow = make_uow()

        handler = self._make_handler(
            role_repo=role_repo,
            permission_repo=permission_repo,
            session_repo=session_repo,
            permission_resolver=permission_resolver,
            uow=uow,
        )

        await handler.handle(
            SetRolePermissionsCommand(
                role_id=role.id,
                permission_ids=[perm.id],
                session_id=uuid.uuid4(),
            )
        )

        # Cache invalidated for all 3 affected sessions
        assert permission_resolver.invalidate.await_count == 3
        all_session_ids = session_ids_1 + session_ids_2
        for sid in all_session_ids:
            permission_resolver.invalidate.assert_any_await(sid)

    async def test_set_permissions_empty_list_clears_all(self) -> None:
        role = make_role()

        role_repo = AsyncMock()
        role_repo.get.return_value = role
        role_repo.get_identity_ids_with_role.return_value = []
        permission_repo = AsyncMock()
        uow = make_uow()

        handler = self._make_handler(
            role_repo=role_repo,
            permission_repo=permission_repo,
            uow=uow,
        )

        await handler.handle(
            SetRolePermissionsCommand(
                role_id=role.id,
                permission_ids=[],
                session_id=uuid.uuid4(),
            )
        )

        role_repo.set_permissions.assert_awaited_once_with(role.id, [])
        uow.commit.assert_awaited_once()
        # get_by_ids should not be called for empty list
        permission_repo.get_by_ids.assert_not_awaited()
