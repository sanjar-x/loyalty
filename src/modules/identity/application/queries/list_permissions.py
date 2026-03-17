"""Query handler for listing all available permissions.

Returns all permission definitions from the database, ordered by codename.
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


_LIST_PERMISSIONS_SQL = text(
    "SELECT id, codename, resource, action, description FROM permissions ORDER BY codename"
)


class ListPermissionsHandler:
    """Handles the list-permissions query using raw SQL."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(self) -> list[PermissionInfo]:
        """Execute the query and return all permissions.

        Returns:
            List of all permissions ordered by codename.
        """
        result = await self._session.execute(_LIST_PERMISSIONS_SQL)
        return [
            PermissionInfo(
                id=row["id"],
                codename=row["codename"],
                resource=row["resource"],
                action=row["action"],
                description=row["description"],
            )
            for row in result.mappings().all()
        ]
