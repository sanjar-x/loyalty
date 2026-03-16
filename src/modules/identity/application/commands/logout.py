# src/modules/identity/application/commands/logout.py
import uuid
from dataclasses import dataclass

from src.modules.identity.domain.interfaces import ISessionRepository
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.security import IPermissionResolver
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class LogoutCommand:
    session_id: uuid.UUID


class LogoutHandler:
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
        self._logger = logger.bind(handler="LogoutHandler")

    async def handle(self, command: LogoutCommand) -> None:
        async with self._uow:
            session = await self._session_repo.get(command.session_id)
            if session and not session.is_revoked:
                session.revoke()
                await self._session_repo.update(session)
            await self._uow.commit()

        # Invalidate permissions cache (outside transaction)
        await self._permission_resolver.invalidate(command.session_id)

        self._logger.info(
            "session.revoked",
            session_id=str(command.session_id),
            reason="logout",
        )
