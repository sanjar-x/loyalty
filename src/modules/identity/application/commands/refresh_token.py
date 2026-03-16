# src/modules/identity/application/commands/refresh_token.py
import hashlib
import uuid
from dataclasses import dataclass

from src.modules.identity.domain.exceptions import RefreshTokenReuseError
from src.modules.identity.domain.interfaces import (
    IIdentityRepository,
    ISessionRepository,
)
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.security import IPermissionResolver, ITokenProvider
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class RefreshTokenCommand:
    refresh_token: str
    ip_address: str
    user_agent: str


@dataclass(frozen=True)
class RefreshTokenResult:
    access_token: str
    refresh_token: str


class RefreshTokenHandler:
    def __init__(
        self,
        session_repo: ISessionRepository,
        identity_repo: IIdentityRepository,
        uow: IUnitOfWork,
        token_provider: ITokenProvider,
        permission_resolver: IPermissionResolver,
        logger: ILogger,
    ) -> None:
        self._session_repo = session_repo
        self._identity_repo = identity_repo
        self._uow = uow
        self._token_provider = token_provider
        self._permission_resolver = permission_resolver
        self._logger = logger.bind(handler="RefreshTokenHandler")

    async def handle(self, command: RefreshTokenCommand) -> RefreshTokenResult:
        token_hash = hashlib.sha256(command.refresh_token.encode()).hexdigest()

        async with self._uow:
            # 1. Find session by refresh token hash
            session = await self._session_repo.get_by_refresh_token_hash(token_hash)

            if session is None:
                # Possible reuse: token was already rotated
                self._logger.warning(
                    "refresh_token.reuse_detected",
                    ip=command.ip_address,
                    reason="token_not_found",
                )
                raise RefreshTokenReuseError()

            # 2. Validate session
            session.ensure_valid()

            # 3. Verify identity is still active
            identity = await self._identity_repo.get(session.identity_id)
            if identity:
                identity.ensure_active()

            # 4. Rotate refresh token
            new_raw, _ = self._token_provider.create_refresh_token()
            session.rotate_refresh_token(new_raw)
            await self._session_repo.update(session)

            # 5. Create new access token
            access_token = self._token_provider.create_access_token(
                payload_data={
                    "sub": str(session.identity_id),
                    "sid": str(session.id),
                },
            )

            await self._uow.commit()

        self._logger.info(
            "session.refreshed",
            session_id=str(session.id),
            identity_id=str(session.identity_id),
        )

        return RefreshTokenResult(
            access_token=access_token,
            refresh_token=new_raw,
        )
