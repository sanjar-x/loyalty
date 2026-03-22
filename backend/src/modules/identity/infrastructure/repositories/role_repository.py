"""SQLAlchemy implementation of the Role repository.

Maps between RoleModel/IdentityRoleModel ORM objects and domain Role
entities using the Data Mapper pattern. Also handles identity-role
association management.
"""

import uuid

from sqlalchemy import delete, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.identity.domain.entities import Role
from src.modules.identity.domain.interfaces import IRoleRepository
from src.modules.identity.domain.value_objects import AccountType
from src.modules.identity.infrastructure.models import (
    IdentityModel,
    IdentityRoleModel,
    RoleModel,
    RolePermissionModel,
)


class RoleRepository(IRoleRepository):
    """Concrete repository for Role persistence and identity-role associations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_domain(self, orm: RoleModel) -> Role:
        """Map a RoleModel ORM instance to a domain entity.

        Args:
            orm: The ORM model instance.

        Returns:
            The corresponding domain entity.
        """
        return Role(
            id=orm.id,
            name=orm.name,
            description=orm.description,
            is_system=orm.is_system,
            target_account_type=AccountType(orm.target_account_type)
            if orm.target_account_type
            else None,
        )

    async def add(self, role: Role) -> Role:
        """Persist a new role.

        Args:
            role: The domain role to persist.

        Returns:
            The persisted role.
        """
        orm = RoleModel(
            id=role.id,
            name=role.name,
            description=role.description,
            is_system=role.is_system,
            target_account_type=role.target_account_type.value
            if role.target_account_type
            else None,
        )
        self._session.add(orm)
        await self._session.flush()
        return self._to_domain(orm)

    async def get(self, role_id: uuid.UUID) -> Role | None:
        """Retrieve a role by its UUID.

        Args:
            role_id: The role's UUID.

        Returns:
            The role if found, or None.
        """
        orm = await self._session.get(RoleModel, role_id)
        return self._to_domain(orm) if orm else None

    async def get_by_name(self, name: str) -> Role | None:
        """Retrieve a role by its unique name.

        Args:
            name: The role name.

        Returns:
            The role if found, or None.
        """
        stmt = select(RoleModel).where(RoleModel.name == name)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def delete(self, role_id: uuid.UUID) -> None:
        """Delete a role by its UUID.

        Args:
            role_id: The role's UUID.
        """
        stmt = delete(RoleModel).where(RoleModel.id == role_id)
        await self._session.execute(stmt)

    async def get_all(self) -> list[Role]:
        """Retrieve all roles ordered by name.

        Returns:
            List of all roles.
        """
        stmt = select(RoleModel).order_by(RoleModel.name)
        result = await self._session.execute(stmt)
        return [self._to_domain(orm) for orm in result.scalars().all()]

    async def get_identity_role_ids(self, identity_id: uuid.UUID) -> list[uuid.UUID]:
        """Retrieve role IDs assigned to an identity.

        Args:
            identity_id: The identity to query.

        Returns:
            List of assigned role UUIDs.
        """
        stmt = select(IdentityRoleModel.role_id).where(IdentityRoleModel.identity_id == identity_id)
        result = await self._session.execute(stmt)
        return [row[0] for row in result.all()]

    async def is_role_assigned(self, identity_id: uuid.UUID, role_id: uuid.UUID) -> bool:
        """Check if a role is already assigned to an identity."""
        stmt = select(IdentityRoleModel.identity_id).where(
            IdentityRoleModel.identity_id == identity_id,
            IdentityRoleModel.role_id == role_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def assign_to_identity(
        self,
        identity_id: uuid.UUID,
        role_id: uuid.UUID,
        assigned_by: uuid.UUID | None = None,
    ) -> None:
        """Assign a role to an identity by inserting an identity_roles row.

        Args:
            identity_id: The identity to assign the role to.
            role_id: The role to assign.
            assigned_by: The admin identity who performed the assignment, if any.
        """
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
        """Revoke a role from an identity by deleting the identity_roles row.

        Args:
            identity_id: The identity to revoke the role from.
            role_id: The role to revoke.
        """
        stmt = delete(IdentityRoleModel).where(
            IdentityRoleModel.identity_id == identity_id,
            IdentityRoleModel.role_id == role_id,
        )
        await self._session.execute(stmt)

    async def update(self, role: Role) -> None:
        """Update an existing role's name and/or description."""
        stmt = (
            update(RoleModel)
            .where(RoleModel.id == role.id)
            .values(name=role.name, description=role.description)
        )
        await self._session.execute(stmt)

    async def count_identities_with_role(self, role_name: str) -> int:
        """Count active identities that have a role with the given name.

        Uses FOR UPDATE on identity_roles rows to serialize concurrent
        operations that depend on this count (e.g. last-admin protection).
        """
        stmt = (
            select(IdentityRoleModel.identity_id)
            .join(RoleModel, RoleModel.id == IdentityRoleModel.role_id)
            .join(IdentityModel, IdentityModel.id == IdentityRoleModel.identity_id)
            .where(RoleModel.name == role_name, IdentityModel.is_active.is_(True))
            .with_for_update(of=IdentityRoleModel)
        )
        result = await self._session.execute(stmt)
        return len(result.all())

    async def get_identity_ids_with_role(self, role_id: uuid.UUID) -> list[uuid.UUID]:
        """Get all identity IDs that have this role assigned."""
        stmt = select(IdentityRoleModel.identity_id).where(IdentityRoleModel.role_id == role_id)
        result = await self._session.execute(stmt)
        return [row[0] for row in result.all()]

    async def set_permissions(self, role_id: uuid.UUID, permission_ids: list[uuid.UUID]) -> None:
        """Full-replace permissions for a role."""
        del_stmt = delete(RolePermissionModel).where(RolePermissionModel.role_id == role_id)
        await self._session.execute(del_stmt)
        if permission_ids:
            values = [{"role_id": role_id, "permission_id": pid} for pid in permission_ids]
            ins_stmt = insert(RolePermissionModel).values(values)
            await self._session.execute(ins_stmt)
