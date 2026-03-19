"""Update user profile command and handler.

Provides the workflow for partial updates to a user's profile fields.
Only non-None fields in the command are applied to the aggregate.
"""

import uuid
from dataclasses import dataclass

from src.modules.user.domain.exceptions import UserNotFoundError
from src.modules.user.domain.interfaces import IUserRepository
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class UpdateProfileCommand:
    """Command to update a user's profile fields.

    Only fields set to non-None values will be applied. All fields
    default to None, meaning "no change".

    Attributes:
        user_id: The UUID of the user to update.
        first_name: New first name, or None to leave unchanged.
        last_name: New last name, or None to leave unchanged.
        phone: New phone number, or None to leave unchanged.
        profile_email: New display email, or None to leave unchanged.
    """

    user_id: uuid.UUID
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    profile_email: str | None = None


class UpdateProfileHandler:
    """Handler for partial user profile updates.

    Applies only the provided (non-None) fields to the User aggregate
    and persists the changes within a unit of work.
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
        self._logger = logger.bind(handler="UpdateProfileHandler")

    async def handle(self, command: UpdateProfileCommand) -> None:
        """Execute a partial profile update.

        Retrieves the user, builds a dict of non-None updates, applies
        them to the aggregate, and commits the transaction.

        Args:
            command: The update command with fields to change.

        Raises:
            UserNotFoundError: If no user exists with the given user_id.
        """
        async with self._uow:
            user = await self._user_repo.get(command.user_id)
            if user is None:
                raise UserNotFoundError(command.user_id)

            # Build kwargs from non-None fields
            updates = {}
            if command.first_name is not None:
                updates["first_name"] = command.first_name
            if command.last_name is not None:
                updates["last_name"] = command.last_name
            if command.phone is not None:
                updates["phone"] = command.phone
            if command.profile_email is not None:
                updates["profile_email"] = command.profile_email

            if updates:
                user.update_profile(**updates)
                await self._user_repo.update(user)

            await self._uow.commit()

        self._logger.info("user.profile_updated", user_id=str(command.user_id))
