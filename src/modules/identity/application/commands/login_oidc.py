# src/modules/identity/application/commands/login_oidc.py
import uuid
from dataclasses import dataclass

from src.modules.identity.domain.entities import Identity, Session
from src.modules.identity.domain.events import IdentityRegisteredEvent
from src.modules.identity.domain.interfaces import (
    IIdentityRepository,
    ILinkedAccountRepository,
    IRoleRepository,
    ISessionRepository,
)
from src.modules.identity.domain.value_objects import IdentityType
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.security import IOIDCProvider, ITokenProvider
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class LoginOIDCCommand:
    provider_token: str
    ip_address: str
    user_agent: str


@dataclass(frozen=True)
class LoginOIDCResult:
    access_token: str
    refresh_token: str
    identity_id: uuid.UUID
    is_new_identity: bool


class LoginOIDCHandler:
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
        self._refresh_token_days = refresh_token_days

    async def handle(self, command: LoginOIDCCommand) -> LoginOIDCResult:
        # 1. Validate token with OIDC provider
        user_info = await self._oidc.validate_token(command.provider_token)

        is_new = False
        identity: Identity | None = None
        async with self._uow:
            # 2. Find existing linked account
            linked = await self._linked_repo.get_by_provider(
                provider=user_info.provider,
                provider_sub_id=user_info.sub,
            )

            if linked:
                identity = await self._identity_repo.get(linked.identity_id)
                if identity:
                    identity.ensure_active()
            else:
                # 3. Create new identity + linked account
                identity = Identity.register(IdentityType.OIDC)
                await self._identity_repo.add(identity)

                from src.modules.identity.domain.entities import LinkedAccount

                linked_account = LinkedAccount(
                    id=uuid.uuid7() if hasattr(uuid, "uuid7") else uuid.uuid4(),
                    identity_id=identity.id,
                    provider=user_info.provider,
                    provider_sub_id=user_info.sub,
                    provider_email=user_info.email,
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
                is_new = True

            # 4. Create session — identity is guaranteed non-None at this point
            assert identity is not None, "Identity must be set in if or else branch"
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

        return LoginOIDCResult(
            access_token=access_token,
            refresh_token=raw_refresh,
            identity_id=identity.id,
            is_new_identity=is_new,
        )
