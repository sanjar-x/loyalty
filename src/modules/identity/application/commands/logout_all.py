# src/modules/identity/application/commands/logout_all.py
import uuid
from dataclasses import dataclass

from src.modules.identity.domain.interfaces import ISessionRepository
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.security import IPermissionResolver
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class LogoutAllCommand:
    identity_id: uuid.UUID


class LogoutAllHandler:
    def __init__(
        self,
        session_repo: ISessionRepository,
        uow: IUnitOfWork,
        permission_resolver: IPermissionResolver,
        logger: ILogger,
    ) -> None:
        self._session_repo = session_repo
        self._uow = uow
        self._permission_resolver = permission_resolver
        self._logger = logger.bind(handler="LogoutAllHandler")

    async def handle(self, command: LogoutAllCommand) -> None:
        async with self._uow:
            revoked_ids = await self._session_repo.revoke_all_for_identity(
                command.identity_id,
            )
            await self._uow.commit()

        # Invalidate permissions cache for all revoked sessions
        for session_id in revoked_ids:
            await self._permission_resolver.invalidate(session_id)

        self._logger.info(
            "sessions.all_revoked",
            identity_id=str(command.identity_id),
            revoked_count=len(revoked_ids),
        )
