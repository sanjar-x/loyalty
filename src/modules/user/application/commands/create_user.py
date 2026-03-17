"""Create user command and handler.

Provides the user creation workflow triggered by an IdentityRegisteredEvent
from the Identity module via the outbox consumer. Creates a User aggregate
with a shared primary key matching the Identity aggregate.
"""

import uuid
from dataclasses import dataclass

from src.modules.user.domain.entities import User
from src.modules.user.domain.interfaces import IUserRepository
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class CreateUserCommand:
    """Command to create a new user from an identity registration.

    Attributes:
        identity_id: The Identity aggregate ID to use as the shared PK.
        profile_email: Optional display email for the new user profile.
    """

    identity_id: uuid.UUID
    profile_email: str | None = None


class CreateUserHandler:
    """Handler for creating a User from an identity registration event.

    This is an internal handler invoked via the outbox consumer when
    an IdentityRegisteredEvent is received. The operation is idempotent:
    if a user with the given identity ID already exists, creation is skipped.
    """

    def __init__(
        self,
        user_repo: IUserRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        """Initialize the handler with its dependencies.

        Args:
            user_repo: Repository for User aggregate persistence.
            uow: Unit of Work for transactional consistency.
            logger: Structured logger instance.
        """
        self._user_repo = user_repo
        self._uow = uow
        self._logger = logger.bind(handler="CreateUserHandler")

    async def handle(self, command: CreateUserCommand) -> None:
        """Execute user creation from an identity registration.

        Checks for an existing user to ensure idempotency, then creates
        a new User aggregate with the shared primary key from the Identity
        module.

        Args:
            command: The creation command containing identity ID and
                optional profile email.
        """
        async with self._uow:
            existing = await self._user_repo.get(command.identity_id)
            if existing:
                self._logger.warning(
                    "user.already_exists",
                    identity_id=str(command.identity_id),
                )
                return

            user = User.create_from_identity(
                identity_id=command.identity_id,
                profile_email=command.profile_email,
            )
            await self._user_repo.add(user)
            await self._uow.commit()

        self._logger.info(
            "user.created",
            user_id=str(command.identity_id),
        )
