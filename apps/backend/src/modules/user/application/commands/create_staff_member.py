"""Create staff member command and handler.

Provides the staff member creation workflow triggered by an IdentityRegisteredEvent
(account_type=STAFF) from the Identity module via the outbox consumer.
"""

import uuid
from dataclasses import dataclass

from src.modules.user.domain.entities import StaffMember
from src.modules.user.domain.interfaces import IStaffMemberRepository
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class CreateStaffMemberCommand:
    """Command to create a staff member from an invitation acceptance.

    Attributes:
        identity_id: The Identity aggregate ID (shared PK).
        profile_email: Display email.
        invited_by: Identity ID of the admin who invited.
        first_name: First name.
        last_name: Last name.
    """

    identity_id: uuid.UUID
    profile_email: str | None = None
    invited_by: uuid.UUID | None = None
    first_name: str = ""
    last_name: str = ""


class CreateStaffMemberHandler:
    """Handler for creating a StaffMember from an identity registration event.

    Idempotent: if a staff member with the given ID already exists, creation is skipped.
    """

    def __init__(
        self,
        staff_repo: IStaffMemberRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._staff_repo = staff_repo
        self._uow = uow
        self._logger = logger.bind(handler="CreateStaffMemberHandler")

    async def handle(self, command: CreateStaffMemberCommand) -> None:
        """Execute staff member creation.

        Args:
            command: The creation command.
        """
        async with self._uow:
            existing = await self._staff_repo.get(command.identity_id)
            if existing:
                self._logger.warning(
                    "staff_member.already_exists",
                    identity_id=str(command.identity_id),
                )
                return

            staff = StaffMember.create_from_invitation(
                identity_id=command.identity_id,
                profile_email=command.profile_email,
                invited_by=command.invited_by or command.identity_id,
                first_name=command.first_name,
                last_name=command.last_name,
            )
            await self._staff_repo.add(staff)
            await self._uow.commit()

        self._logger.info(
            "staff_member.created",
            staff_id=str(command.identity_id),
        )
