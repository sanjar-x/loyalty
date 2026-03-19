"""Command handler for inviting a new staff member."""

import secrets
import uuid
from dataclasses import dataclass

from src.modules.identity.domain.entities import StaffInvitation
from src.modules.identity.domain.exceptions import (
    ActiveInvitationExistsError,
    IdentityAlreadyExistsError,
)
from src.modules.identity.domain.interfaces import (
    IIdentityRepository,
    IRoleRepository,
    IStaffInvitationRepository,
)
from src.shared.exceptions import NotFoundError
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class InviteStaffCommand:
    """Command to invite a new staff member.

    Attributes:
        email: Email address of the invitee.
        role_ids: Roles to pre-assign upon acceptance.
        invited_by: Identity ID of the admin sending the invitation.
    """

    email: str
    role_ids: list[uuid.UUID]
    invited_by: uuid.UUID


@dataclass(frozen=True)
class InviteStaffResult:
    """Result of a successful staff invitation.

    Attributes:
        invitation_id: The new invitation's UUID.
        raw_token: The raw invite token (to be sent to invitee).
    """

    invitation_id: uuid.UUID
    raw_token: str


class InviteStaffHandler:
    """Handles staff invitation creation."""

    def __init__(
        self,
        identity_repo: IIdentityRepository,
        role_repo: IRoleRepository,
        invitation_repo: IStaffInvitationRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._identity_repo = identity_repo
        self._role_repo = role_repo
        self._invitation_repo = invitation_repo
        self._uow = uow
        self._logger = logger.bind(handler="InviteStaffHandler")

    async def handle(self, command: InviteStaffCommand) -> InviteStaffResult:
        """Execute the invite staff command.

        Args:
            command: The invitation command.

        Returns:
            Result with invitation ID and raw token.

        Raises:
            IdentityAlreadyExistsError: If the email is already registered.
            ActiveInvitationExistsError: If a pending invitation exists for this email.
            NotFoundError: If any of the role IDs don't exist.
        """
        async with self._uow:
            # Check email not already registered
            if await self._identity_repo.email_exists(command.email):
                raise IdentityAlreadyExistsError()

            # Check no pending invitation for this email
            existing = await self._invitation_repo.get_pending_by_email(command.email)
            if existing:
                raise ActiveInvitationExistsError()

            # Validate all roles exist
            for role_id in command.role_ids:
                role = await self._role_repo.get(role_id)
                if role is None:
                    raise NotFoundError(
                        message=f"Role {role_id} not found",
                        error_code="ROLE_NOT_FOUND",
                    )

            # Create invitation
            raw_token = secrets.token_urlsafe(32)
            invitation = StaffInvitation.create(
                email=command.email,
                invited_by=command.invited_by,
                role_ids=command.role_ids,
                raw_token=raw_token,
            )
            await self._invitation_repo.add(invitation)
            self._uow.register_aggregate(invitation)
            await self._uow.commit()

        self._logger.info(
            "staff.invited",
            invitation_id=str(invitation.id),
            email=command.email,
        )
        return InviteStaffResult(
            invitation_id=invitation.id,
            raw_token=raw_token,
        )
