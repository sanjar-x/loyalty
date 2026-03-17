# src/modules/identity/application/queries/list_roles.py
import uuid

from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class RoleWithPermissions(BaseModel):
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
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(self) -> list[RoleWithPermissions]:
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
