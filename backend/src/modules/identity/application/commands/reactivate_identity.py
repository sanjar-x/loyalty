"""Command handler for reactivating a deactivated identity.

Reactivates an identity, clearing deactivation fields and emitting
an IdentityReactivatedEvent.
"""

import uuid
from dataclasses import dataclass

from src.modules.identity.domain.exceptions import IdentityAlreadyActiveError
from src.modules.identity.domain.interfaces import IIdentityRepository
from src.shared.exceptions import NotFoundError
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class ReactivateIdentityCommand:
    """Command to reactivate a deactivated identity.

    Attributes:
        identity_id: The identity to reactivate.
        reactivated_by: Identity ID of the admin performing the reactivation.
    """

    identity_id: uuid.UUID
    reactivated_by: uuid.UUID


class ReactivateIdentityHandler:
    """Handles identity reactivation."""

    def __init__(
        self,
        identity_repo: IIdentityRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._identity_repo = identity_repo
        self._uow = uow
        self._logger = logger.bind(handler="ReactivateIdentityHandler")

    async def handle(self, command: ReactivateIdentityCommand) -> None:
        """Execute the reactivate identity command.

        Args:
            command: The reactivate identity command.

        Raises:
            NotFoundError: If the identity does not exist.
            IdentityAlreadyActiveError: If the identity is already active.
        """
        async with self._uow:
            # 1. Identity exists
            identity = await self._identity_repo.get(command.identity_id)
            if identity is None:
                raise NotFoundError(
                    message=f"Identity {command.identity_id} not found",
                    error_code="IDENTITY_NOT_FOUND",
                )

            # 2. Identity is deactivated
            if identity.is_active:
                raise IdentityAlreadyActiveError()

            # 3. Reactivate and register aggregate immediately for event collection
            identity.reactivate()
            self._uow.register_aggregate(identity)

            # 4. Persist reactivation state (CRITICAL)
            await self._identity_repo.update(identity)

            await self._uow.commit()

        self._logger.info(
            "identity.reactivated",
            identity_id=str(command.identity_id),
            reactivated_by=str(command.reactivated_by),
        )
