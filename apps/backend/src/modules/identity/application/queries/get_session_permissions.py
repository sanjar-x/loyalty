"""Query handler for retrieving permissions associated with a session.

Delegates to the IPermissionResolver (cache-aside pattern with Redis)
to return the effective permission codenames for the given session.
"""

import uuid
from dataclasses import dataclass

from src.shared.interfaces.security import IPermissionResolver


@dataclass(frozen=True)
class GetSessionPermissionsQuery:
    """Query to retrieve effective permissions for a session.

    Attributes:
        session_id: The session whose permissions to resolve.
    """

    session_id: uuid.UUID


class GetSessionPermissionsHandler:
    """Handles the get-session-permissions query via the permission resolver."""

    def __init__(self, permission_resolver: IPermissionResolver) -> None:
        self._resolver = permission_resolver

    async def handle(self, query: GetSessionPermissionsQuery) -> frozenset[str]:
        """Resolve and return the effective permissions for the session.

        Args:
            query: The get-session-permissions query.

        Returns:
            A frozen set of permission codename strings.
        """
        return await self._resolver.get_permissions(query.session_id)
