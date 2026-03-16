# src/modules/identity/infrastructure/repositories/permission_repository.py
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.identity.domain.entities import Permission
from src.modules.identity.domain.interfaces import IPermissionRepository
from src.modules.identity.infrastructure.models import PermissionModel


class PermissionRepository(IPermissionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_domain(self, orm: PermissionModel) -> Permission:
        return Permission(
            id=orm.id,
            codename=orm.codename,
            resource=orm.resource,
            action=orm.action,
            description=orm.description,
        )

    async def get_all(self) -> list[Permission]:
        stmt = select(PermissionModel).order_by(PermissionModel.codename)
        result = await self._session.execute(stmt)
        return [self._to_domain(orm) for orm in result.scalars().all()]

    async def get_by_codename(self, codename: str) -> Permission | None:
        stmt = select(PermissionModel).where(PermissionModel.codename == codename)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None
