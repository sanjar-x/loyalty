"""Command handler for OIDC (OpenID Connect) provider authentication.

Validates the provider token, links or creates an identity, assigns a default
role for new identities, and creates a session with token pair.
"""

import uuid
from dataclasses import dataclass

from src.modules.identity.domain.entities import Identity, Session
from src.modules.identity.domain.events import IdentityRegisteredEvent
from src.modules.identity.domain.exceptions import (
    InvalidCredentialsError,
    MaxSessionsExceededError,
)
from src.modules.identity.domain.interfaces import (
    IIdentityRepository,
    ILinkedAccountRepository,
    IRoleRepository,
    ISessionRepository,
)
from src.modules.identity.domain.value_objects import PrimaryAuthMethod
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.security import IOIDCProvider, ITokenProvider
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class LoginOIDCCommand:
    """Command to authenticate via an external OIDC provider.

    Attributes:
        provider_token: The token issued by the OIDC provider.
        ip_address: Client IP address for session tracking.
        user_agent: Client User-Agent header for session tracking.
    """

    provider_token: str
    ip_address: str
    user_agent: str


@dataclass(frozen=True)
class LoginOIDCResult:
    """Result of a successful OIDC login.

    Attributes:
        access_token: Short-lived JWT access token.
        refresh_token: Opaque refresh token for token rotation.
        identity_id: The authenticated identity's UUID.
        is_new_identity: True if a new identity was created during this login.
    """

    access_token: str
    refresh_token: str
    identity_id: uuid.UUID
    is_new_identity: bool


class LoginOIDCHandler:
    """Handles OIDC-based authentication with automatic identity provisioning."""

    def __init__(
        self,
        oidc_provider: IOIDCProvider,
        identity_repo: IIdentityRepository,
        linked_account_repo: ILinkedAccountRepository,
        session_repo: ISessionRepository,
        role_repo: IRoleRepository,
        uow: IUnitOfWork,
        token_provider: ITokenProvider,
        logger: ILogger,
        max_sessions: int = 5,
        refresh_token_days: int = 30,
    ) -> None:
        self._oidc = oidc_provider
        self._identity_repo = identity_repo
        self._linked_repo = linked_account_repo
        self._session_repo = session_repo
        self._role_repo = role_repo
        self._uow = uow
        self._token_provider = token_provider
        self._logger = logger.bind(handler="LoginOIDCHandler")
        self._max_sessions = max_sessions
        self._refresh_token_days = refresh_token_days

    async def handle(self, command: LoginOIDCCommand) -> LoginOIDCResult:
        """Execute the OIDC login command.

        Validates the provider token, resolves or creates the identity,
        and issues a session with access and refresh tokens.

        Args:
            command: The OIDC login command.

        Returns:
            A result containing tokens and identity information.

        Raises:
            InvalidCredentialsError: If the linked identity no longer exists.
            IdentityDeactivatedError: If the identity is deactivated.
        """
        # Validate token with OIDC provider
        user_info = await self._oidc.validate_token(command.provider_token)

        is_new = False
        identity: Identity | None = None
        async with self._uow:
            # Find existing linked account
            linked = await self._linked_repo.get_by_provider(
                provider=user_info.provider,
                provider_sub_id=user_info.sub,
            )

            if linked:
                identity = await self._identity_repo.get(linked.identity_id)
                if identity is None:
                    raise InvalidCredentialsError()
                identity.ensure_active()
            else:
                # Create new identity and linked account
                identity = Identity.register(PrimaryAuthMethod.OIDC)
                await self._identity_repo.add(identity)

                from datetime import UTC, datetime

                from src.modules.identity.domain.entities import LinkedAccount
                from src.modules.identity.domain.value_objects import (
                    TRUSTED_EMAIL_PROVIDERS,
                    AuthProvider,
                )

                now = datetime.now(UTC)
                # Trust email verification for known OIDC providers (Google, Apple)
                provider_enum = (
                    AuthProvider(user_info.provider)
                    if user_info.provider in [p.value for p in AuthProvider]
                    else None
                )
                email_verified = (
                    provider_enum in TRUSTED_EMAIL_PROVIDERS if provider_enum else False
                )

                linked_account = LinkedAccount(
                    id=uuid.uuid7() if hasattr(uuid, "uuid7") else uuid.uuid4(),
                    identity_id=identity.id,
                    provider=user_info.provider,
                    provider_sub_id=user_info.sub,
                    provider_email=user_info.email,
                    email_verified=email_verified,
                    provider_metadata={},
                    created_at=now,
                    updated_at=now,
                )
                await self._linked_repo.add(linked_account)

                # Assign default customer role
                customer_role = await self._role_repo.get_by_name("customer")
                if customer_role:
                    await self._role_repo.assign_to_identity(
                        identity_id=identity.id,
                        role_id=customer_role.id,
                    )

                identity.add_domain_event(
                    IdentityRegisteredEvent(
                        identity_id=identity.id,
                        email=user_info.email or "",
                        aggregate_id=str(identity.id),
                    )
                )
                identity.ensure_active()
                is_new = True

            # Check session limit (same enforcement as local login)
            active_count = await self._session_repo.count_active(identity.id)
            if active_count >= self._max_sessions:
                self._logger.warning(
                    "max_sessions.exceeded",
                    identity_id=str(identity.id),
                    ip=command.ip_address,
                )
                raise MaxSessionsExceededError(max_sessions=self._max_sessions)

            # Create session
            role_ids = await self._role_repo.get_identity_role_ids(identity.id)
            raw_refresh, _ = self._token_provider.create_refresh_token()

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

            access_token = self._token_provider.create_access_token(
                payload_data={"sub": str(identity.id), "sid": str(session.id)},
            )

            if is_new:
                self._uow.register_aggregate(identity)
            await self._uow.commit()

        if identity is None:
            raise InvalidCredentialsError()
        return LoginOIDCResult(
            access_token=access_token,
            refresh_token=raw_refresh,
            identity_id=identity.id,
            is_new_identity=is_new,
        )
