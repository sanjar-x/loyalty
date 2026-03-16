# src/modules/identity/application/queries/get_identity_roles.py
import uuid
from dataclasses import dataclass

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.identity.infrastructure.models import IdentityRoleModel, RoleModel


class IdentityRoleInfo(BaseModel):
    role_id: uuid.UUID
    role_name: str
    is_system: bool


@dataclass(frozen=True)
class GetIdentityRolesQuery:
    identity_id: uuid.UUID


class GetIdentityRolesHandler:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(self, query: GetIdentityRolesQuery) -> list[IdentityRoleInfo]:
        stmt = (
            select(RoleModel)
            .join(IdentityRoleModel, IdentityRoleModel.role_id == RoleModel.id)
            .where(IdentityRoleModel.identity_id == query.identity_id)
            .order_by(RoleModel.name)
        )
        result = await self._session.execute(stmt)
        return [
            IdentityRoleInfo(
                role_id=role.id,
                role_name=role.name,
                is_system=role.is_system,
            )
            for role in result.scalars().all()
        ]
