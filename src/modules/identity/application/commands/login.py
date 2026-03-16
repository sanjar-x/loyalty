# src/modules/identity/application/commands/login.py
import uuid
from dataclasses import dataclass

from src.modules.identity.domain.entities import Session
from src.modules.identity.domain.exceptions import (
    InvalidCredentialsError,
    MaxSessionsExceededError,
)
from src.modules.identity.domain.interfaces import (
    IIdentityRepository,
    IRoleRepository,
    ISessionRepository,
)
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.security import IPasswordHasher, ITokenProvider
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class LoginCommand:
    email: str
    password: str
    ip_address: str
    user_agent: str


@dataclass(frozen=True)
class LoginResult:
    access_token: str
    refresh_token: str
    identity_id: uuid.UUID


class LoginHandler:
    def __init__(
        self,
        identity_repo: IIdentityRepository,
        session_repo: ISessionRepository,
        role_repo: IRoleRepository,
        uow: IUnitOfWork,
        hasher: IPasswordHasher,
        token_provider: ITokenProvider,
        logger: ILogger,
        max_sessions: int = 5,
        refresh_token_days: int = 30,
    ) -> None:
        self._identity_repo = identity_repo
        self._session_repo = session_repo
        self._role_repo = role_repo
        self._uow = uow
        self._hasher = hasher
        self._token_provider = token_provider
        self._logger = logger.bind(handler="LoginHandler")
        self._max_sessions = max_sessions
        self._refresh_token_days = refresh_token_days

    async def handle(self, command: LoginCommand) -> LoginResult:
        async with self._uow:
            # 1. Find identity by email (unified error for enumeration protection)
            result = await self._identity_repo.get_by_email(command.email)
            if result is None:
                raise InvalidCredentialsError()

            identity, credentials = result

            # 2. Verify password
            if not self._hasher.verify(command.password, credentials.password_hash):
                self._logger.warning(
                    "identity.login.failed",
                    email=command.email,
                    ip=command.ip_address,
                    reason="invalid_credentials",
                )
                raise InvalidCredentialsError()

            # 3. Ensure identity is active
            identity.ensure_active()

            # 4. Transparent Argon2id rehash (Bcrypt → Argon2id)
            if self._hasher.needs_rehash(credentials.password_hash):
                credentials.password_hash = self._hasher.hash(command.password)
                await self._identity_repo.update_credentials(credentials)
                self._logger.info(
                    "password.rehashed",
                    identity_id=str(identity.id),
                    from_algo="bcrypt",
                    to_algo="argon2id",
                )

            # 5. Check session limit
            active_count = await self._session_repo.count_active(identity.id)
            if active_count >= self._max_sessions:
                self._logger.warning(
                    "max_sessions.exceeded",
                    identity_id=str(identity.id),
                    ip=command.ip_address,
                )
                raise MaxSessionsExceededError(max_sessions=self._max_sessions)

            # 6. Generate tokens
            raw_refresh, _ = self._token_provider.create_refresh_token()

            # 7. Get role IDs for session activation (NIST)
            role_ids = await self._role_repo.get_identity_role_ids(identity.id)

            # 8. Create session
            session = Session.create(
                identity_id=identity.id,
                refresh_token=raw_refresh,
                ip_address=command.ip_address,
                user_agent=command.user_agent,
                role_ids=role_ids,
                expires_days=self._refresh_token_days,
            )
            await self._session_repo.add(session)
            await self._session_repo.add_session_roles(session.id, role_ids)

            # 9. Create access token
            access_token = self._token_provider.create_access_token(
                payload_data={
                    "sub": str(identity.id),
                    "sid": str(session.id),
                },
            )

            await self._uow.commit()

        self._logger.info(
            "identity.login.success",
            identity_id=str(identity.id),
            ip=command.ip_address,
            user_agent=command.user_agent,
        )

        return LoginResult(
            access_token=access_token,
            refresh_token=raw_refresh,
            identity_id=identity.id,
        )
