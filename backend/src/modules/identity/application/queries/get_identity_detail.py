"""Query handler for retrieving a single identity's full detail.

Returns identity info joined with user data and full role objects.
Used by admin interfaces for viewing user profiles.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.exceptions import NotFoundError


class RoleInfo(BaseModel):
    """Read model for role info attached to an identity.

    Attributes:
        id: The role's UUID.
        name: The role's display name.
        description: Optional role description.
        is_system: Whether this is a system-managed role.
    """

    id: uuid.UUID
    name: str
    description: str | None
    is_system: bool


class AdminIdentityDetail(BaseModel):
    """Read model for a single identity's full detail.

    Attributes:
        identity_id: The identity's UUID.
        email: Login email from local_credentials (None for OIDC-only).
        auth_type: Authentication method (LOCAL or OIDC).
        is_active: Whether the identity is currently active.
        first_name: User's first name.
        last_name: User's last name.
        phone: User's phone number, if available.
        roles: List of role info objects.
        created_at: When the identity was created.
        deactivated_at: When the identity was deactivated, if applicable.
        deactivated_by: Identity ID of admin who deactivated, if applicable.
    """

    identity_id: uuid.UUID
    email: str | None
    auth_type: str
    is_active: bool
    first_name: str | None
    last_name: str | None
    phone: str | None
    roles: list[RoleInfo]
    created_at: datetime
    deactivated_at: datetime | None
    deactivated_by: uuid.UUID | None


@dataclass(frozen=True)
class GetIdentityDetailQuery:
    """Query parameters for getting identity detail.

    Attributes:
        identity_id: The identity's UUID to look up.
    """

    identity_id: uuid.UUID


_IDENTITY_DETAIL_SQL = text(
    "SELECT i.id AS identity_id, lc.email, i.type AS auth_type, i.is_active, "
    "u.first_name, u.last_name, u.phone, i.created_at, "
    "i.deactivated_at, i.deactivated_by "
    "FROM identities i "
    "LEFT JOIN local_credentials lc ON lc.identity_id = i.id "
    "LEFT JOIN users u ON u.id = i.id "
    "WHERE i.id = :identity_id"
)

_IDENTITY_ROLES_SQL = text(
    "SELECT r.id, r.name, r.description, r.is_system "
    "FROM roles r "
    "JOIN identity_roles ir ON ir.role_id = r.id "
    "WHERE ir.identity_id = :identity_id "
    "ORDER BY r.name"
)


class GetIdentityDetailHandler:
    """Handles the get-identity-detail query using raw SQL."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(self, query: GetIdentityDetailQuery) -> AdminIdentityDetail:
        """Execute the query and return identity detail.

        Args:
            query: The get identity detail query.

        Returns:
            Full identity detail with roles.

        Raises:
            NotFoundError: If the identity does not exist.
        """
        result = await self._session.execute(
            _IDENTITY_DETAIL_SQL, {"identity_id": query.identity_id}
        )
        row = result.mappings().first()

        if row is None:
            raise NotFoundError(
                message=f"Identity {query.identity_id} not found",
                error_code="IDENTITY_NOT_FOUND",
            )

        # Fetch roles
        role_result = await self._session.execute(
            _IDENTITY_ROLES_SQL, {"identity_id": query.identity_id}
        )
        role_rows = role_result.mappings().all()

        roles = [
            RoleInfo(
                id=rr["id"],
                name=rr["name"],
                description=rr["description"],
                is_system=rr["is_system"],
            )
            for rr in role_rows
        ]

        return AdminIdentityDetail(
            identity_id=row["identity_id"],
            email=row["email"],
            auth_type=row["auth_type"],
            is_active=row["is_active"],
            first_name=row["first_name"] or "",
            last_name=row["last_name"] or "",
            phone=row["phone"],
            roles=roles,
            created_at=row["created_at"],
            deactivated_at=row["deactivated_at"],
            deactivated_by=row["deactivated_by"],
        )
