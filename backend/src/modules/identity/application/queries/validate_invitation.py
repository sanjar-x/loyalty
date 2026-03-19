"""Query handler for validating a staff invitation token.

Checks that the token corresponds to a valid, pending, non-expired invitation
and returns the invitation info for the accept form.
"""

from dataclasses import dataclass
from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.identity.domain.entities import StaffInvitation
from src.modules.identity.domain.exceptions import InvitationNotFoundError


class InvitationInfo(BaseModel):
    """Read model for a validated staff invitation.

    Attributes:
        email: Email address the invitation was sent to.
        roles: List of role names pre-assigned to this invitation.
        expires_at: When the invitation expires.
    """

    email: str
    roles: list[str]
    expires_at: datetime


@dataclass(frozen=True)
class ValidateInvitationQuery:
    """Query parameters for validating a staff invitation.

    Attributes:
        raw_token: The raw invitation token from the URL.
    """

    raw_token: str


class ValidateInvitationHandler:
    """Validates an invitation token and returns info for the accept form."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(self, query: ValidateInvitationQuery) -> InvitationInfo:
        """Validate the invitation token and return invitation details.

        Args:
            query: The validate invitation query with the raw token.

        Returns:
            Invitation info including email, roles, and expiry.

        Raises:
            InvitationNotFoundError: If no valid pending invitation matches the token.
        """
        token_hash = StaffInvitation.hash_token(query.raw_token)

        sql = text(
            "SELECT si.id, si.email, si.status, si.expires_at "
            "FROM staff_invitations si "
            "WHERE si.token_hash = :token_hash "
            "AND si.status = 'PENDING' "
            "AND si.expires_at > now()"
        )
        result = await self._session.execute(sql, {"token_hash": token_hash})
        row = result.mappings().first()
        if row is None:
            raise InvitationNotFoundError()

        roles_sql = text(
            "SELECT r.name FROM staff_invitation_roles sir "
            "JOIN roles r ON r.id = sir.role_id "
            "WHERE sir.invitation_id = :invitation_id"
        )
        roles_result = await self._session.execute(roles_sql, {"invitation_id": row["id"]})
        role_names = [r["name"] for r in roles_result.mappings().all()]

        return InvitationInfo(
            email=row["email"],
            roles=role_names,
            expires_at=row["expires_at"],
        )
