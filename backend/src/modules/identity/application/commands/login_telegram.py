"""Command handler for Telegram Mini App authentication.

Validates initData, auto-provisions new identities, syncs profiles for
existing users, and creates sessions with token pairs.
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from src.modules.identity.domain.entities import Identity, LinkedAccount, Session
from src.modules.identity.domain.events import LinkedAccountCreatedEvent
from src.modules.identity.domain.interfaces import (
    IIdentityRepository,
    ILinkedAccountRepository,
    IRoleRepository,
    ISessionRepository,
    ITelegramInitDataValidator,
)
from src.modules.identity.domain.value_objects import (
    AccountType,
    PrimaryAuthMethod,
    TelegramUserData,
)
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.security import IPermissionResolver, ITokenProvider
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class LoginTelegramCommand:
    init_data_raw: str
    ip_address: str
    user_agent: str


@dataclass(frozen=True)
class LoginTelegramResult:
    access_token: str
    refresh_token: str
    identity_id: uuid.UUID
    is_new_user: bool


class LoginTelegramHandler:
    def __init__(
        self,
        telegram_validator: ITelegramInitDataValidator,
        linked_account_repo: ILinkedAccountRepository,
        identity_repo: IIdentityRepository,
        session_repo: ISessionRepository,
        role_repo: IRoleRepository,
        uow: IUnitOfWork,
        token_provider: ITokenProvider,
        permission_resolver: IPermissionResolver,
        logger: ILogger,
        max_sessions: int = 5,
        refresh_token_days: int = 7,
        idle_timeout_minutes: int = 1440,
    ) -> None:
        self._validator: ITelegramInitDataValidator = telegram_validator
        self._linked_account_repo: ILinkedAccountRepository = linked_account_repo
        self._identity_repo: IIdentityRepository = identity_repo
        self._session_repo: ISessionRepository = session_repo
        self._role_repo: IRoleRepository = role_repo
        self._uow: IUnitOfWork = uow
        self._token_provider: ITokenProvider = token_provider
        self._permission_resolver: IPermissionResolver = permission_resolver
        self._logger: ILogger = logger.bind(handler="LoginTelegramHandler")
        self._max_sessions: int = max_sessions
        self._refresh_token_days: int = refresh_token_days
        self._idle_timeout_minutes: int = idle_timeout_minutes

    async def handle(self, command: LoginTelegramCommand) -> LoginTelegramResult:
        # 1. Validate initData (outside UoW)
        telegram_user: TelegramUserData = self._validator.validate_and_parse(command.init_data_raw)

        async with self._uow:
            # 2. Lookup by telegram_id
            result: (
                tuple[Identity, LinkedAccount] | None
            ) = await self._linked_account_repo.get_by_provider(
                "telegram", str(telegram_user.telegram_id)
            )
            is_new_user: bool = result is None

            if is_new_user:
                identity: Identity = await self._provision_new_identity(telegram_user)
            else:
                identity, linked_account = result
                identity.ensure_active()
                new_metadata = {
                    "first_name": telegram_user.first_name,
                    "last_name": telegram_user.last_name,
                    "username": telegram_user.username,
                    "language_code": telegram_user.language_code,
                    "is_premium": telegram_user.is_premium,
                    "photo_url": telegram_user.photo_url
                    if telegram_user.photo_url is not None
                    else linked_account.provider_metadata.get("photo_url"),
                    "allows_write_to_pm": telegram_user.allows_write_to_pm,
                }
                if linked_account.update_metadata(new_metadata):
                    await self._linked_account_repo.update(linked_account)
                    self._logger.info(
                        "telegram.profile.synced",
                        identity_id=str(identity.id),
                        telegram_id=telegram_user.telegram_id,
                    )

            # 3. Session limit — evict oldest if needed
            active_count: int = await self._session_repo.count_active(identity.id)
            if active_count >= self._max_sessions:
                evicted_id: uuid.UUID | None = await self._session_repo.revoke_oldest_active(
                    identity.id
                )
                if evicted_id:
                    await self._permission_resolver.invalidate(evicted_id)
                    self._logger.info(
                        "telegram.session.evicted",
                        identity_id=str(identity.id),
                        evicted_session_id=str(evicted_id),
                    )

            # 4. Create session + tokens
            raw_refresh, _ = self._token_provider.create_refresh_token()
            role_ids: list[uuid.UUID] = await self._role_repo.get_identity_role_ids(identity.id)

            session = Session.create(
                identity_id=identity.id,
                refresh_token=raw_refresh,
                ip_address=command.ip_address,
                user_agent=command.user_agent,
                role_ids=role_ids,
                expires_days=self._refresh_token_days,
                idle_timeout_minutes=self._idle_timeout_minutes,
            )
            await self._session_repo.add(session)
            await self._session_repo.add_session_roles(session.id, role_ids)

            access_token = self._token_provider.create_access_token(
                payload_data={
                    "sub": str(identity.id),
                    "sid": str(session.id),
                    "tv": identity.token_version,
                },
            )

            # 5. Register aggregate for outbox (only new users have events)
            if is_new_user:
                self._uow.register_aggregate(identity)
            await self._uow.commit()

        self._logger.info(
            "telegram.login.success",
            identity_id=str(identity.id),
            telegram_id=telegram_user.telegram_id,
            is_new_user=is_new_user,
            ip=command.ip_address,
        )

        return LoginTelegramResult(
            access_token=access_token,
            refresh_token=raw_refresh,
            identity_id=identity.id,
            is_new_user=is_new_user,
        )

    async def _provision_new_identity(self, data: TelegramUserData) -> Identity:
        """Create Identity + LinkedAccount + default role atomically."""
        identity = Identity.register(PrimaryAuthMethod.TELEGRAM, AccountType.CUSTOMER)
        await self._identity_repo.add(identity)

        now = datetime.now(UTC)
        provider_metadata = {
            "first_name": data.first_name,
            "last_name": data.last_name,
            "username": data.username,
            "language_code": data.language_code,
            "is_premium": data.is_premium,
            "photo_url": data.photo_url,
            "allows_write_to_pm": data.allows_write_to_pm,
        }
        linked_account = LinkedAccount(
            id=uuid.uuid7() if hasattr(uuid, "uuid7") else uuid.uuid4(),
            identity_id=identity.id,
            provider="telegram",
            provider_sub_id=str(data.telegram_id),
            provider_email=None,
            email_verified=False,
            provider_metadata=provider_metadata,
            created_at=now,
            updated_at=now,
        )
        await self._linked_account_repo.add(linked_account)

        customer_role = await self._role_repo.get_by_name("customer")
        if customer_role:
            await self._role_repo.assign_to_identity(identity.id, customer_role.id)

        identity.add_domain_event(
            LinkedAccountCreatedEvent(
                identity_id=identity.id,
                provider="telegram",
                provider_sub_id=str(data.telegram_id),
                provider_metadata=provider_metadata,
                start_param=data.start_param,
                is_new_identity=True,
                aggregate_id=str(identity.id),
            )
        )

        self._logger.info(
            "telegram.user.provisioned",
            identity_id=str(identity.id),
            telegram_id=data.telegram_id,
            start_param=data.start_param,
        )

        return identity
