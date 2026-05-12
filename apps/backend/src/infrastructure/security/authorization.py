"""Cache-aside permission resolver with Redis and PostgreSQL fallback.

Resolution flow:
1. Check Redis SET ``perms:{session_id}``
2. Cache hit -> return frozenset from cache
3. Cache miss -> execute recursive CTE query -> cache with TTL -> return
"""

import json
import uuid

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.shared.interfaces.cache import ICacheService
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
    """Cache-aside permission resolver using Redis and a recursive CTE fallback.

    Permissions for a session are cached in Redis with a configurable TTL.
    On cache miss, a recursive CTE traverses the role hierarchy to resolve
    the full set of permission codenames.
    """

    def __init__(
        self,
        redis: ICacheService,
        session_factory: async_sessionmaker[AsyncSession],
        cache_ttl: int = 300,
    ) -> None:
        """Initialize the resolver with cache and database access.

        Args:
            redis: The cache service for permission lookups.
            session_factory: An async session factory for CTE fallback queries.
            cache_ttl: Time-to-live in seconds for cached permission sets.
        """
        self._redis = redis
        self._session_factory = session_factory
        self._cache_ttl = cache_ttl

    def _build_cache_key(self, session_id: uuid.UUID) -> str:
        """Build the Redis cache key for a given session.

        Args:
            session_id: The session UUID.

        Returns:
            A formatted cache key string.
        """
        return f"perms:{session_id}"

    async def get_permissions(self, session_id: uuid.UUID) -> frozenset[str]:
        """Resolve all permission codenames for the given session.

        Checks Redis first; on cache miss, falls back to a recursive CTE
        query and caches the result.

        Args:
            session_id: The session UUID to resolve permissions for.

        Returns:
            A frozenset of permission codename strings.
        """
        key = self._build_cache_key(session_id)

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

        # 3. Cache result (skip empty sets to avoid masking pending role assignments)
        if permissions:
            await self._redis.set(
                key, json.dumps(list(permissions)), ttl=self._cache_ttl
            )

        return permissions

    async def has_permission(self, session_id: uuid.UUID, codename: str) -> bool:
        """Check whether a session holds a specific permission.

        Args:
            session_id: The session UUID.
            codename: The permission codename to check.

        Returns:
            True if the permission is present, False otherwise.
        """
        permissions = await self.get_permissions(session_id)
        return codename in permissions

    async def invalidate(self, session_id: uuid.UUID) -> None:
        """Invalidate the cached permission set for a session.

        Args:
            session_id: The session UUID whose cache entry should be removed.
        """
        key = self._build_cache_key(session_id)
        await self._redis.delete(key)
        logger.info("permissions.cache_invalidated", session_id=str(session_id))

    async def invalidate_many(self, session_ids: list[uuid.UUID]) -> None:
        """Invalidate cached permission sets for multiple sessions in one round-trip.

        Args:
            session_ids: The session UUIDs whose cache entries should be removed.
        """
        if not session_ids:
            return
        keys = [self._build_cache_key(sid) for sid in session_ids]
        await self._redis.delete_many(keys)
        logger.info("permissions.cache_bulk_invalidated", count=len(session_ids))
