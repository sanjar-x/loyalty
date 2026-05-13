"""Dishka dependency provider for security infrastructure.

Registers token provider, password hasher, and permission resolver
bindings in the IoC container.
"""

from dishka import Provider, Scope, provide
from dishka.dependency_source.composite import CompositeDependencySource
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.bootstrap.config import settings
from src.infrastructure.security.authorization import PermissionResolver
from src.infrastructure.security.jwt import JwtTokenProvider
from src.infrastructure.security.password import Argon2PasswordHasher
from src.shared.interfaces.cache import ICacheService
from src.shared.interfaces.security import (
    IPasswordHasher,
    IPermissionResolver,
    ITokenProvider,
)


class SecurityProvider(Provider):
    """Dishka provider for security-related interface bindings."""

    token_provider: CompositeDependencySource = provide(
        JwtTokenProvider, scope=Scope.APP, provides=ITokenProvider
    )
    password_hasher: CompositeDependencySource = provide(
        Argon2PasswordHasher, scope=Scope.APP, provides=IPasswordHasher
    )

    @provide(scope=Scope.APP)
    def permission_resolver(
        self,
        redis: ICacheService,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> IPermissionResolver:
        """Create the permission resolver with cache-aside strategy.

        Args:
            redis: The cache service for permission lookups.
            session_factory: An async session factory for CTE fallback queries.

        Returns:
            An ``IPermissionResolver`` backed by Redis and PostgreSQL.
        """
        return PermissionResolver(
            redis=redis,
            session_factory=session_factory,
            cache_ttl=settings.SESSION_PERMISSIONS_CACHE_TTL,
        )
