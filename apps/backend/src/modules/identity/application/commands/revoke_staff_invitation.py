"""Command handler for revoking a staff invitation."""

import uuid
from dataclasses import dataclass

from src.modules.identity.domain.exceptions import InvitationNotFoundError
from src.modules.identity.domain.interfaces import IStaffInvitationRepository
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class RevokeStaffInvitationCommand:
    """Command to revoke a pending staff invitation.

    Attributes:
        invitation_id: The invitation to revoke.
        revoked_by: Identity ID of the admin revoking.
    """

    invitation_id: uuid.UUID
    revoked_by: uuid.UUID


class RevokeStaffInvitationHandler:
    """Handles revoking a pending staff invitation."""

    def __init__(
        self,
        invitation_repo: IStaffInvitationRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._invitation_repo = invitation_repo
        self._uow = uow
        self._logger = logger.bind(handler="RevokeStaffInvitationHandler")

    async def handle(self, command: RevokeStaffInvitationCommand) -> None:
        """Execute the revoke invitation command.

        Args:
            command: The revocation command.

        Raises:
            InvitationNotFoundError: If the invitation doesn't exist.
            InvitationNotPendingError: If not in PENDING status.
        """
        async with self._uow:
            invitation = await self._invitation_repo.get(command.invitation_id)
            if invitation is None:
                raise InvitationNotFoundError()

            invitation.revoke()
            await self._invitation_repo.update(invitation)
            await self._uow.commit()

        self._logger.info(
            "staff.invitation.revoked",
            invitation_id=str(command.invitation_id),
            revoked_by=str(command.revoked_by),
        )
