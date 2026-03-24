"""Command handler for admin-initiated identity deactivation.

Deactivates a target identity with security guards: self-deactivation
prevention, last admin protection, and session revocation with
cache invalidation.
"""

import uuid
from dataclasses import dataclass

from src.modules.identity.domain.exceptions import (
    IdentityAlreadyDeactivatedError,
    LastAdminProtectionError,
    SelfDeactivationError,
)
from src.modules.identity.domain.interfaces import (
    IIdentityRepository,
    IRoleRepository,
    ISessionRepository,
)
from src.shared.exceptions import NotFoundError
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.security import IPermissionResolver
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class AdminDeactivateIdentityCommand:
    """Command to deactivate an identity by an admin.

    Attributes:
        identity_id: The identity to deactivate.
        reason: Human-readable deactivation reason.
        deactivated_by: Identity ID of the admin performing the deactivation.
    """

    identity_id: uuid.UUID
    reason: str
    deactivated_by: uuid.UUID


class AdminDeactivateIdentityHandler:
    """Handles admin-initiated identity deactivation with security guards."""

    def __init__(
        self,
        identity_repo: IIdentityRepository,
        role_repo: IRoleRepository,
        session_repo: ISessionRepository,
        uow: IUnitOfWork,
        permission_resolver: IPermissionResolver,
        logger: ILogger,
    ) -> None:
        self._identity_repo = identity_repo
        self._role_repo = role_repo
        self._session_repo = session_repo
        self._uow = uow
        self._permission_resolver = permission_resolver
        self._logger = logger.bind(handler="AdminDeactivateIdentityHandler")

    async def handle(self, command: AdminDeactivateIdentityCommand) -> None:
        """Execute the admin deactivate identity command.

        Args:
            command: The admin deactivate identity command.

        Raises:
            NotFoundError: If the identity does not exist.
            IdentityAlreadyDeactivatedError: If the identity is already deactivated.
            SelfDeactivationError: If the admin tries to deactivate themselves.
            LastAdminProtectionError: If deactivating the last admin.
        """
        revoked_ids: list[uuid.UUID] = []

        async with self._uow:
            # 1. Identity exists
            identity = await self._identity_repo.get(command.identity_id)
            if identity is None:
                raise NotFoundError(
                    message=f"Identity {command.identity_id} not found",
                    error_code="IDENTITY_NOT_FOUND",
                )

            # 2. Identity is active
            if not identity.is_active:
                raise IdentityAlreadyDeactivatedError()

            # 3. Not self-deactivation
            if command.identity_id == command.deactivated_by:
                raise SelfDeactivationError()

            # 4. Not last admin — single query instead of N+1
            admin_count = await self._role_repo.count_identities_with_role("admin")
            target_role_ids = await self._role_repo.get_identity_role_ids(
                command.identity_id
            )
            admin_role = await self._role_repo.get_by_name("admin")
            target_has_admin = (
                admin_role is not None and admin_role.id in target_role_ids
            )

            if target_has_admin and admin_count <= 1:
                raise LastAdminProtectionError()

            # 5. Deactivate and register aggregate immediately for event collection
            identity.deactivate(
                reason=command.reason, deactivated_by=command.deactivated_by
            )
            self._uow.register_aggregate(identity)

            # 6. Persist deactivation state (CRITICAL)
            await self._identity_repo.update(identity)

            # 7. Revoke all sessions — store IDs INSIDE UoW block
            revoked_ids = await self._session_repo.revoke_all_for_identity(
                command.identity_id,
            )

            await self._uow.commit()

        # 8. Invalidate permission cache OUTSIDE transaction (single round-trip)
        await self._permission_resolver.invalidate_many(revoked_ids)

        self._logger.info(
            "identity.admin_deactivated",
            identity_id=str(command.identity_id),
            deactivated_by=str(command.deactivated_by),
            reason=command.reason,
            revoked_sessions=len(revoked_ids),
        )
