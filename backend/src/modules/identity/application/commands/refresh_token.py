"""Command handler for refresh token rotation.

Looks up a session by the SHA-256 hash of the presented refresh token,
validates the session and identity, rotates the refresh token, and issues
a new access/refresh token pair.
"""

import hashlib
from dataclasses import dataclass

from src.modules.identity.domain.exceptions import (
    InvalidCredentialsError,
    RefreshTokenReuseError,
)
from src.modules.identity.domain.interfaces import (
    IIdentityRepository,
    ISessionRepository,
)
from src.shared.interfaces.cache import ICacheService
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

    # TTL for reuse-detection entries: old_hash → identity_id (seconds)
    _REUSE_DETECTION_TTL = 86400  # 24 hours

    def __init__(
        self,
        session_repo: ISessionRepository,
        identity_repo: IIdentityRepository,
        uow: IUnitOfWork,
        token_provider: ITokenProvider,
        permission_resolver: IPermissionResolver,
        cache: ICacheService,
        logger: ILogger,
    ) -> None:
        self._session_repo = session_repo
        self._identity_repo = identity_repo
        self._uow = uow
        self._token_provider = token_provider
        self._permission_resolver = permission_resolver
        self._cache = cache
        self._logger = logger.bind(handler="RefreshTokenHandler")

    async def handle(self, command: RefreshTokenCommand) -> RefreshTokenResult:
        """Execute the refresh token command.

        Args:
            command: The refresh token command.

        Returns:
            A result containing the new access and refresh tokens.

        Raises:
            RefreshTokenReuseError: If the token has already been rotated
                (all sessions for the identity are revoked).
            SessionExpiredError: If the session has expired.
            SessionRevokedError: If the session has been revoked.
            IdentityDeactivatedError: If the owning identity is deactivated.
        """
        token_hash = hashlib.sha256(command.refresh_token.encode()).hexdigest()

        async with self._uow:
            # Find session by refresh token hash
            session = await self._session_repo.get_by_refresh_token_hash(token_hash)

            if session is None:
                # Reuse detected: look up identity via cache entry from prior rotation
                await self._handle_reuse(token_hash, command.ip_address)
                raise RefreshTokenReuseError()

            # Validate session
            session.ensure_valid()

            # Verify identity exists and is still active
            identity = await self._identity_repo.get(session.identity_id)
            if identity is None:
                raise InvalidCredentialsError()
            identity.ensure_active()

            # Capture identity_id for reuse-detection entry (written after commit)
            identity_id_for_reuse = session.identity_id

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

        # Store reuse-detection entry AFTER commit (old_hash → identity_id)
        # so a DB rollback doesn't leave a phantom cache entry
        reuse_key = f"rotated:{token_hash}"
        await self._cache.set(
            reuse_key, str(identity_id_for_reuse), ttl=self._REUSE_DETECTION_TTL,
        )

        self._logger.info(
            "session.refreshed",
            session_id=str(session.id),
            identity_id=str(session.identity_id),
        )

        return RefreshTokenResult(
            access_token=access_token,
            refresh_token=new_raw,
        )

    async def _handle_reuse(self, token_hash: str, ip_address: str) -> None:
        """Handle a detected refresh token reuse by revoking all sessions.

        Looks up the identity via a cached reuse-detection entry
        (stored during prior rotation), revokes all sessions, and
        invalidates permission caches.

        Args:
            token_hash: The SHA-256 hash of the reused token.
            ip_address: Client IP for audit logging.
        """
        reuse_key = f"rotated:{token_hash}"
        identity_id_str = await self._cache.get(reuse_key)

        if identity_id_str is not None:
            import uuid as _uuid

            identity_id = _uuid.UUID(identity_id_str)

            # Revoke all sessions for the compromised identity
            async with self._uow:
                revoked_ids = await self._session_repo.revoke_all_for_identity(identity_id)
                await self._uow.commit()

            # Invalidate permission caches
            await self._permission_resolver.invalidate_many(revoked_ids)

            # Clean up the reuse entry
            await self._cache.delete(reuse_key)

            self._logger.critical(
                "refresh_token.reuse_confirmed",
                identity_id=str(identity_id),
                ip=ip_address,
                revoked_sessions=len(revoked_ids),
            )
        else:
            self._logger.warning(
                "refresh_token.reuse_suspected",
                ip=ip_address,
                reason="token_not_found_no_reuse_entry",
            )
