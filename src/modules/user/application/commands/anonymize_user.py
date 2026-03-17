"""Anonymize user command and handler.

Provides the GDPR-compliant anonymization workflow that replaces all
personally identifiable information (PII) with placeholder values.
Triggered by an IdentityDeactivatedEvent from the Identity module.
"""

import uuid
from dataclasses import dataclass

from src.modules.user.domain.interfaces import IUserRepository
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class AnonymizeUserCommand:
    """Command to anonymize a user's PII data.

    Attributes:
        user_id: The UUID of the user whose data should be anonymized.
    """

    user_id: uuid.UUID


class AnonymizeUserHandler:
    """Handler for GDPR user anonymization.

    Replaces all PII fields with placeholder values when an identity
    is deactivated. The operation is idempotent: if the user does not
    exist, a warning is logged and no error is raised.
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
        self._logger = logger.bind(handler="AnonymizeUserHandler")

    async def handle(self, command: AnonymizeUserCommand) -> None:
        """Execute the anonymization of a user's PII.

        Retrieves the user, calls ``anonymize()`` on the aggregate, and
        commits the changes. If the user is not found, the operation is
        treated as a no-op for idempotency.

        Args:
            command: The anonymization command containing the target user ID.
        """
        async with self._uow:
            user = await self._user_repo.get(command.user_id)
            if user is None:
                self._logger.warning(
                    "user.not_found_for_anonymization",
                    user_id=str(command.user_id),
                )
                return

            user.anonymize()
            await self._user_repo.update(user)
            await self._uow.commit()

        self._logger.info(
            "user.anonymized",
            user_id=str(command.user_id),
        )
