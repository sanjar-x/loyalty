"""Query handler for retrieving roles assigned to an identity.

Executes a direct SQL join between roles and identity_roles tables,
bypassing the domain layer for read-optimized performance (CQRS read side).
"""

import uuid
from dataclasses import dataclass

from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class IdentityRoleInfo(BaseModel):
    """Read model for a role assigned to an identity.

    Attributes:
        role_id: The role's UUID.
        role_name: The role's display name.
        is_system: Whether this is a system-managed role.
    """

    role_id: uuid.UUID
    role_name: str
    is_system: bool


@dataclass(frozen=True)
class GetIdentityRolesQuery:
    """Query to retrieve all roles assigned to an identity.

    Attributes:
        identity_id: The identity whose roles to retrieve.
    """

    identity_id: uuid.UUID


_IDENTITY_ROLES_SQL = text(
    "SELECT r.id AS role_id, r.name AS role_name, r.is_system "
    "FROM roles r "
    "JOIN identity_roles ir ON ir.role_id = r.id "
    "WHERE ir.identity_id = :identity_id "
    "ORDER BY r.name"
)


class GetIdentityRolesHandler:
    """Handles the get-identity-roles query using raw SQL."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(self, query: GetIdentityRolesQuery) -> list[IdentityRoleInfo]:
        """Execute the query and return roles for the given identity.

        Args:
            query: The get-identity-roles query.

        Returns:
            List of roles assigned to the identity, ordered by name.
        """
        result = await self._session.execute(
            _IDENTITY_ROLES_SQL, {"identity_id": query.identity_id}
        )
        return [
            IdentityRoleInfo(
                role_id=row["role_id"],
                role_name=row["role_name"],
                is_system=row["is_system"],
            )
            for row in result.mappings().all()
        ]
