# src/modules/identity/application/commands/deactivate_identity.py
import uuid
from dataclasses import dataclass

from src.modules.identity.domain.interfaces import (
    IIdentityRepository,
    ISessionRepository,
)
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.security import IPermissionResolver
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class DeactivateIdentityCommand:
    identity_id: uuid.UUID
    reason: str = "user_request"


class DeactivateIdentityHandler:
    def __init__(
        self,
        identity_repo: IIdentityRepository,
        session_repo: ISessionRepository,
        uow: IUnitOfWork,
        permission_resolver: IPermissionResolver,
        logger: ILogger,
    ) -> None:
        self._identity_repo = identity_repo
        self._session_repo = session_repo
        self._uow = uow
        self._permission_resolver = permission_resolver
        self._logger = logger.bind(handler="DeactivateIdentityHandler")

    async def handle(self, command: DeactivateIdentityCommand) -> None:
        async with self._uow:
            identity = await self._identity_repo.get(command.identity_id)
            if identity is None:
                return

            # 1. Deactivate identity (emits IdentityDeactivatedEvent)
            identity.deactivate(reason=command.reason)

            # 2. Revoke all sessions
            revoked_ids = await self._session_repo.revoke_all_for_identity(
                command.identity_id,
            )

            self._uow.register_aggregate(identity)
            await self._uow.commit()

        # 3. Invalidate permissions cache
        for session_id in revoked_ids:
            await self._permission_resolver.invalidate(session_id)

        self._logger.info(
            "identity.deactivated",
            identity_id=str(command.identity_id),
            reason=command.reason,
            revoked_sessions=len(revoked_ids),
        )
