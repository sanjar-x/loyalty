"""Cross-table username uniqueness checker."""

import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.user.domain.interfaces import IUsernameUniquenessChecker

_CHECK_SQL = text("""
    SELECT 1 FROM (
        SELECT id FROM customers
        WHERE LOWER(username) = LOWER(:username) AND (:exclude_id IS NULL OR id != :exclude_id)
        UNION ALL
        SELECT id FROM staff_members
        WHERE LOWER(username) = LOWER(:username) AND (:exclude_id IS NULL OR id != :exclude_id)
    ) t
    LIMIT 1
""")


class UsernameUniquenessChecker(IUsernameUniquenessChecker):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def is_available(
        self,
        username: str,
        exclude_identity_id: uuid.UUID | None = None,
    ) -> bool:
        result = await self._session.execute(
            _CHECK_SQL,
            {"username": username, "exclude_id": exclude_identity_id},
        )
        return result.scalar() is None
