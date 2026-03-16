# src/infrastructure/security/authorization.py
"""
Cache-Aside permission resolver.
1. Check Redis SET `perms:{session_id}`
2. Hit  → return frozenset from cache
3. Miss → execute CTE query → cache with TTL → return
"""

import json
import uuid

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.infrastructure.cache.redis import RedisService
from src.shared.interfaces.security import IPermissionResolver

logger = structlog.get_logger(__name__)

_PERMISSIONS_CTE = text("""
    WITH RECURSIVE role_tree AS (
        SELECT sr.role_id
        FROM session_roles sr
        WHERE sr.session_id = :session_id
        UNION
        SELECT rh.child_role_id
        FROM role_hierarchy rh
        JOIN role_tree rt ON rt.role_id = rh.parent_role_id
    )
    SELECT DISTINCT p.codename
    FROM role_tree rt
    JOIN role_permissions rp ON rp.role_id = rt.role_id
    JOIN permissions p ON p.id = rp.permission_id
""")


class PermissionResolver(IPermissionResolver):
    def __init__(
        self,
        redis: RedisService,
        session_factory: async_sessionmaker[AsyncSession],
        cache_ttl: int = 300,
    ) -> None:
        self._redis = redis
        self._session_factory = session_factory
        self._cache_ttl = cache_ttl

    def _cache_key(self, session_id: uuid.UUID) -> str:
        return f"perms:{session_id}"

    async def get_permissions(self, session_id: uuid.UUID) -> frozenset[str]:
        key = self._cache_key(session_id)

        # 1. Try cache
        cached = await self._redis.get(key)
        if cached is not None:
            logger.debug("permissions.cache_hit", session_id=str(session_id))
            return frozenset(json.loads(cached))

        # 2. CTE fallback
        logger.debug("permissions.cache_miss", session_id=str(session_id))
        async with self._session_factory() as session:
            result = await session.execute(
                _PERMISSIONS_CTE,
                {"session_id": session_id},
            )
            codenames = [row[0] for row in result.all()]

        permissions = frozenset(codenames)

        # 3. Cache result
        await self._redis.set(key, json.dumps(list(permissions)), ttl=self._cache_ttl)

        return permissions

    async def has_permission(self, session_id: uuid.UUID, codename: str) -> bool:
        permissions = await self.get_permissions(session_id)
        return codename in permissions

    async def invalidate(self, session_id: uuid.UUID) -> None:
        key = self._cache_key(session_id)
        await self._redis.delete(key)
        logger.info("permissions.cache_invalidated", session_id=str(session_id))
