# src/modules/identity/application/commands/register.py
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from src.modules.identity.domain.entities import Identity, LocalCredentials
from src.modules.identity.domain.events import IdentityRegisteredEvent
from src.modules.identity.domain.exceptions import IdentityAlreadyExistsError
from src.modules.identity.domain.interfaces import IIdentityRepository, IRoleRepository
from src.modules.identity.domain.value_objects import IdentityType
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.security import IPasswordHasher
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class RegisterCommand:
    email: str
    password: str


@dataclass(frozen=True)
class RegisterResult:
    identity_id: uuid.UUID


class RegisterHandler:
    def __init__(
        self,
        identity_repo: IIdentityRepository,
        role_repo: IRoleRepository,
        uow: IUnitOfWork,
        hasher: IPasswordHasher,
        logger: ILogger,
    ) -> None:
        self._identity_repo = identity_repo
        self._role_repo = role_repo
        self._uow = uow
        self._hasher = hasher
        self._logger = logger.bind(handler="RegisterHandler")

    async def handle(self, command: RegisterCommand) -> RegisterResult:
        async with self._uow:
            # 1. Check email uniqueness
            if await self._identity_repo.email_exists(command.email):
                raise IdentityAlreadyExistsError()

            # 2. Create identity
            identity = Identity.register(IdentityType.LOCAL)

            # 3. Hash password (Argon2id)
            password_hash = self._hasher.hash(command.password)

            # 4. Create credentials
            now = datetime.now(UTC)
            credentials = LocalCredentials(
                identity_id=identity.id,
                email=command.email,
                password_hash=password_hash,
                created_at=now,
                updated_at=now,
            )

            # 5. Persist
            await self._identity_repo.add(identity)
            await self._identity_repo.add_credentials(credentials)

            # 6. Assign default 'customer' role
            customer_role = await self._role_repo.get_by_name("customer")
            if customer_role:
                await self._role_repo.assign_to_identity(
                    identity_id=identity.id,
                    role_id=customer_role.id,
                )

            # 7. Emit IdentityRegisteredEvent (for user module)
            identity.add_domain_event(
                IdentityRegisteredEvent(
                    identity_id=identity.id,
                    email=command.email,
                    aggregate_id=str(identity.id),
                )
            )
            self._uow.register_aggregate(identity)
            await self._uow.commit()

        self._logger.info(
            "identity.registered",
            identity_id=str(identity.id),
            email=command.email,
        )
        return RegisterResult(identity_id=identity.id)
