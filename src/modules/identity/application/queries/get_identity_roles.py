# src/modules/identity/application/queries/get_identity_roles.py
import uuid
from dataclasses import dataclass

from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class IdentityRoleInfo(BaseModel):
    role_id: uuid.UUID
    role_name: str
    is_system: bool


@dataclass(frozen=True)
class GetIdentityRolesQuery:
    identity_id: uuid.UUID


_IDENTITY_ROLES_SQL = text(
    "SELECT r.id AS role_id, r.name AS role_name, r.is_system "
    "FROM roles r "
    "JOIN identity_roles ir ON ir.role_id = r.id "
    "WHERE ir.identity_id = :identity_id "
    "ORDER BY r.name"
)


class GetIdentityRolesHandler:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(self, query: GetIdentityRolesQuery) -> list[IdentityRoleInfo]:
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
