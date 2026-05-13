"""Query handler for listing all available permissions.

Returns all permission definitions from the database, grouped by resource.
Used by admin interfaces to display assignable permissions.
"""

import uuid

from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class PermissionInfo(BaseModel):
    """Read model for a permission definition.

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


class PermissionGroup(BaseModel):
    """Read model for a group of permissions sharing the same resource.

    Attributes:
        resource: The resource name (e.g. "brands", "roles").
        permissions: List of permissions for this resource.
    """

    resource: str
    permissions: list[PermissionInfo]


_LIST_PERMISSIONS_SQL = text(
    "SELECT id, codename, resource, action, description FROM permissions ORDER BY codename"
)


class ListPermissionsHandler:
    """Handles the list-permissions query using raw SQL."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(self) -> list[PermissionGroup]:
        """Execute the query and return all permissions grouped by resource.

        Returns:
            List of permission groups sorted by resource name.
        """
        result = await self._session.execute(_LIST_PERMISSIONS_SQL)
        rows = result.mappings().all()

        groups: dict[str, list[PermissionInfo]] = {}
        for row in rows:
            info = PermissionInfo(
                id=row["id"],
                codename=row["codename"],
                resource=row["resource"],
                action=row["action"],
                description=row["description"],
            )
            groups.setdefault(info.resource, []).append(info)

        return [
            PermissionGroup(resource=resource, permissions=perms)
            for resource, perms in sorted(groups.items())
        ]
