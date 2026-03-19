"""Command handler for refresh token rotation.

Looks up a session by the SHA-256 hash of the presented refresh token,
validates the session and identity, rotates the refresh token, and issues
a new access/refresh token pair.
"""

import hashlib
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
    """Command to rotate a refresh token and obtain new tokens.

    Attributes:
        refresh_token: The current raw opaque refresh token.
        ip_address: Client IP address for audit logging.
        user_agent: Client User-Agent header for audit logging.
    """

    refresh_token: str
    ip_address: str
    user_agent: str


@dataclass(frozen=True)
class RefreshTokenResult:
    """Result of a successful token refresh.

    Attributes:
        access_token: The new short-lived JWT access token.
        refresh_token: The new opaque refresh token (rotated).
    """

    access_token: str
    refresh_token: str


class RefreshTokenHandler:
    """Handles refresh token rotation with reuse detection."""

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
        """Execute the refresh token command.

        Args:
            command: The refresh token command.

        Returns:
            A result containing the new access and refresh tokens.

        Raises:
            RefreshTokenReuseError: If the token has already been rotated.
            SessionExpiredError: If the session has expired.
            SessionRevokedError: If the session has been revoked.
            IdentityDeactivatedError: If the owning identity is deactivated.
        """
        token_hash = hashlib.sha256(command.refresh_token.encode()).hexdigest()

        async with self._uow:
            # Find session by refresh token hash
            session = await self._session_repo.get_by_refresh_token_hash(token_hash)

            if session is None:
                # Possible reuse: token was already rotated
                self._logger.warning(
                    "refresh_token.reuse_detected",
                    ip=command.ip_address,
                    reason="token_not_found",
                )
                raise RefreshTokenReuseError()

            # Validate session
            session.ensure_valid()

            # Verify identity is still active
            identity = await self._identity_repo.get(session.identity_id)
            if identity:
                identity.ensure_active()

            # Rotate refresh token
            new_raw, _ = self._token_provider.create_refresh_token()
            session.rotate_refresh_token(new_raw)
            await self._session_repo.update(session)

            # Create new access token
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
