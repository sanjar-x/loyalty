# src/infrastructure/security/provider.py
from dishka import Provider, Scope, provide

from src.infrastructure.security.jwt import JwtTokenProvider
from src.infrastructure.security.password import BcryptPasswordHasher
from src.shared.interfaces.security import IPasswordHasher, ITokenProvider


class SecurityProvider(Provider):
    """
    DI Провайдер для инициализации инфраструктурных сервисов безопасности.
    Позволяет бизнес-логике зависеть только от абстрактных интерфейсов 
    (IPasswordHasher, ITokenProvider).
    """

    token_provider = provide(
        JwtTokenProvider, scope=Scope.APP, provides=ITokenProvider
    )

    password_hasher = provide(
        BcryptPasswordHasher, scope=Scope.APP, provides=IPasswordHasher
    )
