# src/modules/identity/infrastructure/repositories/role_repository.py
import uuid

from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.identity.domain.entities import Role
from src.modules.identity.domain.interfaces import IRoleRepository
from src.modules.identity.infrastructure.models import (
    IdentityRoleModel,
    RoleModel,
)


class RoleRepository(IRoleRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_domain(self, orm: RoleModel) -> Role:
        return Role(
            id=orm.id,
            name=orm.name,
            description=orm.description,
            is_system=orm.is_system,
        )

    async def add(self, role: Role) -> Role:
        orm = RoleModel(
            id=role.id,
            name=role.name,
            description=role.description,
            is_system=role.is_system,
        )
        self._session.add(orm)
        await self._session.flush()
        return self._to_domain(orm)

    async def get(self, role_id: uuid.UUID) -> Role | None:
        orm = await self._session.get(RoleModel, role_id)
        return self._to_domain(orm) if orm else None

    async def get_by_name(self, name: str) -> Role | None:
        stmt = select(RoleModel).where(RoleModel.name == name)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def delete(self, role_id: uuid.UUID) -> None:
        stmt = delete(RoleModel).where(RoleModel.id == role_id)
        await self._session.execute(stmt)

    async def get_all(self) -> list[Role]:
        stmt = select(RoleModel).order_by(RoleModel.name)
        result = await self._session.execute(stmt)
        return [self._to_domain(orm) for orm in result.scalars().all()]

    async def get_identity_role_ids(self, identity_id: uuid.UUID) -> list[uuid.UUID]:
        stmt = select(IdentityRoleModel.role_id).where(IdentityRoleModel.identity_id == identity_id)
        result = await self._session.execute(stmt)
        return [row[0] for row in result.all()]

    async def assign_to_identity(
        self,
        identity_id: uuid.UUID,
        role_id: uuid.UUID,
        assigned_by: uuid.UUID | None = None,
    ) -> None:
        stmt = insert(IdentityRoleModel).values(
            identity_id=identity_id,
            role_id=role_id,
            assigned_by=assigned_by,
        )
        await self._session.execute(stmt)

    async def revoke_from_identity(
        self,
        identity_id: uuid.UUID,
        role_id: uuid.UUID,
    ) -> None:
        stmt = delete(IdentityRoleModel).where(
            IdentityRoleModel.identity_id == identity_id,
            IdentityRoleModel.role_id == role_id,
        )
        await self._session.execute(stmt)
