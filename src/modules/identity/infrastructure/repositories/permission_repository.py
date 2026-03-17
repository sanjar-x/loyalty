"""SQLAlchemy implementation of the Permission repository.

Maps between PermissionModel ORM objects and domain Permission entities
using the Data Mapper pattern.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.identity.domain.entities import Permission
from src.modules.identity.domain.interfaces import IPermissionRepository
from src.modules.identity.infrastructure.models import PermissionModel


class PermissionRepository(IPermissionRepository):
    """Concrete repository for Permission persistence via SQLAlchemy."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_domain(self, orm: PermissionModel) -> Permission:
        """Map a PermissionModel ORM instance to a domain entity.

        Args:
            orm: The ORM model instance.

        Returns:
            The corresponding domain entity.
        """
        return Permission(
            id=orm.id,
            codename=orm.codename,
            resource=orm.resource,
            action=orm.action,
            description=orm.description,
        )

    async def get_all(self) -> list[Permission]:
        """Retrieve all permissions ordered by codename.

        Returns:
            List of all permissions.
        """
        stmt = select(PermissionModel).order_by(PermissionModel.codename)
        result = await self._session.execute(stmt)
        return [self._to_domain(orm) for orm in result.scalars().all()]

    async def get_by_codename(self, codename: str) -> Permission | None:
        """Retrieve a permission by its codename.

        Args:
            codename: The permission codename (e.g. "orders:read").

        Returns:
            The permission if found, or None.
        """
        stmt = select(PermissionModel).where(PermissionModel.codename == codename)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None
