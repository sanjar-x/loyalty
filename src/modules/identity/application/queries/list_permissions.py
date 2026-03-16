# src/modules/identity/application/queries/list_permissions.py
import uuid

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.identity.infrastructure.models import PermissionModel


class PermissionInfo(BaseModel):
    id: uuid.UUID
    codename: str
    resource: str
    action: str
    description: str | None


class ListPermissionsHandler:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(self) -> list[PermissionInfo]:
        stmt = select(PermissionModel).order_by(PermissionModel.codename)
        result = await self._session.execute(stmt)
        return [
            PermissionInfo(
                id=p.id,
                codename=p.codename,
                resource=p.resource,
                action=p.action,
                description=p.description,
            )
            for p in result.scalars().all()
        ]
