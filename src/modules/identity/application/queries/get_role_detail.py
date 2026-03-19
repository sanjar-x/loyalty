"""Query handler for retrieving a single role's full detail with permissions.

Returns role info with all associated permission objects.
Used by admin interfaces for role management.
"""

import uuid
from dataclasses import dataclass

from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.exceptions import NotFoundError


class PermissionDetail(BaseModel):
    """Read model for a permission detail.

    Attributes:
        id: The permission's UUID.
        codename: Permission codename in 'resource:action' format.
        resource: The resource component of the codename.
        action: The action component of the codename.
        description: Optional human-readable description.
    """

    id: uuid.UUID
    codename: str
    resource: str
    action: str
    description: str | None


class RoleDetail(BaseModel):
    """Read model for a single role's full detail.

    Attributes:
        id: The role's UUID.
        name: The role's display name.
        description: Optional role description.
        is_system: Whether this is a system-managed role.
        permissions: List of permission detail objects.
    """

    id: uuid.UUID
    name: str
    description: str | None
    is_system: bool
    permissions: list[PermissionDetail]


@dataclass(frozen=True)
class GetRoleDetailQuery:
    """Query parameters for getting role detail.

    Attributes:
        role_id: The role's UUID to look up.
    """

    role_id: uuid.UUID


_ROLE_SQL = text("SELECT id, name, description, is_system FROM roles WHERE id = :role_id")

_ROLE_PERMS_SQL = text(
    "SELECT p.id, p.codename, p.resource, p.action, p.description "
    "FROM permissions p "
    "JOIN role_permissions rp ON rp.permission_id = p.id "
    "WHERE rp.role_id = :role_id "
    "ORDER BY p.codename"
)


class GetRoleDetailHandler:
    """Handles the get-role-detail query using raw SQL."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(self, query: GetRoleDetailQuery) -> RoleDetail:
        """Execute the query and return role detail with permissions.

        Args:
            query: The get role detail query.

        Returns:
            Full role detail with permissions.

        Raises:
            NotFoundError: If the role does not exist.
        """
        result = await self._session.execute(_ROLE_SQL, {"role_id": query.role_id})
        row = result.mappings().first()

        if row is None:
            raise NotFoundError(
                message=f"Role {query.role_id} not found",
                error_code="ROLE_NOT_FOUND",
            )

        perm_result = await self._session.execute(_ROLE_PERMS_SQL, {"role_id": query.role_id})
        perm_rows = perm_result.mappings().all()

        permissions = [
            PermissionDetail(
                id=pr["id"],
                codename=pr["codename"],
                resource=pr["resource"],
                action=pr["action"],
                description=pr["description"],
            )
            for pr in perm_rows
        ]

        return RoleDetail(
            id=row["id"],
            name=row["name"],
            description=row["description"],
            is_system=row["is_system"],
            permissions=permissions,
        )
