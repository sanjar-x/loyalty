# src/infrastructure/security/provider.py
from dishka import Provider, Scope, provide
from dishka.dependency_source.composite import CompositeDependencySource
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.infrastructure.cache.redis import RedisService
from src.infrastructure.security.authorization import PermissionResolver
from src.infrastructure.security.jwt import JwtTokenProvider
from src.infrastructure.security.password import Argon2PasswordHasher
from src.shared.interfaces.security import (
    IPasswordHasher,
    IPermissionResolver,
    ITokenProvider,
)


class SecurityProvider(Provider):
    token_provider: CompositeDependencySource = provide(
        JwtTokenProvider, scope=Scope.APP, provides=ITokenProvider
    )
    password_hasher: CompositeDependencySource = provide(
        Argon2PasswordHasher, scope=Scope.APP, provides=IPasswordHasher
    )

    @provide(scope=Scope.APP)
    def permission_resolver(
        self,
        redis: RedisService,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> IPermissionResolver:
        return PermissionResolver(redis=redis, session_factory=session_factory)
