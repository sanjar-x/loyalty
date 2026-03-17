"""Command handler for local email/password authentication.

Implements the full login flow: credential verification, identity status
check, transparent password rehash (Bcrypt to Argon2id), session limit
enforcement, token generation, and session creation with NIST RBAC role
activation.
"""

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
    """Command to authenticate with email and password.

    Attributes:
        email: The user's email address.
        password: The user's plaintext password.
        ip_address: Client IP address for session tracking.
        user_agent: Client User-Agent header for session tracking.
    """

    email: str
    password: str
    ip_address: str
    user_agent: str


@dataclass(frozen=True)
class LoginResult:
    """Result of a successful login.

    Attributes:
        access_token: Short-lived JWT access token.
        refresh_token: Opaque refresh token for token rotation.
        identity_id: The authenticated identity's UUID.
    """

    access_token: str
    refresh_token: str
    identity_id: uuid.UUID


class LoginHandler:
    """Handles local email/password login with session creation."""

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
        """Execute the login command.

        Args:
            command: The login command with credentials and client info.

        Returns:
            A result containing access and refresh tokens.

        Raises:
            InvalidCredentialsError: If email is not found or password is wrong.
            IdentityDeactivatedError: If the identity is deactivated.
            MaxSessionsExceededError: If the session limit is reached.
        """
        async with self._uow:
            # Find identity by email (unified error for enumeration protection)
            result = await self._identity_repo.get_by_email(command.email)
            if result is None:
                raise InvalidCredentialsError()

            identity, credentials = result

            # Verify password
            if not self._hasher.verify(command.password, credentials.password_hash):
                self._logger.warning(
                    "identity.login.failed",
                    email=command.email,
                    ip=command.ip_address,
                    reason="invalid_credentials",
                )
                raise InvalidCredentialsError()

            # Ensure identity is active
            identity.ensure_active()

            # Transparent Argon2id rehash (Bcrypt -> Argon2id migration)
            if self._hasher.needs_rehash(credentials.password_hash):
                credentials.password_hash = self._hasher.hash(command.password)
                await self._identity_repo.update_credentials(credentials)
                self._logger.info(
                    "password.rehashed",
                    identity_id=str(identity.id),
                    from_algo="bcrypt",
                    to_algo="argon2id",
                )

            # Check session limit
            active_count = await self._session_repo.count_active(identity.id)
            if active_count >= self._max_sessions:
                self._logger.warning(
                    "max_sessions.exceeded",
                    identity_id=str(identity.id),
                    ip=command.ip_address,
                )
                raise MaxSessionsExceededError(max_sessions=self._max_sessions)

            # Generate tokens
            raw_refresh, _ = self._token_provider.create_refresh_token()

            # Get role IDs for session activation (NIST RBAC)
            role_ids = await self._role_repo.get_identity_role_ids(identity.id)

            # Create session
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

            # Create access token
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
