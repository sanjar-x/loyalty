# src/modules/identity/application/queries/list_roles.py
import uuid

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.modules.identity.infrastructure.models import RoleModel


class RoleWithPermissions(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    is_system: bool
    permissions: list[str]


class ListRolesHandler:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(self) -> list[RoleWithPermissions]:
        stmt = (
            select(RoleModel)
            .options(selectinload(RoleModel.permissions))
            .order_by(RoleModel.name)
        )
        result = await self._session.execute(stmt)
        roles = result.unique().scalars().all()

        return [
            RoleWithPermissions(
                id=role.id,
                name=role.name,
                description=role.description,
                is_system=role.is_system,
                permissions=[p.codename for p in role.permissions],
            )
            for role in roles
        ]
