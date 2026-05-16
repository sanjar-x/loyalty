"""Command handler for re-sending a staff invitation.

A re-send revokes the existing invitation (if still pending) and
mints a fresh one with the same email + role assignments but a new
CSPRNG token and a refreshed TTL. The new invitation becomes the
only valid path for the invitee — the old token (even if not yet
expired) stops working the moment the old invitation flips to
REVOKED.

Use case: admin sent the invite, invitee never clicked the link,
ops needs to extend the window OR the original link leaked into a
log / chat and needs rotating without the admin re-typing email + roles.
"""

import secrets
import uuid
from dataclasses import dataclass

from src.bootstrap.config import settings
from src.modules.identity.domain.entities import StaffInvitation
from src.modules.identity.domain.exceptions import (
    IdentityAlreadyExistsError,
    InvitationAlreadyAcceptedError,
    InvitationNotFoundError,
    InvitationRoleAccountTypeMismatchError,
)
from src.modules.identity.domain.interfaces import (
    IIdentityRepository,
    IRoleRepository,
    IStaffInvitationRepository,
)
from src.modules.identity.domain.value_objects import (
    AccountType,
    InvitationStatus,
)
from src.shared.exceptions import NotFoundError
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class ResendStaffInvitationCommand:
    """Command to re-send (revoke + recreate) a staff invitation.

    Attributes:
        invitation_id: The invitation to re-send. May be in any
            non-ACCEPTED status — pending invitations are revoked
            first, expired / revoked ones are simply superseded.
        requested_by: Identity ID of the admin triggering the resend.
            Stamped onto the new invitation's ``invited_by`` so the
            audit trail reflects who actually re-sent (which may
            differ from the original inviter).
    """

    invitation_id: uuid.UUID
    requested_by: uuid.UUID


@dataclass(frozen=True)
class ResendStaffInvitationResult:
    """Result of a successful re-send.

    Attributes:
        invitation_id: The NEW invitation's UUID (the old one is
            now REVOKED). Front-end should replace the row it was
            showing rather than appending.
        raw_token: The fresh CSPRNG token for the new invite URL.
    """

    invitation_id: uuid.UUID
    raw_token: str


class ResendStaffInvitationHandler:
    """Handles re-sending a staff invitation.

    Order of operations:

    1. Look up the source invitation; reject ``ACCEPTED`` outright
       (you cannot "re-send" to someone who already activated).
    2. Re-validate that the email is still un-registered — a
       different signup path may have claimed it since the original
       invite was sent.
    3. Re-validate each role still exists and targets ``STAFF``.
       Permissions evolve over time; a role that was STAFF when the
       original invite was issued might have been re-targeted.
    4. Revoke the source invitation (no-op if already EXPIRED /
       REVOKED — those are not in ``PENDING`` so ``.revoke()`` would
       raise; we skip the call in that case).
    5. Mint a new invitation with the same email + roles + fresh
       token + fresh TTL pulled from settings.
    """

    def __init__(
        self,
        invitation_repo: IStaffInvitationRepository,
        identity_repo: IIdentityRepository,
        role_repo: IRoleRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._invitation_repo = invitation_repo
        self._identity_repo = identity_repo
        self._role_repo = role_repo
        self._uow = uow
        self._logger = logger.bind(handler="ResendStaffInvitationHandler")

    async def handle(
        self, command: ResendStaffInvitationCommand
    ) -> ResendStaffInvitationResult:
        async with self._uow:
            source = await self._invitation_repo.get(command.invitation_id)
            if source is None:
                raise InvitationNotFoundError()
            if source.status == InvitationStatus.ACCEPTED:
                # Accepting an invitation provisions a real Identity —
                # nothing to "re-send" to. Admin should manage the
                # active account, not the spent invitation.
                raise InvitationAlreadyAcceptedError()

            if await self._identity_repo.email_exists(source.email):
                # Could happen if the invitee signed up through a
                # different path (OIDC, Telegram) between the original
                # invite and the re-send request.
                raise IdentityAlreadyExistsError()

            for role_id in source.role_ids:
                role = await self._role_repo.get(role_id)
                if role is None:
                    raise NotFoundError(
                        message=f"Role {role_id} not found",
                        error_code="ROLE_NOT_FOUND",
                    )
                if (
                    role.target_account_type is not None
                    and role.target_account_type != AccountType.STAFF
                ):
                    raise InvitationRoleAccountTypeMismatchError(role_id=role_id)

            if source.status == InvitationStatus.PENDING:
                source.revoke()
                await self._invitation_repo.update(source)

            raw_token = secrets.token_urlsafe(32)
            fresh = StaffInvitation.create(
                email=source.email,
                invited_by=command.requested_by,
                role_ids=list(source.role_ids),
                raw_token=raw_token,
                ttl_hours=settings.STAFF_INVITATION_TTL_HOURS,
            )
            await self._invitation_repo.add(fresh)
            self._uow.register_aggregate(fresh)
            await self._uow.commit()

        self._logger.info(
            "staff.invitation.resent",
            previous_invitation_id=str(command.invitation_id),
            new_invitation_id=str(fresh.id),
            email=source.email,
            requested_by=str(command.requested_by),
        )
        return ResendStaffInvitationResult(
            invitation_id=fresh.id,
            raw_token=raw_token,
        )
