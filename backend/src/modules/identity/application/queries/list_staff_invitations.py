"""Query handler for listing staff invitations with pagination and filtering.

Returns a paginated list of staff invitations with role names and inviter info.
Used by admin interfaces for invitation management.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class InvitationListItem(BaseModel):
    """Read model for a single staff invitation in the paginated list.

    Attributes:
        id: The invitation's UUID.
        email: Email address the invitation was sent to.
        status: Current invitation status (PENDING, ACCEPTED, REVOKED, EXPIRED).
        invited_by_email: Email of the admin who created the invitation.
        roles: List of role names assigned to this invitation.
        created_at: When the invitation was created.
        expires_at: When the invitation expires.
    """

    id: uuid.UUID
    email: str
    status: str
    invited_by_email: str | None
    roles: list[str]
    created_at: datetime
    expires_at: datetime


class InvitationListResult(BaseModel):
    """Read model for the paginated invitation list response.

    Attributes:
        items: List of invitation items for the current page.
        total: Total number of matching invitations.
        offset: Current offset.
        limit: Page size.
    """

    items: list[InvitationListItem]
    total: int
    offset: int
    limit: int


@dataclass(frozen=True)
class ListStaffInvitationsQuery:
    """Query parameters for listing staff invitations.

    Attributes:
        offset: Pagination offset.
        limit: Page size.
        status: Optional filter by invitation status.
    """

    offset: int = 0
    limit: int = 20
    status: str | None = None


class ListStaffInvitationsHandler:
    """Handles listing staff invitations with pagination and filtering."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(self, query: ListStaffInvitationsQuery) -> InvitationListResult:
        """Execute the query and return a paginated invitation list.

        Args:
            query: The list staff invitations query parameters.

        Returns:
            Paginated list of staff invitations with role names.
        """
        where_clauses: list[str] = []
        params: dict[str, object] = {}

        if query.status is not None:
            where_clauses.append("si.status = :status")
            params["status"] = query.status

        where_sql = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

        # Count total
        count_sql = "SELECT COUNT(*) FROM staff_invitations si" + where_sql
        count_result = await self._session.execute(text(count_sql), params)
        total = count_result.scalar() or 0

        if total == 0:
            return InvitationListResult(items=[], total=0, offset=query.offset, limit=query.limit)

        # Fetch page
        list_sql = (
            "SELECT si.id, si.email, si.status, si.created_at, si.expires_at, "
            "lc.email AS invited_by_email "
            "FROM staff_invitations si "
            "LEFT JOIN local_credentials lc ON lc.identity_id = si.invited_by"
            + where_sql
            + " ORDER BY si.created_at DESC LIMIT :limit OFFSET :offset"
        )
        params["limit"] = query.limit
        params["offset"] = query.offset

        list_result = await self._session.execute(text(list_sql), params)
        rows = list_result.mappings().all()

        if not rows:
            return InvitationListResult(
                items=[], total=total, offset=query.offset, limit=query.limit
            )

        # Fetch role names for each invitation
        invitation_ids = [row["id"] for row in rows]
        roles_sql = text(
            "SELECT sir.invitation_id, r.name "
            "FROM staff_invitation_roles sir "
            "JOIN roles r ON r.id = sir.role_id "
            "WHERE sir.invitation_id = ANY(:invitation_ids)"
        )
        roles_result = await self._session.execute(roles_sql, {"invitation_ids": invitation_ids})
        roles_rows = roles_result.mappings().all()

        roles_by_invitation: dict[uuid.UUID, list[str]] = {}
        for rr in roles_rows:
            roles_by_invitation.setdefault(rr["invitation_id"], []).append(rr["name"])

        items = [
            InvitationListItem(
                id=row["id"],
                email=row["email"],
                status=row["status"],
                invited_by_email=row["invited_by_email"],
                roles=roles_by_invitation.get(row["id"], []),
                created_at=row["created_at"],
                expires_at=row["expires_at"],
            )
            for row in rows
        ]

        return InvitationListResult(
            items=items, total=total, offset=query.offset, limit=query.limit
        )
