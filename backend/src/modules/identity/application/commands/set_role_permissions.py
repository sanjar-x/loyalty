"""Command handler for setting (full-replace) role permissions.

Validates role existence, permission IDs, privilege escalation prevention,
then replaces all permissions and invalidates permission caches for affected
sessions.
"""

import uuid
from dataclasses import dataclass

from src.modules.identity.domain.exceptions import PrivilegeEscalationError
from src.modules.identity.domain.interfaces import (
    IPermissionRepository,
    IRoleRepository,
    ISessionRepository,
)
from src.shared.exceptions import NotFoundError
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.security import IPermissionResolver
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class SetRolePermissionsCommand:
    """Command to full-replace permissions for a role.

    Attributes:
        role_id: The role to update permissions for.
        permission_ids: Complete set of permission IDs to assign.
        session_id: The admin's session ID for privilege escalation check.
    """

    role_id: uuid.UUID
    permission_ids: list[uuid.UUID]
    session_id: uuid.UUID


class SetRolePermissionsHandler:
    """Handles setting role permissions with privilege escalation prevention."""

    def __init__(
        self,
        role_repo: IRoleRepository,
        permission_repo: IPermissionRepository,
        session_repo: ISessionRepository,
        uow: IUnitOfWork,
        permission_resolver: IPermissionResolver,
        logger: ILogger,
    ) -> None:
        self._role_repo = role_repo
        self._permission_repo = permission_repo
        self._session_repo = session_repo
        self._uow = uow
        self._permission_resolver = permission_resolver
        self._logger = logger.bind(handler="SetRolePermissionsHandler")

    async def handle(self, command: SetRolePermissionsCommand) -> None:
        """Execute the set role permissions command.

        Args:
            command: The set role permissions command.

        Raises:
            NotFoundError: If the role or any permission does not exist.
            PrivilegeEscalationError: If the admin tries to grant permissions they lack.
        """
        affected_session_ids: list[uuid.UUID] = []

        async with self._uow:
            # 1. Role exists
            role = await self._role_repo.get(command.role_id)
            if role is None:
                raise NotFoundError(
                    message=f"Role {command.role_id} not found",
                    error_code="ROLE_NOT_FOUND",
                )

            # 2. Validate all permission IDs exist
            if command.permission_ids:
                existing = await self._permission_repo.get_by_ids(command.permission_ids)
                if len(existing) != len(command.permission_ids):
                    found_ids = {p.id for p in existing}
                    missing_ids = [
                        str(pid) for pid in command.permission_ids if pid not in found_ids
                    ]
                    raise NotFoundError(
                        message="Some permissions not found",
                        error_code="PERMISSION_NOT_FOUND",
                        details={"missing_ids": missing_ids},
                    )

                # 3. Privilege escalation check
                admin_perms = await self._permission_resolver.get_permissions(command.session_id)
                requested_codenames = {p.codename for p in existing}
                escalation = requested_codenames - admin_perms
                if escalation:
                    raise PrivilegeEscalationError(escalated_permissions=sorted(escalation))

            # 4. Full-replace permissions
            await self._role_repo.set_permissions(command.role_id, command.permission_ids)

            # 5. Fetch affected session IDs INSIDE UoW block
            affected_identity_ids = await self._role_repo.get_identity_ids_with_role(
                command.role_id
            )
            for identity_id in affected_identity_ids:
                session_ids = await self._session_repo.get_active_session_ids(identity_id)
                affected_session_ids.extend(session_ids)

            await self._uow.commit()

        # 6. Invalidate cache OUTSIDE transaction (single round-trip)
        await self._permission_resolver.invalidate_many(affected_session_ids)

        self._logger.info(
            "role.permissions_set",
            role_id=str(command.role_id),
            permission_count=len(command.permission_ids),
            affected_sessions=len(affected_session_ids),
        )
