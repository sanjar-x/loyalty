"""Query handler for getting a single staff member's detail.

Returns the full detail of a staff member including identity info,
staff-specific fields, and assigned roles with metadata.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.exceptions import NotFoundError


class StaffRoleInfo(BaseModel):
    """Read model for a role assigned to a staff member.

    Attributes:
        id: The role's UUID.
        name: The role's display name.
        description: Optional description of the role.
        is_system: Whether this is a system-managed role.
    """

    id: uuid.UUID
    name: str
    description: str | None
    is_system: bool


class StaffDetail(BaseModel):
    """Read model for a staff member's full detail view.

    Attributes:
        identity_id: The identity's UUID.
        email: Login email from local_credentials (None for OIDC-only).
        auth_type: Authentication method (LOCAL or OIDC).
        is_active: Whether the identity is currently active.
        first_name: Staff member's first name.
        last_name: Staff member's last name.
        position: Job position/title.
        department: Department within the organization.
        roles: List of roles with full metadata.
        created_at: When the identity was created.
        deactivated_at: When the identity was deactivated, if applicable.
        deactivated_by: UUID of the admin who deactivated this identity.
        invited_by: UUID of the admin who invited this staff member.
    """

    identity_id: uuid.UUID
    email: str | None
    auth_type: str
    is_active: bool
    first_name: str
    last_name: str
    position: str | None
    department: str | None
    roles: list[StaffRoleInfo]
    created_at: datetime
    deactivated_at: datetime | None
    deactivated_by: uuid.UUID | None
    invited_by: uuid.UUID


@dataclass(frozen=True)
class GetStaffDetailQuery:
    """Query parameters for getting a staff member's detail.

    Attributes:
        identity_id: The identity UUID of the staff member to fetch.
    """

    identity_id: uuid.UUID


class GetStaffDetailHandler:
    """Handles fetching a single staff member's full detail."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(self, query: GetStaffDetailQuery) -> StaffDetail:
        """Fetch the staff member's detail by identity ID.

        Args:
            query: The get staff detail query with the identity ID.

        Returns:
            Full staff member detail including roles.

        Raises:
            NotFoundError: If no staff member with the given ID exists.
        """
        sql = text(
            "SELECT i.id AS identity_id, lc.email, i.type AS auth_type, "
            "i.is_active, sm.first_name, sm.last_name, sm.position, sm.department, "
            "sm.invited_by, i.created_at, i.deactivated_at, i.deactivated_by "
            "FROM identities i "
            "LEFT JOIN local_credentials lc ON lc.identity_id = i.id "
            "JOIN staff_members sm ON sm.id = i.id "
            "WHERE i.id = :identity_id AND i.account_type = 'STAFF'"
        )
        result = await self._session.execute(sql, {"identity_id": query.identity_id})
        row = result.mappings().first()
        if row is None:
            raise NotFoundError(
                message="Staff member not found",
                error_code="STAFF_NOT_FOUND",
            )

        # Fetch roles with full metadata
        roles_sql = text(
            "SELECT r.id, r.name, r.description, r.is_system "
            "FROM identity_roles ir JOIN roles r ON r.id = ir.role_id "
            "WHERE ir.identity_id = :identity_id"
        )
        roles_result = await self._session.execute(roles_sql, {"identity_id": query.identity_id})
        roles = [
            StaffRoleInfo(
                id=rr["id"],
                name=rr["name"],
                description=rr["description"],
                is_system=rr["is_system"],
            )
            for rr in roles_result.mappings().all()
        ]

        return StaffDetail(
            identity_id=row["identity_id"],
            email=row["email"],
            auth_type=row["auth_type"],
            is_active=row["is_active"],
            first_name=row["first_name"] or "",
            last_name=row["last_name"] or "",
            position=row["position"],
            department=row["department"],
            roles=roles,
            created_at=row["created_at"],
            deactivated_at=row["deactivated_at"],
            deactivated_by=row["deactivated_by"],
            invited_by=row["invited_by"],
        )
