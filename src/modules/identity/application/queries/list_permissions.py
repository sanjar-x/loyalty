# src/modules/identity/application/queries/list_permissions.py
import uuid

from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class PermissionInfo(BaseModel):
    id: uuid.UUID
    codename: str
    resource: str
    action: str
    description: str | None


_LIST_PERMISSIONS_SQL = text(
    "SELECT id, codename, resource, action, description FROM permissions ORDER BY codename"
)


class ListPermissionsHandler:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(self) -> list[PermissionInfo]:
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
