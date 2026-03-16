# src/modules/identity/application/queries/get_session_permissions.py
import uuid
from dataclasses import dataclass

from src.shared.interfaces.security import IPermissionResolver


@dataclass(frozen=True)
class GetSessionPermissionsQuery:
    session_id: uuid.UUID


class GetSessionPermissionsHandler:
    def __init__(self, permission_resolver: IPermissionResolver) -> None:
        self._resolver = permission_resolver

    async def handle(self, query: GetSessionPermissionsQuery) -> frozenset[str]:
        return await self._resolver.get_permissions(query.session_id)
