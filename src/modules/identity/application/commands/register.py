"""Command handler for local identity registration.

Creates a new identity with local email/password credentials, assigns
the default 'customer' role, and emits an IdentityRegisteredEvent for
cross-module consumers (e.g. User module).
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from src.modules.identity.domain.entities import Identity, LocalCredentials
from src.modules.identity.domain.events import IdentityRegisteredEvent
from src.modules.identity.domain.exceptions import IdentityAlreadyExistsError
from src.modules.identity.domain.interfaces import IIdentityRepository, IRoleRepository
from src.modules.identity.domain.value_objects import AccountType, IdentityType
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.security import IPasswordHasher
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class RegisterCommand:
    """Command to register a new identity with email and password.

    Attributes:
        email: The email address for the new identity.
        password: The plaintext password (will be hashed with Argon2id).
    """

    email: str
    password: str


@dataclass(frozen=True)
class RegisterResult:
    """Result of a successful registration.

    Attributes:
        identity_id: The UUID of the newly created identity.
    """

    identity_id: uuid.UUID


class RegisterHandler:
    """Handles new identity registration with credential creation."""

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
        """Execute the register command.

        Args:
            command: The registration command with email and password.

        Returns:
            A result containing the new identity's UUID.

        Raises:
            IdentityAlreadyExistsError: If the email is already registered.
        """
        async with self._uow:
            # Check email uniqueness
            if await self._identity_repo.email_exists(command.email):
                raise IdentityAlreadyExistsError()

            # Create identity
            identity = Identity.register(IdentityType.LOCAL, AccountType.CUSTOMER)

            # Hash password (Argon2id)
            password_hash = self._hasher.hash(command.password)

            # Create credentials
            now = datetime.now(UTC)
            credentials = LocalCredentials(
                identity_id=identity.id,
                email=command.email,
                password_hash=password_hash,
                created_at=now,
                updated_at=now,
            )

            # Persist identity and credentials
            await self._identity_repo.add(identity)
            await self._identity_repo.add_credentials(credentials)

            # Assign default 'customer' role
            customer_role = await self._role_repo.get_by_name("customer")
            if customer_role:
                await self._role_repo.assign_to_identity(
                    identity_id=identity.id,
                    role_id=customer_role.id,
                )

            # Emit IdentityRegisteredEvent (consumed by User module)
            identity.add_domain_event(
                IdentityRegisteredEvent(
                    identity_id=identity.id,
                    email=command.email,
                    account_type=AccountType.CUSTOMER.value,
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
