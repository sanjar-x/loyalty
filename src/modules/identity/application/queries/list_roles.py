"""Query handler for listing all roles with their associated permissions.

Fetches roles and their permission codenames in two queries, then assembles
the result. Used by admin interfaces for role management.
"""

import uuid

from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class RoleWithPermissions(BaseModel):
    """Read model for a role with its associated permission codenames.

    Attributes:
        id: The role's UUID.
        name: The role's display name.
        description: Optional role description.
        is_system: Whether this is a system-managed role.
        permissions: List of permission codenames assigned to this role.
    """

    id: uuid.UUID
    name: str
    description: str | None
    is_system: bool
    permissions: list[str]


_LIST_ROLES_SQL = text(
    "SELECT r.id, r.name, r.description, r.is_system FROM roles r ORDER BY r.name"
)

_ROLE_PERMISSIONS_SQL = text(
    "SELECT rp.role_id, p.codename "
    "FROM role_permissions rp "
    "JOIN permissions p ON p.id = rp.permission_id "
    "WHERE rp.role_id = ANY(:role_ids)"
)


class ListRolesHandler:
    """Handles the list-roles query using raw SQL with permission aggregation."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(self) -> list[RoleWithPermissions]:
        """Execute the query and return all roles with their permissions.

        Returns:
            List of all roles with associated permission codenames, ordered by name.
        """
        result = await self._session.execute(_LIST_ROLES_SQL)
        rows = result.mappings().all()

        if not rows:
            return []

        role_ids = [row["id"] for row in rows]
        perm_result = await self._session.execute(_ROLE_PERMISSIONS_SQL, {"role_ids": role_ids})
        perm_rows = perm_result.mappings().all()

        perms_by_role: dict[uuid.UUID, list[str]] = {}
        for pr in perm_rows:
            perms_by_role.setdefault(pr["role_id"], []).append(pr["codename"])

        return [
            RoleWithPermissions(
                id=row["id"],
                name=row["name"],
                description=row["description"],
                is_system=row["is_system"],
                permissions=perms_by_role.get(row["id"], []),
            )
            for row in rows
        ]
